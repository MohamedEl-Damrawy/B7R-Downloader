"""Playlist metadata models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlaylistEntry:
    entry_id: str
    source_url: str
    title: str = ""
    thumbnail_url: str = ""
    index: Optional[int] = None
    available: bool = True


@dataclass
class PlaylistMetadata:
    source_url: str
    title: str = ""
    thumbnail_url: str = ""
    entries: list[PlaylistEntry] = field(default_factory=list)
    total_entries: int = 0
