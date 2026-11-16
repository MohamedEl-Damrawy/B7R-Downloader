"""Shared dataclasses and protocol for source providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class TrackSpec:
    """One downloadable item, normalized across all source providers.

    A TrackSpec either carries a direct media ``source_url`` (YouTube-like)
    or a ``search_query`` that the engine resolves via ``ytsearch1:`` with a
    duration sanity check (Spotify-matched tracks). Never both at once for
    matched downloads; ``source_url`` wins when both are set.
    """

    title: str
    artist: str = ""
    album: str = ""
    duration_sec: Optional[int] = None
    cover_url: str = ""
    source_url: str = ""
    source_type: str = "youtube"  # "youtube" | "spotify"
    search_query: str = ""  # non-empty => engine uses matched-download mode
    index: Optional[int] = None
    available: bool = True


@dataclass
class SourcePlan:
    """Resolved metadata for a user URL: one track or a list of tracks."""

    kind: str  # "track" | "playlist"
    title: str
    entries: list[TrackSpec] = field(default_factory=list)
    source_url: str = ""
    thumbnail_url: str = ""


class SourceError(Exception):
    """Raised by providers with an actionable, user-translatable message."""


@runtime_checkable
class SourceProvider(Protocol):
    """A source that can recognize and resolve user-pasted URLs."""

    name: str

    def matches_url(self, url: str) -> bool: ...

    def resolve(self, url: str) -> SourcePlan: ...
