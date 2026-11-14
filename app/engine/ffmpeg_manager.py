"""FFmpeg discovery helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from app.core.paths import get_vendor_ffmpeg_dir


def _exe_name(base: str) -> str:
    return f"{base}.exe" if os.name == "nt" else base


def _candidate_paths() -> list[Path]:
    base = get_vendor_ffmpeg_dir()
    return [base, base / "bin"]


def find_bundled_binary(name: str) -> Optional[Path]:
    exe = _exe_name(name)
    for d in _candidate_paths():
        p = d / exe
        if p.exists():
            return p
    # Development fallback: PATH (not relied upon for packaged app)
    which = shutil.which(exe)
    return Path(which) if which else None


def get_ffmpeg_path() -> Optional[Path]:
    return find_bundled_binary("ffmpeg")


def get_ffprobe_path() -> Optional[Path]:
    return find_bundled_binary("ffprobe")


def get_ffmpeg_location_for_ytdlp() -> Optional[str]:
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    if ffmpeg and ffprobe and ffmpeg.parent == ffprobe.parent:
        return str(ffmpeg.parent)
    if ffmpeg:
        return str(ffmpeg.parent)
    return None
