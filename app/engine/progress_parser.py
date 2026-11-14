"""Normalize yt-dlp progress hook payloads."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class ProgressInfo:
    status: str = "unknown"
    percentage: Optional[float] = None
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[int] = None
    filename: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def parse_progress_hook(data: dict[str, Any] | None) -> ProgressInfo:
    if not isinstance(data, dict):
        return ProgressInfo()

    status = str(data.get("status") or "unknown")
    downloaded = _safe_int(data.get("downloaded_bytes"))
    total = _safe_int(data.get("total_bytes") or data.get("total_bytes_estimate"))

    percentage = None
    pct_raw = data.get("_percent_str")
    if isinstance(pct_raw, str):
        cleaned = pct_raw.strip().replace("%", "").strip()
        percentage = _safe_float(cleaned)
    if percentage is None and downloaded is not None and total:
        try:
            percentage = (downloaded / total) * 100.0
        except Exception:
            percentage = None
    if percentage is not None:
        # yt-dlp sometimes provides values like 12.3 or "12.3%" parsed oddly; clamp
        percentage = max(0.0, min(100.0, percentage))

    return ProgressInfo(
        status=status,
        percentage=percentage,
        downloaded_bytes=downloaded,
        total_bytes=total,
        speed=_safe_float(data.get("speed")),
        eta=_safe_int(data.get("eta")),
        filename=data.get("filename") or data.get("_filename"),
        error=None,
    )
