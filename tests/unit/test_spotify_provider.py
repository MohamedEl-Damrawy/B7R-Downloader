"""Unit tests for the Spotify provider with a mocked spotipy client (no network)."""

from __future__ import annotations

import unittest

from app.sources.base import SourceError
from app.sources.spotify import (
    SpotifyCredentialsError,
    SpotifyProvider,
    parse_spotify_url,
)


def _track(name="Song", artist="Artist", album=None, duration_ms=200000, track_id="id1", is_local=False, images=None):
    data = {
        "id": track_id,
        "name": name,
        "duration_ms": duration_ms,
        "is_local": is_local,
        "artists": [{"name": artist}] if artist else [],
    }
    if album is not None or images is not None:
        data["album"] = {"name": album or "", "images": images or []}
    return data


class _FakeSpotify:
    """Offline stand-in covering spotipy calls used by SpotifyProvider."""

    def __init__(self, track=None, album=None, playlist=None):
        self._track = track or _track()
        self._album = album or {
            "name": "Album X",
            "images": [{"url": "https://img/cover.jpg"}],
            "tracks": {"items": []},
        }
        self._playlist = playlist or {"name": "Playlist P", "images": [], "tracks": {"items": []}}
        self.album_tracks_page = {"items": [_track(name="T1", album=None)], "next": None}

    def track(self, track_id):
        return self._track

    def album(self, album_id):
        return self._album

    def album_tracks(self, album_id):
        return self.album_tracks_page

    def playlist(self, playlist_id):
        return self._playlist

    def playlist_items(self, playlist_id, offset=0):
        return {
            "items": [{"track": _track(name=f"Track {i}")} for i in range(1, 4)],
            "next": None,
        }


class TestParseSpotifyUrl(unittest.TestCase):
    def test_https_kinds(self):
        self.assertEqual(
            parse_spotify_url("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"),
            ("track", "4uLU6hMCjMI75M1A2tKUQC"),
        )
        self.assertEqual(parse_spotify_url("https://open.spotify.com/album/abc?si=xyz"), ("album", "abc"))
        self.assertEqual(
            parse_spotify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"),
            ("playlist", "37i9dQZF1DXcBWIGoYBM5M"),
        )

    def test_uri_kinds(self):
        self.assertEqual(parse_spotify_url("spotify:track:id123"), ("track", "id123"))
        self.assertEqual(parse_spotify_url("spotify:album:id123"), ("album", "id123"))

    def test_non_spotify(self):
        self.assertIsNone(parse_spotify_url("https://www.youtube.com/watch?v=x"))
        self.assertIsNone(parse_spotify_url("https://open.spotify.com/episode/xyz"))  # unsupported kind
        self.assertIsNone(parse_spotify_url("spotify:episode:xyz"))
        self.assertIsNone(parse_spotify_url(""))


