"""Spotify metadata provider (Option A).

Spotify supplies *metadata only* (title/artist/album/duration/cover). Audio
streams are DRM-encrypted and are never touched; resolved tracks are matched
to YouTube Music by the engine at download time (``search_query`` +
duration gate). Credentials: Client ID/Secret from Settings (free from the
Spotify Developer Dashboard, client-credentials flow) with a best-effort
anonymous fallback; errors are actionable, never silent empty playlists.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional
from urllib.parse import urlparse

from app.core.logger import get_logger
from app.sources.base import SourceError, SourcePlan, SourceProvider, TrackSpec
from app.sources.match import build_search_query

logger = get_logger(__name__)

_KNOWLEDGE_HOSTS = ("open.spotify.com", "play.spotify.com")
_KINDS = ("track", "album", "playlist")

_CREDENTIALS_MESSAGE = (
    "Spotify metadata needs API credentials. Open Settings and enter a free "
    "Spotify Client ID and Secret (from the Spotify Developer Dashboard), "
    "then try again."
)

# Simple client-side politeness throttle (~1 request/second) on top of
# spotipy's Retry-After handling for 429s.
_MIN_REQUEST_INTERVAL = 1.0
_throttle_lock = threading.Lock()
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    with _throttle_lock:
        now = time.monotonic()
        wait = _MIN_REQUEST_INTERVAL - (now - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        _last_request_ts = time.monotonic()


def parse_spotify_url(url: str) -> Optional[tuple[str, str]]:
    """Return (kind, id) for a Spotify URL/URI, or None for anything else."""
    value = (url or "").strip()
    if not value:
        return None
    if value.lower().startswith("spotify:"):
        parts = value.split(":")
        if len(parts) >= 3 and parts[1].lower() in _KINDS:
            return parts[1].lower(), parts[2].split("?")[0]
        return None
    try:
        parsed = urlparse(value if "://" in value else f"https://{value}")
    except Exception:
        return None
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in _KNOWLEDGE_HOSTS:
        return None
    segments = [s for s in (parsed.path or "").split("/") if s]
    if len(segments) >= 2 and segments[0].lower() in _KINDS:
        return segments[0].lower(), segments[1].split("?")[0]
    return None


class SpotifyCredentialsError(SourceError):
    """Raised when no usable credentials path is available."""


def _credentials_from_settings() -> tuple[str, str]:
    try:
        from app.core.constants import SETTINGS_SPOTIFY_CLIENT_ID, SETTINGS_SPOTIFY_CLIENT_SECRET
        from app.services.settings_service import SettingsService

        svc = SettingsService()
        client_id = str(svc.get(SETTINGS_SPOTIFY_CLIENT_ID) or "").strip()
        client_secret = str(svc.get(SETTINGS_SPOTIFY_CLIENT_SECRET) or "").strip()
        return client_id, client_secret
    except Exception:
        logger.debug("Could not read Spotify credentials from settings", exc_info=True)
        return "", ""


def _anonymous_token() -> str:
    """Best-effort anonymous token (community endpoint; may stop working)."""
    try:
        import requests

        resp = requests.get(
            "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
            headers={"User-Agent": "Mozilla/5.0", "App-Platform": "WebPlayer"},
            timeout=10,
        )
        data = resp.json() if resp.ok else {}
        token = str(data.get("accessToken") or "").strip()
        if token:
            logger.info("Spotify: anonymous fallback token acquired")
        return token
    except Exception:
        logger.info("Spotify: anonymous fallback token unavailable", exc_info=True)
        return ""


def _create_client() -> Any:
    """Build a spotipy client: settings credentials first, anonymous fallback."""
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    client_id, client_secret = _credentials_from_settings()
    if client_id and client_secret:
        logger.info("Spotify: using client-credentials from Settings")
        return spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            ),
            requests_timeout=15,
            retries=3,
        )
    token = _anonymous_token()
    if token:
        return spotipy.Spotify(auth=token, requests_timeout=15, retries=3)
    raise SpotifyCredentialsError(_CREDENTIALS_MESSAGE)


def _track_to_spec(track: dict, index: Optional[int], album_name: str = "", cover_url: str = "") -> TrackSpec:
    artists = track.get("artists") or []
    artist = ""
    for a in artists:
        name = (a or {}).get("name")
        if name:
            artist = str(name)
            break
    name = str(track.get("name") or "")
    album = str(album_name or (track.get("album") or {}).get("name") or "")
    duration_ms = track.get("duration_ms")
    duration = int(duration_ms // 1000) if duration_ms else None
    images = ((track.get("album") or {}).get("images") or [])
    if not cover_url and images:
        cover_url = str(images[0].get("url") or "")
    return TrackSpec(
        title=name,
        artist=artist,
        album=album,
        duration_sec=duration,
        cover_url=cover_url,
        source_url=f"https://open.spotify.com/track/{track.get('id') or ''}",
        source_type="spotify",
        search_query=build_search_query(name, artist),
        index=index,
        # Local-file entries in playlists are not real streamable tracks.
        available=not bool(track.get("is_local")),
    )


class SpotifyProvider(SourceProvider):
    """Metadata provider for Spotify track/album/playlist URLs."""

    name = "spotify"

    def __init__(self, client: Any = None):
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = _create_client()
        return self._client

    def matches_url(self, url: str) -> bool:
        return parse_spotify_url(url) is not None

    def resolve(self, url: str) -> SourcePlan:
        parsed = parse_spotify_url(url)
        if not parsed:
            raise SourceError("Not a Spotify URL.")
        kind, obj_id = parsed
        _throttle()
        try:
            sp = self._get_client()
            if kind == "track":
                return self._resolve_track(sp, obj_id, url)
            if kind == "album":
                return self._resolve_album(sp, obj_id, url)
            return self._resolve_playlist(sp, obj_id, url)
        except SourceError:
            raise
        except Exception as exc:
            logger.exception("Spotify resolve failed: url=%s", url)
            raise SourceError(f"Spotify metadata error: {exc}") from exc

    def _resolve_track(self, sp, track_id: str, url: str) -> SourcePlan:
        track = sp.track(track_id)
        spec = _track_to_spec(track or {}, index=1)
        return SourcePlan(
            kind="track",
            title=spec.title,
            entries=[spec],
            source_url=url,
            thumbnail_url=spec.cover_url,
        )

    def _resolve_album(self, sp, album_id: str, url: str) -> SourcePlan:
        album = sp.album(album_id) or {}
        album_name = str(album.get("name") or "Album")
        cover_url = ""
        images = album.get("images") or []
        if images:
            cover_url = str(images[0].get("url") or "")
        entries: list[TrackSpec] = []
        index = 0
        results = sp.album_tracks(album_id) or {}
        while True:
            for item in results.get("items") or []:
                index += 1
                spec = _track_to_spec(item or {}, index=index, album_name=album_name, cover_url=cover_url)
                entries.append(spec)
            nxt = (results.get("next") or "")
            if not nxt:
                break
            _throttle()
            results = sp.next(results) or {}
        return SourcePlan(
            kind="playlist",
            title=album_name,
            entries=entries,
            source_url=url,
            thumbnail_url=cover_url,
        )

    def _resolve_playlist(self, sp, playlist_id: str, url: str) -> SourcePlan:
        playlist = sp.playlist(playlist_id) or {}
        title = str(playlist.get("name") or "Playlist")
        cover_url = ""
        images = playlist.get("images") or []
        if images:
            cover_url = str(images[0].get("url") or "")
        entries: list[TrackSpec] = []
        index = 0
        results = sp.playlist_items(playlist_id) or {}
        while True:
            for item in results.get("items") or []:
                index += 1
                track = (item or {}).get("track") or {}
                if not track:
                    continue
                entries.append(_track_to_spec(track, index=index, cover_url=cover_url))
            nxt = (results.get("next") or "")
            if not nxt:
                break
            _throttle()
            results = sp.next(results) or {}
        return SourcePlan(
            kind="playlist",
            title=title,
            entries=entries,
            source_url=url,
            thumbnail_url=cover_url,
        )
