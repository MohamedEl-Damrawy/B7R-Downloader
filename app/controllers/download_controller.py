"""Download orchestration controller with queue/concurrency and playlist item support."""

from __future__ import annotations

import shutil
import time
import uuid
from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.core.constants import (
    DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    MAX_CONCURRENT_DOWNLOADS,
    MIN_CONCURRENT_DOWNLOADS,
    MIN_FREE_SPACE_BYTES,
    SETTINGS_COOKIEFILE,
    SETTINGS_MAX_CONCURRENT_DOWNLOADS,
    SETTINGS_PROXY,
    SETTINGS_SPONSORBLOCK,
)
from app.core.logger import get_logger
from app.core.validators import is_valid_playlist_items, redact_url
from app.database.repositories.download_items_repo import DownloadItemsRepository
from app.database.repositories.downloads_repo import DownloadsRepository
from app.engine.format_selector import audio_preset_for_quality, pick_format_for_quality
from app.models.download import DownloadTask, utc_now_iso
from app.models.download_status import DownloadStatus, can_transition
from app.services.settings_service import SettingsService
from app.sources import get_provider_for_url
from app.workers.download_worker import DownloadWorker
from app.workers.metadata_worker import MetadataWorker

logger = get_logger(__name__)

# Minimum interval between two DB writes for the same task's progress-only
# updates, so that high-frequency yt-dlp progress hooks cannot hammer SQLite.
_DB_WRITE_INTERVAL_SEC = 0.5