class TestSpotifyResolve(unittest.TestCase):
    def test_resolve_track_maps_metadata(self):
        sp = _FakeSpotify(track=_track(
            name="Blinding Lights",
            artist="The Weeknd",
            album="After Hours",
            duration_ms=200000,
            images=[{"url": "https://img/a.jpg"}],
        ))
        plan = SpotifyProvider(client=sp).resolve("https://open.spotify.com/track/id1")
        self.assertEqual(plan.kind, "track")
        self.assertEqual(len(plan.entries), 1)
        t = plan.entries[0]
        self.assertEqual(t.title, "Blinding Lights")
        self.assertEqual(t.artist, "The Weeknd")
        self.assertEqual(t.album, "After Hours")
        self.assertEqual(t.duration_sec, 200)
        self.assertEqual(t.cover_url, "https://img/a.jpg")
        self.assertEqual(t.source_type, "spotify")
        self.assertEqual(t.search_query, "The Weeknd - Blinding Lights")
        self.assertEqual(plan.source_url, "https://open.spotify.com/track/id1")

    def test_resolve_album_uses_album_cover_and_paging_stop(self):
        sp = _FakeSpotify()
        plan = SpotifyProvider(client=sp).resolve("https://open.spotify.com/album/aid")
        self.assertEqual(plan.kind, "playlist")
        self.assertEqual(plan.title, "Album X")
        self.assertEqual(len(plan.entries), 1)
        t = plan.entries[0]
        self.assertEqual(t.album, "Album X")
        self.assertEqual(t.cover_url, "https://img/cover.jpg")
        self.assertEqual(t.index, 1)
        self.assertEqual(t.search_query, "Artist - T1")

    def test_resolve_playlist_indexes_entries(self):
        sp = _FakeSpotify()
        plan = SpotifyProvider(client=sp).resolve("https://open.spotify.com/playlist/pid")
        self.assertEqual(plan.kind, "playlist")
        self.assertEqual(plan.title, "Playlist P")
        self.assertEqual([t.index for t in plan.entries], [1, 2, 3])
        self.assertTrue(all(t.available for t in plan.entries))

    def test_local_entries_marked_unavailable(self):
        sp = _FakeSpotify()
        sp._playlist = {"name": "P", "images": [], "tracks": {"items": []}}
        # Emulate one local + one real track
        sp.playlist_items = lambda playlist_id, offset=0: {
            "items": [
                {"track": _track(name="Local", is_local=True)},
                {"track": _track(name="Real")},
            ],
            "next": None,
        }
        plan = SpotifyProvider(client=sp).resolve("https://open.spotify.com/playlist/pid")
        self.assertFalse(plan.entries[0].available)
        self.assertTrue(plan.entries[1].available)


class TestCredentialsPath(unittest.TestCase):
    def test_missing_credentials_raises_actionable_error(self):
        import app.sources.spotify as sp_mod

        original_creds = sp_mod._credentials_from_settings
        original_anon = sp_mod._anonymous_token
        sp_mod._credentials_from_settings = lambda: ("", "")
        sp_mod._anonymous_token = lambda: ""
        try:
            with self.assertRaises(SpotifyCredentialsError):
                sp_mod._create_client()
        finally:
            sp_mod._credentials_from_settings = original_creds
            sp_mod._anonymous_token = original_anon

    def test_resolve_raises_source_error_on_client_failure(self):
        class FailingClient:
            def playlist(self, playlist_id):
                raise RuntimeError("api down")

        with self.assertRaises(SourceError):
            SpotifyProvider(client=FailingClient()).resolve("https://open.spotify.com/playlist/pid")


class TestFeb2026PlaylistEndpoint(unittest.TestCase):
    """Spotify's Feb-2026 rename: GET /playlists/{id}/tracks -> /items."""

    def test_new_endpoint_shape_used_when_legacy_missing(self):
        from app.sources.spotify import SpotifyProvider

        meta = {"name": "Playlist P", "images": []}

        class NewApiOnlyClient:
            """Post-2026-02-11 Development Mode app: no legacy endpoint."""

            def __init__(self, page):
                self._page = page

            def playlist(self, playlist_id):
                return meta

            def _get(self, path, **kwargs):
                assert "/items" in path
                return self._page

        page = {
            "items": [
                {"item": _track(name=f"T{i}")} for i in range(1, 3)
            ],
            "next": None,
        }
        plan = SpotifyProvider(client=NewApiOnlyClient(page)).resolve(
            "https://open.spotify.com/playlist/pid"
        )
        self.assertEqual([t.title for t in plan.entries], ["T1", "T2"])
        self.assertEqual([t.index for t in plan.entries], [1, 2])

    def test_both_endpoints_failing_is_actionable(self):
        from app.sources.spotify import _PLAYLIST_ACCESS_MESSAGE, SpotifyProvider

        meta = {"name": "P", "images": []}

        class NoAccessClient:
            def playlist(self, playlist_id):
                return meta

            def playlist_items(self, playlist_id):
                raise RuntimeError("404 legacy removed")

            def _get(self, path, **kwargs):
                raise RuntimeError("403 not owned")

        with self.assertRaises(SourceError) as ctx:
            SpotifyProvider(client=NoAccessClient()).resolve(
                "https://open.spotify.com/playlist/pid"
            )
        self.assertIn("not accessible", str(ctx.exception))
        self.assertTrue(_PLAYLIST_ACCESS_MESSAGE)


if __name__ == "__main__":
    unittest.main()
