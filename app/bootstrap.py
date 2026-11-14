"""Application bootstrap and wiring."""

from __future__ import annotations

from app.core.logger import configure_logging, get_logger, log_startup_diagnostics
from app.core.paths import ensure_runtime_directories, get_app_data_dir
from app.database.migrations import apply_migrations


def bootstrap() -> None:
    ensure_runtime_directories()
    log_path = configure_logging()
    logger = get_logger(__name__)
    log_startup_diagnostics(logger)
    try:
        apply_migrations()
        from app.database.repositories.download_items_repo import DownloadItemsRepository
        from app.database.repositories.downloads_repo import DownloadsRepository

        items_interrupted = DownloadItemsRepository().mark_interrupted()
        interrupted = DownloadsRepository().mark_interrupted()
        if interrupted or items_interrupted:
            logger.info(
                "Startup recovery: marked %s downloads and %s playlist items as failed",
                interrupted,
                items_interrupted,
            )
    except Exception:
        logger.exception("Startup recovery/migrations issue")
    logger.info("Bootstrap complete. app_data=%s log=%s", get_app_data_dir(), log_path)
