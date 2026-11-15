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
    # DL-09: clean up ffmpeg processes orphaned by a previous unclean exit.
    # Scoped strictly to the bundled vendor binary; best effort, never fatal.
    try:
        from app.engine.ffmpeg_manager import kill_bundled_ffmpeg_orphans

        orphans = kill_bundled_ffmpeg_orphans()
        if orphans:
            logger.info("Startup cleanup: terminated %s orphaned bundled ffmpeg process(es)", orphans)
    except Exception:
        logger.debug("Orphan ffmpeg cleanup skipped/failed", exc_info=True)
    logger.info("Bootstrap complete. app_data=%s log=%s", get_app_data_dir(), log_path)
