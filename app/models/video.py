"""Video metadata model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormatOption:
    format_id: str
    label: str
    ext: Optional[str] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    note: Optional[str] = None


@dataclass
class VideoMetadata:
    source_url: str
    title: str = ""
    thumbnail_url: str = ""
    duration: Optional[int] = None
    uploader: Optional[str] = None
    is_playlist: bool = False
    formats: list[FormatOption] = field(default_factory=list)
