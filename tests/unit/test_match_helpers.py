"""Unit tests for match helpers (query building + duration gate)."""

from __future__ import annotations

import unittest

from app.sources.match import (
    DURATION_TOLERANCE_SEC,
    build_search_query,
    clean_title,
    duration_within_tolerance,
)


class TestCleanTitle(unittest.TestCase):
    def test_strips_parenthesized_noise(self):
        self.assertEqual(clean_title("Song Name (Official Video)"), "Song Name")
        self.assertEqual(clean_title("Song Name (Official Music Video)"), "Song Name")
        self.assertEqual(clean_title("Song Name (Audio)"), "Song Name")
        self.assertEqual(clean_title("Song Name (Lyric Video)"), "Song Name")
        self.assertEqual(clean_title("Song Name (HQ)"), "Song Name")

    def test_strips_bracketed_noise(self):
        self.assertEqual(clean_title("Song Name [Official Audio]"), "Song Name")
        self.assertEqual(clean_title("Song Name [Lyrics]"), "Song Name")

    def test_keeps_meaningful_parentheses(self):
        self.assertEqual(clean_title("Song Name (Live at Wembley)"), "Song Name (Live at Wembley)")
        self.assertEqual(clean_title("Song Name (feat. Someone)"), "Song Name (feat. Someone)")
        self.assertEqual(clean_title("Song Name (Remastered 2011)"), "Song Name (Remastered 2011)")

    def test_empty_and_plain_titles(self):
        self.assertEqual(clean_title(""), "")
        self.assertEqual(clean_title("Just A Song"), "Just A Song")


class TestBuildSearchQuery(unittest.TestCase):
    def test_artist_title_format(self):
        self.assertEqual(
            build_search_query("Song Name (Official Video)", "The Artist"),
            "The Artist - Song Name",
        )

    def test_falls_back_to_title_without_artist(self):
        self.assertEqual(build_search_query("Song Name", ""), "Song Name")

    def test_falls_back_to_artist_without_title(self):
        self.assertEqual(build_search_query("", "The Artist"), "The Artist")


class TestDurationGate(unittest.TestCase):
    def test_within_tolerance_accepts(self):
        self.assertTrue(duration_within_tolerance(200, 200))
        self.assertTrue(duration_within_tolerance(200, 188))  # exactly -12
        self.assertTrue(duration_within_tolerance(200, 212))  # exactly +12

    def test_beyond_tolerance_rejects(self):
        self.assertFalse(duration_within_tolerance(200, 213))  # +13
        self.assertFalse(duration_within_tolerance(200, 187))  # -13

    def test_unknown_durations_never_reject(self):
        self.assertFalse(duration_within_tolerance(None, 200))
        self.assertFalse(duration_within_tolerance(200, None))
        self.assertFalse(duration_within_tolerance(None, None))

    def test_tolerance_value_documented(self):
        self.assertEqual(DURATION_TOLERANCE_SEC, 12)


if __name__ == "__main__":
    unittest.main()
