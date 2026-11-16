"""Source-provider layer.

A SourceProvider maps a user-pasted URL into a normalized SourcePlan of
downloadable TrackSpec items. YouTube is the default provider (delegates to
yt-dlp); Spotify is a metadata provider whose tracks are matched to YouTube
Music audio at download time (see docs/architecture_notes.md).
"""

from __future__ import annotations

from app.sources.base import SourceError, SourcePlan, SourceProvider, TrackSpec
from app.sources.registry import get_provider_for_url, register_provider
from app.sources.spotify import SpotifyProvider

register_provider(SpotifyProvider())

__all__ = [
    "SourceError",
    "SourcePlan",
    "SourceProvider",
    "TrackSpec",
    "get_provider_for_url",
    "register_provider",
]
