"""Application logging configuration."""

from __future__ import annotations

import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.constants import APP_NAME, APP_VERSION, LOG_FILENAME
from app.core.paths import get_app_data_dir, get_log_dir

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> Path:
    global _CONFIGURED
    log_dir = get_log_dir()
    log_path = log_dir / LOG_FILENAME

    if _CONFIGURED:
        return log_path

    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    # Avoid duplicate handlers in repeated setup/test contexts.
    has_file_handler = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(log_path)
        for h in root.handlers
    )
    if not has_file_handler:
        root.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(stream_handler)

    _CONFIGURED = True
    return log_path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_startup_diagnostics(logger: logging.Logger | None = None) -> None:
    """Log environment/runtime info useful for troubleshooting packaged builds."""
    log = logger or get_logger(__name__)
    try:
        frozen = bool(getattr(sys, "frozen", False))
        log.info(
            "Startup: app=%s version=%s frozen=%s python=%s platform=%s app_data=%s",
            APP_NAME,
            APP_VERSION,
            frozen,
            sys.version.split()[0],
            platform.platform(),
            get_app_data_dir(),
        )
        try:
            from PySide6 import __version__ as pyside_version  # type: ignore

            log.info("Runtime: PySide6=%s", pyside_version)
        except Exception as exc:
            log.info("Runtime: PySide6 unavailable (%s)", exc)
        try:
            import yt_dlp  # type: ignore

            ver = getattr(yt_dlp, "version", None) or getattr(yt_dlp, "__version__", "unknown")
            log.info("Runtime: yt-dlp=%s", ver)
        except Exception as exc:
            log.info("Runtime: yt-dlp unavailable (%s)", exc)
        try:
            from app.engine.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path

            log.info("Runtime: ffmpeg=%s ffprobe=%s", get_ffmpeg_path(), get_ffprobe_path())
        except Exception as exc:
            log.info("Runtime: FFmpeg detection failed (%s)", exc)
    except Exception:
        # Diagnostics must never break startup.
        try:
            log.debug("Startup diagnostics logging failed", exc_info=True)
        except Exception:
            pass
