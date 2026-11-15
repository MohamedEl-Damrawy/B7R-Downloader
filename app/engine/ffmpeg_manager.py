"""FFmpeg discovery helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def kill_bundled_ffmpeg_orphans() -> int:
    """DL-09: terminate ffmpeg processes started by this app but left orphaned.

    Only processes whose ExecutablePath resolves inside the bundled vendor
    directory are killed — user/system ffmpeg installs are never touched.
    Best effort: returns the number of processes terminated.
    """
    if os.name != "nt":
        return 0
    bundled = get_vendor_ffmpeg_dir().resolve()
    candidates = {str(bundled), str((bundled / "bin").resolve())}
    exe = _exe_name("ffmpeg")
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='ffmpeg.exe'\" | "
        "Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
        )
        data = json.loads(out.stdout or "null")
        rows = data if isinstance(data, list) else ([data] if data else [])
    except Exception:
        return 0
    killed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        exe_path = str(row.get("ExecutablePath") or "").strip()
        try:
            resolved = str(Path(exe_path).resolve()) if exe_path else ""
        except Exception:
            continue
        parent = str(Path(resolved).parent) if resolved else ""
        if not resolved or not resolved.endswith(exe) or parent not in candidates:
            continue
        pid = row.get("ProcessId")
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                capture_output=True,
                timeout=10,
            )
            killed += 1
        except Exception:
            continue
    return killed
