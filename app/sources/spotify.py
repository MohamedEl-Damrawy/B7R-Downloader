"""Spotify provider skeleton (Phase A).

``matches_url`` is final; ``resolve`` lands in Phase B with the spotipy-based
metadata client (client-credentials from Settings + anonymous fallback).
Registered in the default registry in Phase B, when resolve is implemented.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.sources.base import SourceError, SourcePlan


def is_spotify_url(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value:
        return False
    if value.startswith("spotify:"):
        return True
    try:
        parsed = urlparse(value if "://" in value else f"https://{value}")
    except Exception:
        return False
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host in ("open.spotify.com", "play.spotify.com")


class SpotifyProvider:
    """Metadata provider for Spotify track/album/playlist URLs.

    Audio never comes from Spotify (DRM-encrypted streams); resolved tracks
    are matched to YouTube Music at download time (Option A, owner-approved).
    """

    name = "spotify"

    def matches_url(self, url: str) -> bool:
        return is_spotify_url(url)

    def resolve(self, url: str) -> SourcePlan:
        raise SourceError(
            "Spotify support is not implemented yet (Phase B of the approved plan)."
        )
