from __future__ import annotations

import unittest

from app.core.validators import is_http_url, is_valid_playlist_items


class TestValidators(unittest.TestCase):
    def test_is_http_url(self):
        self.assertTrue(is_http_url("https://example.com/watch?v=1"))
        self.assertTrue(is_http_url("http://example.com"))
        self.assertFalse(is_http_url(""))
        self.assertFalse(is_http_url("ftp://example.com"))
        self.assertFalse(is_http_url("not a url"))
        self.assertFalse(is_http_url("https://"))

    def test_is_valid_playlist_items_accepts_numeric_forms(self):
        self.assertTrue(is_valid_playlist_items("1"))
        self.assertTrue(is_valid_playlist_items("1,2,3"))
        self.assertTrue(is_valid_playlist_items("1-5"))
        self.assertTrue(is_valid_playlist_items(" 3 "))
        self.assertTrue(is_valid_playlist_items("1-5,7"))
        self.assertTrue(is_valid_playlist_items("2 - 4"))

    def test_is_valid_playlist_items_rejects_non_numeric(self):
        self.assertFalse(is_valid_playlist_items(""))
        self.assertFalse(is_valid_playlist_items(None))
        self.assertFalse(is_valid_playlist_items("abc"))
        # A video ID must never be passed as playlist_items.
        self.assertFalse(is_valid_playlist_items("dQw4w9WgXcQ"))
        self.assertFalse(is_valid_playlist_items("1,,2"))
        self.assertFalse(is_valid_playlist_items("1--3"))
        self.assertFalse(is_valid_playlist_items("1-"))
        self.assertFalse(is_valid_playlist_items("-3"))
        self.assertFalse(is_valid_playlist_items("1-2-3"))


if __name__ == "__main__":
    unittest.main()
