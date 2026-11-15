"""Worker for download execution."""

from __future__ import annotations

from PySide6.QtCore import Slot

from app.core.logger import get_logger
from app.core.validators import redact_url
from app.engine.ffmpeg_manager import get_ffmpeg_location_for_ytdlp
from app.engine.ytdlp_engine import CancelToken, download_media
from app.workers.base_worker import BaseWorker


class DownloadWorker(BaseWorker):
    def __init__(
        self,
        task_id: str,
        url: str,
        output_dir: str,
        format_selector: str = "bv*+ba/b",
        playlist_items: str | None = None,
        audio_format: str | None = None,
        embed_metadata: bool = False,
        embed_thumbnail: bool = False,
        write_subs: bool = False,
        sponsorblock: bool = False,
        cookiefile: str | None = None,
        proxy: str | None = None,
    ):
        super().__init__()
        self.task_id = task_id
        self.url = url
        self.output_dir = output_dir
        self.format_selector = format_selector
        self.playlist_items = playlist_items
        self.audio_format = audio_format
        self.embed_metadata = embed_metadata
        self.embed_thumbnail = embed_thumbnail
        self.write_subs = write_subs
        self.sponsorblock = sponsorblock
        self.cookiefile = cookiefile
        self.proxy = proxy
        self.cancel_token = CancelToken()

    def cancel(self) -> None:
        self.cancel_token.cancel()

    @Slot()
    def run(self) -> None:
        logger = get_logger(__name__)
        try:
            result = download_media(
                url=self.url,
                output_dir=self.output_dir,
                format_selector=self.format_selector,
                ffmpeg_location=get_ffmpeg_location_for_ytdlp(),
                progress_callback=lambda d: self.signals.progress.emit(
                    {"task_id": self.task_id, **(d or {})}
                ),
                cancel_token=self.cancel_token,
                playlist_items=self.playlist_items,
                audio_format=self.audio_format,
                embed_metadata=self.embed_metadata,
                embed_thumbnail=self.embed_thumbnail,
                write_subs=self.write_subs,
                sponsorblock=self.sponsorblock,
                cookiefile=self.cookiefile,
                proxy=self.proxy,
            )
            self.signals.result.emit({"task_id": self.task_id, "result": result})
        except Exception as exc:
            logger.exception(
                "DownloadWorker failed: task_id=%s url=%s output=%s",
                self.task_id,
                redact_url(self.url),
                self.output_dir,
            )
            self.signals.error.emit(f"{self.task_id}::{exc}")
        finally:
            self.signals.finished.emit()
