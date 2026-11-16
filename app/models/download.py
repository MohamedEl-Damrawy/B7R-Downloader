"""Download domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.models.download_status import DownloadStatus


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class DownloadTask:
    id: str
    source_url: str
    title: str = ""
    thumbnail_url: str = ""
    selected_format: str = "best"
    output_path: str = ""
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[int] = None
    error_message: Optional[str] = None
    playlist_id: Optional[str] = None
    playlist_items: Optional[str] = None  # PERF-04: persisted for correct retry of batch tasks
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None
