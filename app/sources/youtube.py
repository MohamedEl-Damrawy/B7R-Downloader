"""YouTube provider: default catch-all delegating to the yt-dlp engine."""

from __future__ import annotations

from typing import Optional

from app.core.validators import is_http_url
from app.engine import ytdlp_engine
from app.sources.base import SourcePlan, TrackSpec


class YouTubeProvider:
    """Wraps the existing yt-dlp metadata extraction into SourcePlan form.

    Behavior is intentionally identical to the legacy metadata path: the
    controller still calls ``ytdlp_engine.extract_metadata`` directly for
    YouTube URLs; this adapter exists so future providers (Spotify) share
    one normalized plan/track shape.
    """

    name = "youtube"

    def matches_url(self, url: str) -> bool:
        # Catch-all: any valid http(s) URL is handled by yt-dlp.
        return is_http_url(url)

    def resolve(
        self,
        url: str,
        *,
        ffmpeg_location: Optional[str] = None,
        cookiefile: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> SourcePlan:
        video, playlist = ytdlp_engine.extract_metadata(
            url,
            ffmpeg_location=ffmpeg_location,
            cookiefile=cookiefile,
            proxy=proxy,
        )
        if playlist is not None:
            entries = [
                TrackSpec(
                    title=e.title,
                    source_url=e.source_url,
                    cover_url=e.thumbnail_url or "",
                    source_type="youtube",
                    index=e.index,
                    available=e.available,
                )
                for e in playlist.entries
            ]
            return SourcePlan(
                kind="playlist",
                title=playlist.title,
                entries=entries,
                source_url=playlist.source_url,
                thumbnail_url=playlist.thumbnail_url,
            )
        if video is not None:
            track = TrackSpec(
                title=video.title,
                source_url=video.source_url,
                cover_url=video.thumbnail_url or "",
                duration_sec=int(video.duration) if video.duration else None,
                source_type="youtube",
            )
            return SourcePlan(
                kind="track",
                title=video.title,
                entries=[track],
                source_url=video.source_url,
                thumbnail_url=video.thumbnail_url or "",
            )
        raise ValueError("No metadata was returned.")
