"""Default provider registry.

Providers are consulted in registration order; the YouTube provider is
always registered last as the catch-all for generic yt-dlp URLs. Spotify is
registered by the Spotify provider module import (Phase B).
"""

from __future__ import annotations

from app.sources.base import SourceProvider

_PROVIDERS: list[SourceProvider] = []
_YOUTUBE_FALLBACK: SourceProvider | None = None


def register_provider(provider: SourceProvider, *, fallback: bool = False) -> None:
    """Register a provider. ``fallback=True`` marks the catch-all checked last."""
    global _YOUTUBE_FALLBACK
    if fallback:
        _YOUTUBE_FALLBACK = provider
        return
    if all(getattr(p, "name", "") != getattr(provider, "name", "") for p in _PROVIDERS):
        _PROVIDERS.append(provider)


def get_provider_for_url(url: str) -> SourceProvider | None:
    """Return the first provider that matches ``url`` (fallback included)."""
    _ensure_default_registry()
    value = (url or "").strip()
    for provider in _PROVIDERS:
        try:
            if provider.matches_url(value):
                return provider
        except Exception:
            continue
    if _YOUTUBE_FALLBACK is not None:
        try:
            if _YOUTUBE_FALLBACK.matches_url(value):
                return _YOUTUBE_FALLBACK
        except Exception:
            return None
    return None


def _reset_registry() -> None:
    """Test helper: clear all providers (including the fallback)."""
    global _YOUTUBE_FALLBACK
    _PROVIDERS.clear()
    _YOUTUBE_FALLBACK = None


def _ensure_default_registry() -> None:
    """Idempotently install the built-in providers (module import side effect)."""
    global _YOUTUBE_FALLBACK
    from app.sources.spotify import SpotifyProvider
    from app.sources.youtube import YouTubeProvider

    if _YOUTUBE_FALLBACK is None:
        _YOUTUBE_FALLBACK = YouTubeProvider()
    names = {getattr(p, "name", "") for p in _PROVIDERS}
    if "spotify" not in names:
        register_provider(SpotifyProvider())
