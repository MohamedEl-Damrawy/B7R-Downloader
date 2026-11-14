"""Download orchestration controller with queue/concurrency and playlist item support."""

from __future__ import annotations

import time
import uuid
from collections import deque

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.core.constants import (
    DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    MAX_CONCURRENT_DOWNLOADS,
    MIN_CONCURRENT_DOWNLOADS,
    SETTINGS_MAX_CONCURRENT_DOWNLOADS,
)
from app.core.logger import get_logger
from app.core.validators import is_valid_playlist_items, redact_url
from app.database.repositories.download_items_repo import DownloadItemsRepository
from app.database.repositories.downloads_repo import DownloadsRepository
from app.engine.format_selector import pick_format_for_quality
from app.models.download import DownloadTask, utc_now_iso
from app.models.download_status import DownloadStatus
from app.services.settings_service import SettingsService
from app.workers.download_worker import DownloadWorker
from app.workers.metadata_worker import MetadataWorker

logger = get_logger(__name__)

# Minimum interval between two DB writes for the same task's progress-only
# updates, so that high-frequency yt-dlp progress hooks cannot hammer SQLite.
_DB_WRITE_INTERVAL_SEC = 0.5


class DownloadController(QObject):
    metadata_result = Signal(object)
    metadata_error = Signal(str)
    metadata_finished = Signal()

    task_added = Signal(object)
    task_updated = Signal(object)
    task_error = Signal(str, str)  # task_id, message
    task_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.repo = DownloadsRepository()
        self.items_repo = DownloadItemsRepository()
        self._workers: dict[str, DownloadWorker] = {}
        self._pending: deque[str] = deque()
        self._active: set[str] = set()
        self._specs: dict[str, dict] = {}
        self._tasks: dict[str, dict] = {}
        self._persisted_status: dict[str, str] = {}
        self._last_progress_persist: dict[str, float] = {}

    def _max_concurrent(self) -> int:
        try:
            val = int(SettingsService().get(SETTINGS_MAX_CONCURRENT_DOWNLOADS, DEFAULT_MAX_CONCURRENT_DOWNLOADS))
        except Exception:
            val = DEFAULT_MAX_CONCURRENT_DOWNLOADS
        return max(MIN_CONCURRENT_DOWNLOADS, min(MAX_CONCURRENT_DOWNLOADS, val))

    def extract_metadata(self, url: str) -> None:
        logger.info("Queue metadata extraction: url=%s", redact_url(url))
        worker = MetadataWorker(url)
        worker.signals.result.connect(self.metadata_result)
        worker.signals.error.connect(self.metadata_error)
        worker.signals.finished.connect(self.metadata_finished)
        self.pool.start(worker)

    def start_download(
        self,
        url: str,
        output_dir: str,
        quality: str = "best",
        title: str = "",
        thumbnail_url: str = "",
        playlist_id: str | None = None,
        playlist_items: str | None = None,
        playlist_item_id: str | None = None,
    ) -> str:
        if playlist_items and not is_valid_playlist_items(str(playlist_items)):
            logger.error(
                "Refusing to enqueue task with invalid playlist_items=%r "
                "(would risk downloading a whole playlist)",
                playlist_items,
            )
            return ""
        task_id = uuid.uuid4().hex
        fmt = pick_format_for_quality([], quality) or "bv*+ba/b"
        # Resolve/prepare the output directory; fall back to the default when empty
        # so a task never ends up writing to the process working directory.
        try:
            from pathlib import Path

            from app.core.paths import get_default_download_dir

            out = Path(output_dir).expanduser() if str(output_dir or "").strip() else Path(get_default_download_dir())
            out.mkdir(parents=True, exist_ok=True)
            output_dir = str(out)
        except Exception:
            logger.warning("Could not prepare output directory at enqueue time: %s", output_dir, exc_info=True)
        task = DownloadTask(
            id=task_id,
            source_url=url,
            title=title,
            thumbnail_url=thumbnail_url,
            selected_format=quality,
            output_path=output_dir,
            status=DownloadStatus.QUEUED,
            playlist_id=playlist_id,
        )
        self.repo.upsert(self._task_to_record(task))
        self._specs[task_id] = {
            "url": url,
            "output_dir": output_dir,
            "format_selector": fmt,
            "playlist_items": playlist_items,
            "playlist_item_id": playlist_item_id,
        }
        if playlist_item_id:
            try:
                self.items_repo.link_download(playlist_item_id, task_id, DownloadStatus.QUEUED.value)
            except Exception:
                logger.exception("Failed to link playlist item %s to task %s", playlist_item_id, task_id)
        self._pending.append(task_id)
        emitted = self._task_to_record(task)
        self._tasks[task_id] = emitted
        self.task_added.emit(emitted)
        logger.info(
            "Task queued: id=%s url=%s output=%s playlist_item=%s",
            task_id,
            redact_url(url),
            output_dir,
            playlist_item_id,
        )
        self._drain_queue()
        return task_id

    def start_playlist_downloads(
        self,
        playlist_url: str,
        output_dir: str,
        quality: str,
        entries: list,
        playlist_id: str | None = None,
    ) -> list[str]:
        ids: list[str] = []
        for e in entries:
            if not getattr(e, "available", True):
                logger.info("Skipping unavailable playlist entry: title=%s", getattr(e, "title", ""))
                continue
            title = getattr(e, "title", "") or "Untitled"
            thumb = getattr(e, "thumbnail_url", "") or ""
            idx = getattr(e, "index", None)
            entry_url = getattr(e, "source_url", "") or ""
            playlist_item_id = getattr(e, "playlist_item_id", None)
            if entry_url and str(entry_url).startswith("http"):
                url = entry_url
                playlist_items = None
            elif playlist_url and isinstance(idx, int):
                # Without a direct entry URL the item can only be targeted by its
                # numeric playlist index; a video ID is NOT valid playlist_items.
                url = playlist_url
                playlist_items = str(idx)
            else:
                logger.warning(
                    "Skipping playlist entry without direct URL or numeric index: title=%s",
                    title,
                )
                continue
            new_id = self.start_download(
                url=url,
                output_dir=output_dir,
                quality=quality,
                title=title,
                thumbnail_url=thumb,
                playlist_id=playlist_id,
                playlist_items=playlist_items,
                playlist_item_id=playlist_item_id,
            )
            if new_id:
                ids.append(new_id)
        return ids

    def cancel_download(self, task_id: str) -> None:
        if task_id in self._pending:
            try:
                self._pending.remove(task_id)
            except ValueError:
                pass
            self._update_status(task_id, DownloadStatus.CANCELLED, error_message="Cancelled by user.")
            self._specs.pop(task_id, None)
            return
        w = self._workers.get(task_id)
        if w:
            w.cancel()

    def retry_download(self, task_id: str) -> str | None:
        if task_id in self._active or task_id in self._pending:
            return None
        rec = self.repo.get_by_id(task_id)
        if not rec:
            return None
        if rec.get("status") not in (DownloadStatus.FAILED.value, DownloadStatus.CANCELLED.value):
            return None

        playlist_item_id = None
        playlist_items = None
        playlist_url = None
        if rec.get("playlist_id"):
            try:
                from app.database.repositories.playlists_repo import PlaylistsRepository
                pl = PlaylistsRepository().get(str(rec.get("playlist_id")))
                playlist_url = (pl or {}).get("source_url")
            except Exception:
                playlist_url = None
        try:
            item = self.items_repo.get_by_download_id(task_id)
        except Exception:
            item = None
        if item:
            playlist_item_id = item.get("id")
            idx = item.get("entry_index")
            item_url = (item.get("source_url") or "").strip()
            task_url = (rec.get("source_url") or "").strip()
            # Use playlist index selection when the original task targeted the playlist URL
            # (not a direct entry URL), to avoid re-downloading the whole playlist.
            if idx is not None and playlist_url and task_url == str(playlist_url).strip():
                playlist_items = str(idx)
            elif idx is not None and (not item_url or not item_url.startswith("http")) and task_url:
                playlist_items = str(idx)

        # Re-enqueue as a new task to preserve history of prior attempt.
        return self.start_download(
            url=rec.get("source_url") or "",
            output_dir=rec.get("output_path") or "",
            quality=rec.get("selected_format") or "best",
            title=rec.get("title") or "",
            thumbnail_url=rec.get("thumbnail_url") or "",
            playlist_id=rec.get("playlist_id"),
            playlist_items=playlist_items,
            playlist_item_id=playlist_item_id,
        )

    def _drain_queue(self) -> None:
        while len(self._active) < self._max_concurrent() and self._pending:
            task_id = self._pending.popleft()
            spec = self._specs.get(task_id)
            if not spec:
                continue
            self._start_worker(task_id, spec)

    def _start_worker(self, task_id: str, spec: dict) -> None:
        worker = DownloadWorker(
            task_id=task_id,
            url=spec["url"],
            output_dir=spec["output_dir"],
            format_selector=spec.get("format_selector") or "bv*+ba/b",
            playlist_items=spec.get("playlist_items"),
        )
        self._workers[task_id] = worker
        self._active.add(task_id)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda tid=task_id: self._on_finished(tid))
        logger.info("Task started: id=%s url=%s", task_id, redact_url(spec.get("url", "")))
        self._update_status(task_id, DownloadStatus.DOWNLOADING, progress=0.0)
        self.pool.start(worker)

    def _task_to_record(self, task: DownloadTask) -> dict:
        return {
            "id": task.id,
            "source_url": task.source_url,
            "title": task.title,
            "thumbnail_url": task.thumbnail_url,
            "selected_format": task.selected_format,
            "output_path": task.output_path,
            "status": task.status.value if isinstance(task.status, DownloadStatus) else str(task.status),
            "progress": task.progress,
            "downloaded_bytes": task.downloaded_bytes,
            "total_bytes": task.total_bytes,
            "speed": task.speed,
            "eta": task.eta,
            "error_code": None,
            "error_message": task.error_message,
            "playlist_id": task.playlist_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }

    def _sync_playlist_item(self, task_id: str, status: DownloadStatus, progress: float | None = None,
                             error_message: str | None = None, output_path: str | None = None) -> None:
        spec = self._specs.get(task_id) or {}
        item_id = spec.get("playlist_item_id")
        if not item_id:
            return
        try:
            self.items_repo.update_by_download_id(
                task_id,
                status.value if isinstance(status, DownloadStatus) else str(status),
                progress=progress,
                output_path=output_path,
                error_message=error_message,
            )
        except Exception:
            logger.debug("Failed to sync playlist item state for task %s", task_id, exc_info=True)

    def _update_status(self, task_id: str, status: DownloadStatus, progress: float | None = None,
                       error_message: str | None = None, completed: bool = False,
                       downloaded_bytes: int | None = None, total_bytes: int | None = None,
                       speed: float | None = None, eta: int | None = None, output_path: str | None = None) -> None:
        now = utc_now_iso()
        status_str = status.value if isinstance(status, DownloadStatus) else str(status)
        # Persist to the DB only on status changes (always) or at most every
        # _DB_WRITE_INTERVAL_SEC for progress-only updates; the UI payload below
        # is emitted on every call so live progress stays smooth.
        mono = time.monotonic()
        should_persist = (
            self._persisted_status.get(task_id) != status_str
            or (mono - self._last_progress_persist.get(task_id, 0.0)) >= _DB_WRITE_INTERVAL_SEC
        )
        if should_persist:
            self._persisted_status[task_id] = status_str
            self._last_progress_persist[task_id] = mono
            self.repo.update_status(
                task_id,
                status,
                progress=progress,
                error_message=error_message,
                updated_at=now,
                completed_at=now if completed else None,
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
                speed=speed,
                eta=eta,
                output_path=output_path,
            )
        cached = self._tasks.get(task_id, {"id": task_id})
        payload = {
            **cached,
            "id": task_id,
            "status": status.value,
            "progress": progress if progress is not None else cached.get("progress"),
            "error_message": error_message,
            "downloaded_bytes": downloaded_bytes if downloaded_bytes is not None else cached.get("downloaded_bytes"),
            "total_bytes": total_bytes if total_bytes is not None else cached.get("total_bytes"),
            "speed": speed if speed is not None else cached.get("speed"),
            "eta": eta if eta is not None else cached.get("eta"),
            "output_path": output_path if output_path is not None else cached.get("output_path"),
        }
        self._tasks[task_id] = payload
        if should_persist:
            self._sync_playlist_item(task_id, status, progress=payload.get("progress"), error_message=error_message, output_path=payload.get("output_path"))
        self.task_updated.emit(payload)

    def _on_progress(self, payload: dict) -> None:
        task_id = (payload or {}).get("task_id")
        if not task_id:
            return
        pct = payload.get("percentage")
        if pct is not None:
            try:
                pct = max(0.0, min(100.0, float(pct)))
            except Exception:
                pct = None
        status_str = str(payload.get("status") or "downloading").lower()
        # yt-dlp progress hooks emit "downloading"/"finished"; our
        # postprocessor_hooks add "postprocessing" during the ffmpeg merge.
        if "finished" in status_str or "processing" in status_str:
            status = DownloadStatus.PROCESSING
        else:
            status = DownloadStatus.DOWNLOADING
        self._update_status(
            task_id,
            status,
            progress=pct,
            downloaded_bytes=payload.get("downloaded_bytes"),
            total_bytes=payload.get("total_bytes"),
            speed=payload.get("speed"),
            eta=payload.get("eta"),
        )

    def _on_result(self, payload: dict) -> None:
        task_id = (payload or {}).get("task_id")
        if task_id:
            result = (payload or {}).get("result") or {}
            out_path = result.get("filepath") or result.get("_filename")
            logger.info("Task completed: id=%s path=%s", task_id, out_path)
            self._update_status(task_id, DownloadStatus.COMPLETED, progress=100.0, completed=True, output_path=out_path)

    def _on_error(self, message: str) -> None:
        task_id = ""
        err = message or "Download failed."
        if "::" in err:
            task_id, err = err.split("::", 1)
        if task_id:
            status = DownloadStatus.CANCELLED if "cancel" in err.lower() else DownloadStatus.FAILED
            logger.warning("Task %s ended with status %s: %s", task_id, status.value, err)
            self._update_status(task_id, status, error_message=err)
            self.task_error.emit(task_id, err)
        else:
            logger.error("Task error without task id: %s", err)

    def _on_finished(self, task_id: str) -> None:
        self._workers.pop(task_id, None)
        self._active.discard(task_id)
        self._specs.pop(task_id, None)
        self._persisted_status.pop(task_id, None)
        self._last_progress_persist.pop(task_id, None)
        self.task_finished.emit(task_id)
        self._drain_queue()
