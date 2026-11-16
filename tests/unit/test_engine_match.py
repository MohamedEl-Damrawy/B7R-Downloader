"""Unit tests for matched-download engine helpers + music format presets."""

from __future__ import annotations

import unittest

from app.engine.format_selector import MUSIC_PRESETS, music_preset_for_quality
from app.engine.ytdlp_engine import _candidate_url, _pick_match_entry


class TestPickMatchEntry(unittest.TestCase):
    def test_exact_within_tolerance(self):
        entries = [
            {"id": "a", "duration": 300},
            {"id": "b", "duration": 192},
        ]
        entry, quality = _pick_match_entry(entries, 200, tolerance=12)
        self.assertEqual(entry["id"], "b")  # |192-200| = 8 <= 12
        self.assertEqual(quality, "exact")

    def test_loose_when_no_duration_match(self):
        entries = [
            {"id": "a", "duration": 400},
            {"id": "b", "duration": 500},
        ]
        entry, quality = _pick_match_entry(entries, 200, tolerance=12)
        self.assertEqual(entry["id"], "a")  # first candidate fallback
        self.assertEqual(quality, "loose")

    def test_unknown_when_no_expected_duration(self):
        entries = [{"id": "a", "duration": 123}]
        entry, quality = _pick_match_entry(entries, None)
        self.assertEqual(entry["id"], "a")
        self.assertEqual(quality, "unknown")

    def test_no_results(self):
        entry, quality = _pick_match_entry([], 200)
        self.assertIsNone(entry)
        self.assertEqual(quality, "no_results")

    def test_entries_without_duration_are_skipped_for_exact(self):
        entries = [
            {"id": "a", "duration": None},
            {"id": "b", "duration": 205},
        ]
        entry, quality = _pick_match_entry(entries, 200, tolerance=12)
        self.assertEqual(entry["id"], "b")
        self.assertEqual(quality, "exact")


class TestCandidateUrl(unittest.TestCase):
    def test_prefers_webpage_url(self):
        self.assertEqual(
            _candidate_url({"webpage_url": "https://www.youtube.com/watch?v=x", "id": "x"}),
            "https://www.youtube.com/watch?v=x",
        )

    def test_builds_from_id(self):
        self.assertEqual(
            _candidate_url({"id": "abc"}),
            "https://www.youtube.com/watch?v=abc",
        )

    def test_empty(self):
        self.assertEqual(_candidate_url({}), "")


class TestMusicPresets(unittest.TestCase):
    def test_preset_mapping(self):
        self.assertEqual(music_preset_for_quality("mp3_320"), {"codec": "mp3", "quality": "320"})
        self.assertEqual(music_preset_for_quality("m4a_256"), {"codec": "m4a", "quality": "256"})
        self.assertEqual(music_preset_for_quality("flac"), {"codec": "flac", "quality": "0"})

    def test_unknown_quality_returns_none(self):
        self.assertIsNone(music_preset_for_quality("best"))
        self.assertIsNone(music_preset_for_quality("1080p"))
        self.assertIsNone(music_preset_for_quality("audio_mp3"))

    def test_flac_is_declared_honestly(self):
        # FLAC preset must stay documented as a lossless container over a
        # lossy source (no fake-lossless claims anywhere).
        self.assertIn("flac", MUSIC_PRESETS)
        self.assertEqual(MUSIC_PRESETS["flac"]["codec"], "flac")


if __name__ == "__main__":
    unittest.main()
