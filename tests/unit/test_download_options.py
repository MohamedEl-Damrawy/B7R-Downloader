"""Unit tests for yt-dlp option construction in download_media (FEAT-01/02/03 plumbing).

download_media is exercised against a fake yt_dlp module so the composed
options dict can be asserted without any network access.
"""

from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from typing import Any

import app.engine.ytdlp_engine as mod

_CAPTURING: list[dict[str, Any]] = []


class _FakeYoutubeDL:
    last_opts: dict[str, Any] = {}

    def __init__(self, opts: dict[str, Any]) -> None:
        _CAPTURING.append(opts)
        self.opts = opts

    def __enter__(self) -> "_FakeYoutubeDL":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        return {"id": "abc123", "title": "Test Title", "ext": "mp4", "filepath": "x.mp4"}


def _fake_lazy():
    return SimpleNamespace(YoutubeDL=_FakeYoutubeDL, version=SimpleNamespace(__version__="2026.10.26"))


class TestDownloadOptions(unittest.TestCase):
    def setUp(self) -> None:
        _CAPTURING.clear()
        self._orig = mod._lazy_yt_dlp
        mod._lazy_yt_dlp = _fake_lazy  # type: ignore[assignment]
        self.addCleanup(setattr, mod, "_lazy_yt_dlp", self._orig)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        mod.download_media(
            url="https://example.com/watch?v=1",
            output_dir=self.tmpdir.name,
            **kwargs,
        )
        return _CAPTURING[-1]

    def test_defaults_video_merge(self):
        opts = self._run()
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertNotIn("postprocessors", opts)
        self.assertEqual(opts["format"], "bv*+ba/b")
        # DL-11: bounded generated file names.
        self.assertIn("trim_file_name", opts)
        self.assertNotIn("cookiefile", opts)

    def test_audio_only_preset(self):
        # FEAT-01: audio-only uses bestaudio, drops the video merge container,
        # and adds FFmpegExtractAudio with the target codec.
        opts = self._run(audio_format="mp3")
        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertNotIn("merge_output_format", opts)
        pp = opts["postprocessors"][0]
        self.assertEqual(pp["key"], "FFmpegExtractAudio")
        self.assertEqual(pp["preferredcodec"], "mp3")

    def test_subs_and_embed_options(self):
        # FEAT-02: subtitles are written and metadata/thumbnail embedded.
        opts = self._run(write_subs=True, embed_metadata=True, embed_thumbnail=True)
        self.assertTrue(opts["writesubtitles"])
        self.assertEqual(opts["subtitleslangs"], ["en.*", "ar.*"])
        keys = [pp["key"] for pp in opts["postprocessors"]]
        self.assertIn("EmbedThumbnail", keys)
        self.assertIn("FFmpegMetadata", keys)

    def test_network_opts(self):
        # DL-07/FEAT-04/05: cookiefile/proxy reach yt-dlp options.
        opts = self._run(cookiefile="C:\\cookies.txt", proxy="http://127.0.0.1:8080")
        self.assertEqual(opts["cookiefile"], "C:\\cookies.txt")
        self.assertEqual(opts["proxy"], "http://127.0.0.1:8080")

    def test_noplaylist_with_playlist_items(self):
        opts = self._run(playlist_items="2-3")
        self.assertFalse(opts["noplaylist"])
        self.assertEqual(opts["playlist_items"], "2-3")


if __name__ == "__main__":
    unittest.main()
