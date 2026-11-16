"""Worker that resolves a Spotify URL into a SourcePlan (off the GUI thread)."""

from __future__ import annotations

from PySide6.QtCore import Slot

from app.core.logger import get_logger
from app.sources.base import SourcePlan, SourceProvider
from app.workers.base_worker import BaseWorker


class ProviderMetadataWorker(BaseWorker):
    """Runs provider.resolve(url) and emits the normalized SourcePlan."""

    def __init__(self, url: str, provider: SourceProvider):
        super().__init__()
        self.url = url
        self.provider = provider

    @Slot()
    def run(self) -> None:
        logger = get_logger(__name__)
        try:
            plan: SourcePlan = self.provider.resolve(self.url)
            self.signals.result.emit({"plan": plan, "url": self.url})
        except Exception as exc:
            logger.exception("ProviderMetadataWorker failed: provider=%s url=%s", self.provider.name, self.url)
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


# Backwards-compatible alias (Spotify is currently the only non-YouTube provider).
SpotifyMetadataWorker = ProviderMetadataWorker
