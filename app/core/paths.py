"""Filesystem path helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.core.constants import APP_DATA_DIR_NAME, CACHE_DIR_NAME, DB_FILENAME, LOG_DIR_NAME, TEMP_DIR_NAME


def ensure_runtime_directories() -> None:
    get_app_data_dir()
    get_log_dir()
    get_cache_dir()
    get_temp_dir()
    get_default_download_dir()


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> Path:
    # In frozen builds, prefer the executable directory for writable-adjacent context.
    if is_frozen():
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
    return Path(__file__).resolve().parents[2]


def _frozen_bundle_candidates() -> list[Path]:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass))
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir, exe_dir / "_internal"])
    except Exception:
        pass
    # de-duplicate preserving order
    out: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        k = str(c)
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def _resolve_bundle_path(relative: str) -> Path:
    rel = Path(relative)
    if is_frozen():
        for base in _frozen_bundle_candidates():
            p = base / rel
            if p.exists():
                return p
        # fallback to first candidate or exe dir
        cands = _frozen_bundle_candidates()
        if cands:
            return cands[0] / rel
    return get_project_root() / rel


def get_app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / "AppData" / "Local"
    path = root / APP_DATA_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_app_data_dir() / DB_FILENAME


def get_log_dir() -> Path:
    path = get_app_data_dir() / LOG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    path = get_app_data_dir() / CACHE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_dir() -> Path:
    path = get_app_data_dir() / TEMP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_download_dir() -> Path:
    path = Path.home() / "Downloads" / APP_DATA_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_resources_dir() -> Path:
    return _resolve_bundle_path("resources")


def get_vendor_ffmpeg_dir() -> Path:
    return _resolve_bundle_path(os.path.join("vendor", "ffmpeg"))


def get_licenses_dir() -> Path:
    return _resolve_bundle_path("licenses")
