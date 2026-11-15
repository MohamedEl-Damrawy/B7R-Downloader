"""Unit tests for engine helpers and basic repo behavior."""

from __future__ import annotations

import unittest

from app.engine.format_selector import audio_preset_for_quality, normalize_formats, pick_format_for_quality
from app.engine.progress_parser import parse_progress_hook
from app.engine.ytdlp_engine import _apply_network_opts, _build_postprocessors, _entry_is_unavailable, get_ytdlp_version


class TestEngineHelpers(unittest.TestCase):
    def test_parse_progress_hook_percentage_from_bytes(self):
        info = parse_progress_hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 200})
        self.assertEqual(info.status, "downloading")
        self.assertEqual(info.percentage, 25.0)
        self.assertEqual(info.downloaded_bytes, 50)
        self.assertEqual(info.total_bytes, 200)

    def test_parse_progress_hook_percent_string(self):
        info = parse_progress_hook({"status": "downloading", "_percent_str": "  42.5%"})
        self.assertEqual(info.percentage, 42.5)

    def test_parse_progress_hook_handles_missing(self):
        info = parse_progress_hook(None)
        self.assertEqual(info.status, "unknown")
        self.assertIsNone(info.percentage)
        info2 = parse_progress_hook({"status": "finished", "filename": "x.mp4"})
        self.assertEqual(info2.status, "finished")
        self.assertEqual(info2.filename, "x.mp4")

    def test_parse_progress_hook_postprocessing_passthrough(self):
        # Status strings injected by our postprocessor hooks pass through intact.
        info = parse_progress_hook({"status": "postprocessing", "postprocessor": "Merger"})
        self.assertEqual(info.status, "postprocessing")

    def test_entry_is_unavailable_markers(self):
        # DL-02: titles rendered by YouTube for unplayable playlist videos.
        for title in (
            "[Private video]",
            "[Deleted video]",
            "[Unavailable video]",
            "[Members-only video]",
            " [private video] ",
        ):
            self.assertTrue(_entry_is_unavailable(title), title)
        self.assertFalse(_entry_is_unavailable("My Normal Video Title"))
        self.assertFalse(_entry_is_unavailable(""))
        self.assertFalse(_entry_is_unavailable(None))

    def test_audio_preset_for_quality(self):
        self.assertEqual(audio_preset_for_quality("audio_mp3"), "mp3")
        self.assertEqual(audio_preset_for_quality("Audio_M4A"), "m4a")
        self.assertIsNone(audio_preset_for_quality("best"))
        self.assertIsNone(audio_preset_for_quality(""))
        self.assertIsNone(audio_preset_for_quality("720p"))

    def test_pick_format_for_quality_audio_presets(self):
        self.assertEqual(pick_format_for_quality([], "audio_mp3"), "bestaudio/best")
        self.assertEqual(pick_format_for_quality([], "audio_m4a"), "bestaudio/best")

    def test_build_postprocessors(self):
        # FEAT-01/02/03: postprocessor list composition.
        self.assertEqual(_build_postprocessors(), [])
        pps = _build_postprocessors(audio_format="mp3")
        self.assertEqual(pps[0]["key"], "FFmpegExtractAudio")
        self.assertEqual(pps[0]["preferredcodec"], "mp3")
        pps = _build_postprocessors(embed_metadata=True, embed_thumbnail=True, sponsorblock=True)
        keys = [pp["key"] for pp in pps]
        self.assertEqual(keys, ["SponsorBlock", "EmbedThumbnail", "FFmpegMetadata"])

    def test_apply_network_opts(self):
        # DL-07/FEAT-04/05: cookies/proxy plumbed into yt-dlp options.
        opts: dict = {}
        _apply_network_opts(opts)
        self.assertEqual(opts, {})
        _apply_network_opts(opts, cookiefile=" C:\\cookies.txt ", proxy=" http://127.0.0.1:8080 ")
        self.assertEqual(opts["cookiefile"], "C:\\cookies.txt")
        self.assertEqual(opts["proxy"], "http://127.0.0.1:8080")
        # Empty values are ignored, not set.
        opts2: dict = {}
        _apply_network_opts(opts2, cookiefile="", proxy="  ")
        self.assertEqual(opts2, {})

    def test_get_ytdlp_version(self):
        self.assertNotEqual(get_ytdlp_version(), "")

    def test_pick_format_for_quality_presets_and_id(self):
        self.assertEqual(pick_format_for_quality([], "best"), "bv*+ba/b")
        sel = pick_format_for_quality([], "720p")
        self.assertIn("720", sel or "")
        self.assertEqual(pick_format_for_quality([], "id:137"), "137+ba/137/b")
        self.assertEqual(pick_format_for_quality([], "unknown"), "bv*+ba/b")

    def test_normalize_formats(self):
        raw = [
            {"format_id": "22", "ext": "mp4", "height": 720, "format_note": "720p"},
            {"format_id": "", "ext": "mp4"},
            "bad",
        ]
        fmts = normalize_formats(raw)
        self.assertEqual(len(fmts), 1)
        self.assertEqual(fmts[0].format_id, "22")
        self.assertEqual(fmts[0].height, 720)
        self.assertIn("720p", fmts[0].label)


if __name__ == "__main__":
    unittest.main()
