from __future__ import annotations

import unittest

from app.core.exceptions import MetadataExtractionError, UnsupportedSourceError
from app.engine.ytdlp_engine import _classify_download_error, _classify_error, _YTdlpCaptureLogger


class TestYTdlpCaptureLogger(unittest.TestCase):
    """DL-01: capture logger collects yt-dlp stderr errors for classification."""

    def test_last_error_returns_stripped_error_text(self):
        cap = _YTdlpCaptureLogger()
        self.assertEqual(cap.last_error(), "")
        cap.error("ERROR: [youtube] abc123: Private video. Sign in if you've been granted access to this video.")
        self.assertEqual(
            cap.last_error(),
            "[youtube] abc123: Private video. Sign in if you've been granted access to this video.",
        )

    def test_last_error_skips_non_error_lines(self):
        cap = _YTdlpCaptureLogger()
        cap.error("WARNING: something odd")  # not an ERROR: line
        cap.error("ERROR: This video is unavailable")
        self.assertEqual(cap.last_error(), "This video is unavailable")

    def test_last_error_uses_most_recent(self):
        cap = _YTdlpCaptureLogger()
        cap.error("ERROR: first failure")
        cap.error("ERROR: second failure")
        self.assertEqual(cap.last_error(), "second failure")

    def test_error_formatting_with_args(self):
        cap = _YTdlpCaptureLogger()
        cap.error("ERROR: %s failed", "video123")
        self.assertEqual(cap.last_error(), "video123 failed")

    def test_debug_info_warning_are_noops(self):
        cap = _YTdlpCaptureLogger()
        cap.debug("[download] 50% of 10MiB")
        cap.info("some info")
        cap.warning("some warning")
        self.assertEqual(cap.errors, [])


class TestEngineErrors(unittest.TestCase):
    def test_classify_metadata_errors(self):
        self.assertIsInstance(_classify_error(Exception("Unsupported URL: x")), UnsupportedSourceError)
        self.assertIsInstance(_classify_error(Exception("This video is private")), MetadataExtractionError)
        self.assertEqual(
            str(_classify_error(Exception("timeout"))),
            "Network timeout while extracting metadata. Check your connection and try again.",
        )
        self.assertIsInstance(_classify_error(Exception("HTTP Error 404")), MetadataExtractionError)
        self.assertEqual(str(_classify_error(Exception("random"))), "Failed to extract metadata from the provided URL.")

    def test_classify_download_errors(self):
        self.assertIsInstance(_classify_download_error(Exception("Unsupported URL")), UnsupportedSourceError)
        self.assertIn("FFmpeg", str(_classify_download_error(Exception("ffmpeg not found"))))
        self.assertIn("Permission", str(_classify_download_error(Exception("Permission denied"))))
        self.assertIn("disk space", str(_classify_download_error(Exception("No space left on device"))))
        self.assertIn("timeout", str(_classify_download_error(Exception("Read timed out"))).lower())
        self.assertIn("Network error", str(_classify_download_error(Exception("HTTP Error 500"))))
        self.assertEqual(
            str(_classify_download_error(Exception("mystery"))),
            "Download failed. Check the URL, network connection, FFmpeg availability, or output path.",
        )


if __name__ == "__main__":
    unittest.main()
