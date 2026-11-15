"""Worker for metadata extraction."""

from __future__ import annotations

from PySide6.QtCore import Slot

from app.core.logger import get_logger
from app.core.validators import redact_url
from app.engine.ffmpeg_manager import get_ffmpeg_location_for_ytdlp
from app.engine.ytdlp_engine import extract_metadata
from app.workers.base_worker import BaseWorker


class MetadataWorker(BaseWorker):
    def __init__(self, url: str, cookiefile: str | None = None, proxy: str | None = None):
        super().__init__()
        self.url = url
        self.cookiefile = cookiefile
        self.proxy = proxy

    @Slot()
    def run(self) -> None:
        logger = get_logger(__name__)
        try:
            ffmpeg_location = get_ffmpeg_location_for_ytdlp()
            video, playlist = extract_metadata(
                self.url,
                ffmpeg_location=ffmpeg_location,
                cookiefile=self.cookiefile,
                proxy=self.proxy,
            )
            self.signals.result.emit({"video": video, "playlist": playlist})
        except Exception as exc:
            logger.exception("MetadataWorker failed: url=%s", redact_url(self.url))
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()
