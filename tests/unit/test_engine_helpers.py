"""Unit tests for engine helpers and basic repo behavior."""

from __future__ import annotations

import unittest

from app.engine.progress_parser import parse_progress_hook
from app.engine.format_selector import normalize_formats, pick_format_for_quality


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
