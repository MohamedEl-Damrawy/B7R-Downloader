"""Unit tests for the source-provider layer (Spotify plan Phase A)."""

from __future__ import annotations

import unittest

from app.models.playlist import PlaylistEntry, PlaylistMetadata
from app.models.video import VideoMetadata
from app.sources import get_provider_for_url
from app.sources.registry import _reset_registry


class TestProviderRouting(unittest.TestCase):
    def tearDown(self):
        _reset_registry()

    def test_youtube_url_routes_to_youtube_fallback(self):
        p = get_provider_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "youtube")

    def test_generic_http_url_routes_to_youtube_fallback(self):
        p = get_provider_for_url("https://example.com/some/media")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "youtube")

    def test_spotify_url_not_registered_in_phase_a(self):
        # Spotify resolves in Phase B; until registered, Spotify URLs fall
        # through to the YouTube catch-all (yt-dlp will reject them, exactly
        # like before the provider layer existed).
        p = get_provider_for_url("https://open.spotify.com/playlist/abc")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "youtube")

    def test_invalid_url_returns_none(self):
        self.assertIsNone(get_provider_for_url("not a url"))
        self.assertIsNone(get_provider_for_url(""))


class TestYouTubeProvider(unittest.TestCase):
    def setUp(self):
        _reset_registry()
        from app.sources.youtube import YouTubeProvider

        self.provider = YouTubeProvider()

    def tearDown(self):
        _reset_registry()

    def test_matches_url(self):
        self.assertTrue(self.provider.matches_url("https://youtu.be/x"))
        self.assertFalse(self.provider.matches_url("not-a-url"))

    def test_resolve_track_maps_to_plan(self):
        from app.sources import youtube as yt_mod

        video = VideoMetadata(
            source_url="https://www.youtube.com/watch?v=x",
            title="Song",
            thumbnail_url="thumb",
            duration=200,
        )

        original = yt_mod.ytdlp_engine.extract_metadata

        def fake_extract(url, **kwargs):
            return video, None

        yt_mod.ytdlp_engine.extract_metadata = fake_extract
        try:
            plan = self.provider.resolve("https://www.youtube.com/watch?v=x")
        finally:
            yt_mod.ytdlp_engine.extract_metadata = original

        self.assertEqual(plan.kind, "track")
        self.assertEqual(plan.title, "Song")
        self.assertEqual(len(plan.entries), 1)
        track = plan.entries[0]
        self.assertEqual(track.title, "Song")
        self.assertEqual(track.source_url, "https://www.youtube.com/watch?v=x")
        self.assertEqual(track.source_type, "youtube")
        self.assertEqual(track.duration_sec, 200)
        self.assertEqual(track.cover_url, "thumb")
        self.assertTrue(track.available)

    def test_resolve_playlist_maps_entries(self):
        from app.sources import youtube as yt_mod

        playlist = PlaylistMetadata(
            source_url="https://www.youtube.com/playlist?list=PL1",
            title="My List",
            thumbnail_url="pl-thumb",
            entries=[
                PlaylistEntry(entry_id="1", source_url="https://youtu.be/a", title="A", index=1),
                PlaylistEntry(
                    entry_id="unavailable-2",
                    source_url="",
                    title="Unavailable (entry 2)",
                    index=2,
                    available=False,
                ),
            ],
            total_entries=2,
        )

        original = yt_mod.ytdlp_engine.extract_metadata

        def fake_extract(url, **kwargs):
            return None, playlist

        yt_mod.ytdlp_engine.extract_metadata = fake_extract
        try:
            plan = self.provider.resolve("https://www.youtube.com/playlist?list=PL1")
        finally:
            yt_mod.ytdlp_engine.extract_metadata = original

        self.assertEqual(plan.kind, "playlist")
        self.assertEqual(plan.title, "My List")
        self.assertEqual(len(plan.entries), 2)
        self.assertEqual(plan.entries[0].index, 1)
        self.assertTrue(plan.entries[0].available)
        self.assertFalse(plan.entries[1].available)
        self.assertEqual(plan.thumbnail_url, "pl-thumb")


class TestSpotifyUrlDetection(unittest.TestCase):
    def test_matches_spotify_https(self):
        from app.sources.spotify import SpotifyProvider

        p = SpotifyProvider()
        self.assertTrue(p.matches_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"))
        self.assertTrue(p.matches_url("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3"))
        self.assertTrue(p.matches_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"))
        self.assertTrue(p.matches_url("https://open.spotify.com/track/abc?si=xyz"))
        self.assertTrue(p.matches_url("https://www.open.spotify.com/track/abc"))

    def test_matches_spotify_uri(self):
        from app.sources.spotify import SpotifyProvider

        p = SpotifyProvider()
        self.assertTrue(p.matches_url("spotify:track:4uLU6hMCjMI75M1A2tKUQC"))
        self.assertTrue(p.matches_url("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"))

    def test_rejects_non_spotify(self):
        from app.sources.spotify import SpotifyProvider

        p = SpotifyProvider()
        self.assertFalse(p.matches_url("https://www.youtube.com/watch?v=x"))
        self.assertFalse(p.matches_url("https://spotify.example.com/track/x"))
        self.assertFalse(p.matches_url(""))
        self.assertFalse(p.matches_url("random text"))

    def test_resolve_not_implemented_in_phase_a(self):
        from app.sources.base import SourceError
        from app.sources.spotify import SpotifyProvider

        with self.assertRaises(SourceError):
            SpotifyProvider().resolve("https://open.spotify.com/track/x")


if __name__ == "__main__":
    unittest.main()
