"""Unit tests for the app self-update service (GitHub Releases check)."""

from __future__ import annotations

import unittest

from app.core.constants import APP_REPO_URL, APP_VERSION
from app.services.app_update_service import (
    check_for_app_update,
    compare_versions,
    normalize_tag,
    parse_version,
)


class TestVersionCompare(unittest.TestCase):
    def test_normalize_tag(self):
        self.assertEqual(normalize_tag("v1.2.3"), "1.2.3")
        self.assertEqual(normalize_tag("V0.1.0"), "0.1.0")
        self.assertEqual(normalize_tag(" 1.0 "), "1.0")
        self.assertEqual(normalize_tag(""), "")
        self.assertEqual(normalize_tag(None), "")

    def test_parse_version(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("1.2"), (1, 2))
        self.assertEqual(parse_version("1.2.3-beta"), (1, 2, 3))
        self.assertIsNone(parse_version("release-1"))
        self.assertIsNone(parse_version(""))

    def test_compare_versions(self):
        self.assertEqual(compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(compare_versions("1.0.0", "1.0.1"), -1)
        self.assertEqual(compare_versions("1.2", "1.2.0"), 0)  # padded
        self.assertEqual(compare_versions("0.2.0", "0.1.0"), 1)
        self.assertEqual(compare_versions("v0.1.0", "0.1.0"), 0)  # tag prefix ignored
        self.assertEqual(compare_versions("10.0", "9.0"), 1)  # numeric not lexical

    def test_compare_with_unparseable_inputs(self):
        self.assertEqual(compare_versions("weird", "1.0.0"), -1)
        self.assertEqual(compare_versions("1.0.0", "weird"), 1)
        self.assertEqual(compare_versions("weird", "also-weird"), 0)


class TestCheckForAppUpdate(unittest.TestCase):
    def test_bundled_version_is_parseable(self):
        self.assertIsNotNone(parse_version(APP_VERSION))

    def test_unreachable_github(self):
        # A port that is closed locally makes the connection fail fast.
        result = check_for_app_update(timeout=0.05)
        self.assertIn(result["status"], ("unreachable", "no_releases"))
        self.assertEqual(result["current"], APP_VERSION)

    def test_no_releases_returns_expected_shape(self):
        # Live call: the project repo may have no published releases yet
        # (404 -> no_releases) or may have one. Either way the shape holds.
        result = check_for_app_update(timeout=10.0)
        self.assertIn(
            result["status"],
            ("update_available", "up_to_date", "no_releases", "unreachable"),
        )
        self.assertEqual(result["current"], APP_VERSION)
        if result["status"] in ("no_releases", "unreachable"):
            self.assertEqual(result["latest"], "")
        if result["status"] == "no_releases":
            self.assertEqual(result["url"], "")  # 404 carries no html_url


class TestRepoConstants(unittest.TestCase):
    def test_repo_urls_are_consistent(self):
        from app.core.constants import APP_RELEASES_API, APP_RELEASES_PAGE

        self.assertTrue(APP_REPO_URL.startswith("https://github.com/"))
        self.assertEqual(APP_RELEASES_PAGE, APP_REPO_URL + "/releases")
        self.assertIn("MohamedEl-Damrawy/B7R-Downloader", APP_RELEASES_API)


if __name__ == "__main__":
    unittest.main()