# PERF-04: number of index-only playlist entries bundled into a single batch
# task. Each per-entry task would re-fetch the whole playlist page once per
# item (N fetches + HTTP 429 risk); a batch task selects a comma list of
# indices with one fetch per chunk instead.
_PLAYLIST_BATCH_SIZE = 25


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
        # PERF-04: per-batch progress aggregation. A batch task downloads N
        # items sequentially; yt-dlp restarts at 0% per item, so the reported
        # percentage would jump down between items. This state tracks how many
        # items finished to compute a monotonic overall percentage.
        self._batch_state: dict[str, dict] = {}

    def _max_concurrent(self) -> int:
        try:
            val = int(SettingsService().get(SETTINGS_MAX_CONCURRENT_DOWNLOADS, DEFAULT_MAX_CONCURRENT_DOWNLOADS))
        except Exception:
            val = DEFAULT_MAX_CONCURRENT_DOWNLOADS
        return max(MIN_CONCURRENT_DOWNLOADS, min(MAX_CONCURRENT_DOWNLOADS, val))

    def _network_opts(self) -> dict[str, str | None]:
        """Read engine credential options from settings (DL-07/FEAT-04/05)."""
        try:
            svc = SettingsService()
            cookiefile = svc.get(SETTINGS_COOKIEFILE) or None
            proxy = svc.get(SETTINGS_PROXY) or None
            cookiefile = cookiefile if cookiefile and Path(cookiefile).exists() else None
            if cookiefile is None:
                configured = svc.get(SETTINGS_COOKIEFILE)
                if configured and not Path(configured).exists():
                    logger.warning("Configured cookiefile does not exist; ignoring: %s", configured)
            return {"cookiefile": cookiefile, "proxy": (proxy or "").strip() or None}
        except Exception:
            return {"cookiefile": None, "proxy": None}

    def _sponsorblock_enabled(self) -> bool:
        try:
            return str(SettingsService().get(SETTINGS_SPONSORBLOCK, "0")).strip() == "1"
        except Exception:
            return False

    def _disk_has_space(self, output_dir: str) -> bool:
        """FEAT-06: refuse enqueueing when the destination drive is nearly full."""
        try:
            usage = shutil.disk_usage(str(output_dir))
        except Exception:
            return True  # cannot verify (e.g. network drive) -> do not block
        if usage.free >= MIN_FREE_SPACE_BYTES:
            return True
        logger.error(
            "Not enough free space at %s: %.1f MB available, %.1f MB required",
            output_dir,
            usage.free / (1024 * 1024),
            MIN_FREE_SPACE_BYTES / (1024 * 1024),
        )
        return False

    def extract_metadata(self, url: str) -> None:
        logger.info("Queue metadata extraction: url=%s", redact_url(url))
        net = self._network_opts()
        # Provider routing (Spotify plan Phase A): non-YouTube providers get
        # their own resolution path in Phase B. Today every registered URL
        # resolves to the YouTube fallback, so the existing worker path below
        # is byte-identical to before.
        provider = get_provider_for_url(url)
        if provider is not None and provider.name != "youtube":
            logger.info("Non-YouTube provider %s matched; dedicated worker pending (Phase B)", provider.name)
        worker = MetadataWorker(url, cookiefile=net.get("cookiefile"), proxy=net.get("proxy"))
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
        embed_metadata: bool = False,
        embed_thumbnail: bool = False,
        write_subs: bool = False,
        playlist_item_ids: list[str] | None = None,
        playlist_item_count: int = 0,
    ) -> str:
        if playlist_items and not is_valid_playlist_items(str(playlist_items)):
            logger.error(
                "Refusing to enqueue task with invalid playlist_items=%r "
                "(would risk downloading a whole playlist)",
                playlist_items,
            )
            return ""
        task_id = uuid.uuid4().hex
        audio_format = audio_preset_for_quality(quality)
        fmt = pick_format_for_quality([], quality) or "bv*+ba/b"
        # Resolve/prepare the output directory; fall back to the default when empty
        # so a task never ends up writing to the process working directory.
        try:
            from app.core.paths import get_default_download_dir

            out = Path(output_dir).expanduser() if str(output_dir or "").strip() else Path(get_default_download_dir())
            out.mkdir(parents=True, exist_ok=True)
            output_dir = str(out)
        except Exception:
            logger.warning("Could not prepare output directory at enqueue time: %s", output_dir, exc_info=True)
        # FEAT-06: preflight disk-space check on the resolved destination.
        if not self._disk_has_space(output_dir):
            self._tasks[task_id] = {"id": task_id, "source_url": url, "title": title}
            self._update_status(
                task_id, DownloadStatus.FAILED,
                error_message="Not enough free disk space at destination.",
            )
            return task_id
        net = self._network_opts()
        task = DownloadTask(
            id=task_id,
            source_url=url,
            title=title,
            thumbnail_url=thumbnail_url,
            selected_format=quality,
            output_path=output_dir,
            status=DownloadStatus.QUEUED,
            playlist_id=playlist_id,
            playlist_items=playlist_items,
        )
        self.repo.upsert(self._task_to_record(task))
        self._specs[task_id] = {
            "url": url,
            "output_dir": output_dir,
            "format_selector": fmt,
            "playlist_items": playlist_items,
            "playlist_item_id": playlist_item_id,
            "playlist_item_ids": list(playlist_item_ids or []),
            "playlist_item_count": int(playlist_item_count) if playlist_item_count else len(playlist_item_ids or []),
            "audio_format": audio_format,
            "embed_metadata": embed_metadata,
            "embed_thumbnail": embed_thumbnail,
            "write_subs": write_subs,
            "sponsorblock": self._sponsorblock_enabled(),
            "cookiefile": net.get("cookiefile"),
            "proxy": net.get("proxy"),
        }
        for item_id in ([playlist_item_id] if playlist_item_id else []) + list(playlist_item_ids or []):
            if not item_id:
                continue
            try:
                self.items_repo.link_download(item_id, task_id, DownloadStatus.QUEUED.value)
            except Exception:
                logger.exception("Failed to link playlist item %s to task %s", item_id, task_id)
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
        playlist_title: str = "",
    ) -> list[str]:
        ids: list[str] = []
        # PERF-04: entries without a direct URL are split into two groups.
        # Direct-URL entries become cheap per-item tasks (single-video fetch).
        # Index-only entries are bundled into batch tasks whose playlist_items
        # is the comma-joined list of numeric indices, so one download_media
        # call (and one playlist page fetch) covers _PLAYLIST_BATCH_SIZE items.
        direct: list = []
        index_only: list = []
        for e in entries:
            if not getattr(e, "available", True):
                logger.info("Skipping unavailable playlist entry: title=%s", getattr(e, "title", ""))
                continue
            entry_url = getattr(e, "source_url", "") or ""
            if entry_url and str(entry_url).startswith("http"):
                direct.append(e)
            elif playlist_url and isinstance(getattr(e, "index", None), int):
                index_only.append(e)
            else:
                logger.warning(
                    "Skipping playlist entry without direct URL or numeric index: title=%s",
                    getattr(e, "title", ""),
                )

        for e in direct:
            new_id = self.start_download(
                url=getattr(e, "source_url", ""),
                output_dir=output_dir,
                quality=quality,
                title=getattr(e, "title", "") or "Untitled",
                thumbnail_url=getattr(e, "thumbnail_url", "") or "",
                playlist_id=playlist_id,
                playlist_item_id=getattr(e, "playlist_item_id", None),
            )
            if new_id:
                ids.append(new_id)

        # Batches must walk the playlist in order: sort by index, chunk, and
        # give yt-dlp the exact "i,j,k" selection list for each chunk.
        index_only.sort(key=lambda e: getattr(e, "index", 0))
        for chunk_start in range(0, len(index_only), _PLAYLIST_BATCH_SIZE):
            chunk = index_only[chunk_start:chunk_start + _PLAYLIST_BATCH_SIZE]
            items_str = ",".join(str(e.index) for e in chunk)
            if playlist_title:
                label = f"{playlist_title} ({len(chunk)} items)"
            else:
                label = f"Playlist batch ({len(chunk)} items)"
            new_id = self.start_download(
                url=playlist_url,
                output_dir=output_dir,
                quality=quality,
                title=label,
                thumbnail_url=getattr(chunk[0], "thumbnail_url", "") or "",
                playlist_id=playlist_id,
                playlist_items=items_str,
                playlist_item_ids=[getattr(e, "playlist_item_id", None) for e in chunk],
                playlist_item_count=len(chunk),
            )
            if new_id:
                ids.append(new_id)
                logger.info(
                    "Batched %d playlist entries into task %s (playlist_items=%s)",
                    len(chunk),
                    new_id,
                    items_str,
                )
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
        task_url = (rec.get("source_url") or "").strip()
        if rec.get("playlist_id"):
            try:
                from app.database.repositories.playlists_repo import PlaylistsRepository
                pl = PlaylistsRepository().get(str(rec.get("playlist_id")))
                playlist_url = (pl or {}).get("source_url")
            except Exception:
                playlist_url = None

        # PERF-04: prefer the persisted playlist_items selection (batch tasks
        # always carry one). Fall back to the legacy single-item index mapping.
        persisted_items = str(rec.get("playlist_items") or "").strip()
        if persisted_items and is_valid_playlist_items(persisted_items):
            playlist_items = persisted_items
        else:
            try:
                item = self.items_repo.get_by_download_id(task_id)
            except Exception:
                item = None
            if item:
                playlist_item_id = item.get("id")
                idx = item.get("entry_index")
                item_url = (item.get("source_url") or "").strip()
                # Use playlist index selection when the original task targeted
                # the playlist URL (not a direct entry URL), to avoid
                # re-downloading the whole playlist.
                if idx is not None and playlist_url and task_url == str(playlist_url).strip():
                    playlist_items = str(idx)
                elif idx is not None and (not item_url or not item_url.startswith("http")) and task_url:
                    playlist_items = str(idx)

        # Guard: a task whose URL is the playlist URL with neither a persisted
        # selection nor a linked item would download the ENTIRE playlist on
        # retry. Refuse instead of silently re-enqueueing a full-playlist task.
        if not playlist_items and not playlist_item_id and playlist_url and task_url == str(playlist_url).strip():
            logger.error(
                "Refusing to retry task %s: playlist-URL task without playlist_items or a linked item "
                "(retrying would download the whole playlist). Re-select the items on the Playlists page instead.",
                task_id,
            )
            return None

        # Re-enqueue as a new task to preserve history of prior attempt.
        new_id = self.start_download(
            url=rec.get("source_url") or "",
            output_dir=rec.get("output_path") or "",
            quality=rec.get("selected_format") or "best",
            title=rec.get("title") or "",
            thumbnail_url=rec.get("thumbnail_url") or "",
            playlist_id=rec.get("playlist_id"),
            playlist_items=playlist_items,
            playlist_item_id=playlist_item_id,
        )
        # Re-link every item that shared the old task (batch tasks link many)
        # to the new task id so per-item status sync keeps working.
        if new_id and not playlist_item_id:
            try:
                for linked in self.items_repo.list_by_download_id(task_id):
                    linked_id = linked.get("id")
                    if linked_id:
                        self.items_repo.link_download(
                            str(linked_id), new_id, DownloadStatus.QUEUED.value
                        )
            except Exception:
                logger.exception("Failed to re-link items from task %s to retry task %s", task_id, new_id)
        return new_id

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
            audio_format=spec.get("audio_format"),
            embed_metadata=bool(spec.get("embed_metadata")),
            embed_thumbnail=bool(spec.get("embed_thumbnail")),
            write_subs=bool(spec.get("write_subs")),
            sponsorblock=bool(spec.get("sponsorblock")),
            cookiefile=spec.get("cookiefile"),
            proxy=spec.get("proxy"),
        )
        self._workers[task_id] = worker
        self._active.add(task_id)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda tid=task_id: self._on_finished(tid))
        logger.info("Task started: id=%s url=%s", task_id, redact_url(spec.get("url", "")))
        # PERF-04: initialize batch aggregation for multi-item batch tasks.
        item_count = int(spec.get("playlist_item_count") or 0)
        if item_count > 1:
            self._batch_state[task_id] = {"completed": 0, "last_progress": 0.0}
        # Real EXTRACTING state: yt-dlp runs metadata extraction before the first
        # progress hook fires, which then flips the task to DOWNLOADING (DEAD-10).
        self._update_status(task_id, DownloadStatus.EXTRACTING, progress=0.0)
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
            "playlist_items": task.playlist_items,
            "source_type": task.source_type,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }

    def _sync_playlist_item(self, task_id: str, status: DownloadStatus, progress: float | None = None,
                             error_message: str | None = None, output_path: str | None = None) -> None:
        spec = self._specs.get(task_id) or {}
        # PERF-04: batch tasks have no single playlist_item_id but DO have a
        # list of linked items; update_by_download_id syncs every item that
        # shares this task's download_id.
        if not spec.get("playlist_item_id") and not spec.get("playlist_item_ids"):
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
        # Enforce the documented state machine (QUAL/DEAD-09): the previous
        # status is whatever was last passed through this method, because any
        # status change is persisted immediately.
        prev = self._persisted_status.get(task_id)
        if prev is not None and prev != status_str and not can_transition(
            DownloadStatus(prev), DownloadStatus(status_str)
        ):
            logger.error(
                "Invalid status transition for task %s: %s -> %s (applying anyway, bug suspected)",
                task_id,
                prev,
                status_str,
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
            self._sync_playlist_item(
                task_id, status,
                progress=payload.get("progress"),
                error_message=error_message,
                output_path=payload.get("output_path"),
            )
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
        # PERF-04: aggregate per-item progress for batch tasks. yt-dlp restarts
        # at 0% for each item inside one batch task; detect the restart (a
        # sharp drop) to count finished items and report a monotonic overall
        # percentage. Heuristic: a drop of more than 20 points means the next
        # item started (per-item hooks never drop that far mid-download).
        spec = self._specs.get(task_id) or {}
        item_count = int(spec.get("playlist_item_count") or 0)
        if item_count > 1 and task_id in self._batch_state:
            state = self._batch_state[task_id]
            if pct is not None:
                if state["last_progress"] >= 20.0 and pct < state["last_progress"] - 20.0:
                    state["completed"] += 1
                state["last_progress"] = pct
                overall = (state["completed"] + pct / 100.0) / item_count * 100.0
                pct = max(0.0, min(100.0, overall))
            else:
                # postprocessing: keep the last overall percentage
                pct = (state["completed"] + 1.0) / item_count * 100.0 if state["completed"] else None
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
        self._batch_state.pop(task_id, None)
        self.task_finished.emit(task_id)
        self._drain_queue()
