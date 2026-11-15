"""Unit tests for theme loading (FEAT-08) and orphan ffmpeg cleanup (DL-09)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.paths import get_resources_dir
from app.ui.theme import palette as palette_mod
from app.ui.theme.style_loader import load_dark_qss, load_theme_qss


class TestThemeLoading(unittest.TestCase):
    def test_dark_default_contains_dark_tokens(self):
        qss = load_theme_qss("dark")
        self.assertTrue(qss)
        self.assertNotIn("@", qss)  # all tokens resolved
        self.assertIn("#0B1018", qss)  # dark main background

    def test_load_dark_qss_alias(self):
        self.assertEqual(load_dark_qss(), load_theme_qss("dark"))

    def test_light_theme_uses_light_palette(self):
        qss = load_theme_qss("light")
        self.assertTrue(qss)
        self.assertNotIn("@", qss)
        self.assertIn(palette_mod.LIGHT_PALETTE["main_bg"], qss)
        self.assertNotIn("#0B1018", qss)  # dark background must not leak in

    def test_unknown_theme_falls_back_to_dark(self):
        self.assertEqual(load_theme_qss("nonsense"), load_theme_qss("dark"))

    def test_light_qss_file_exists(self):
        self.assertTrue((get_resources_dir() / "styles" / "light.qss").exists())

    def test_palette_for_theme(self):
        self.assertIs(palette_mod.palette_for_theme("light"), palette_mod.LIGHT_PALETTE)
        self.assertIs(palette_mod.palette_for_theme("dark"), palette_mod.PALETTE)
        self.assertIs(palette_mod.palette_for_theme(""), palette_mod.PALETTE)
        self.assertIs(palette_mod.palette_for_theme("LIGHT"), palette_mod.LIGHT_PALETTE)


class TestOrphanFfmpegCleanup(unittest.TestCase):
    """DL-09: kill_bundled_ffmpeg_orphans kills only bundled-path processes."""

    def _setup_bundled(self) -> tempfile.TemporaryDirectory:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        ffmpeg = os.path.join(td.name, "ffmpeg.exe")
        with open(ffmpeg, "wb") as f:
            f.write(b"stub")
        self._td = td
        return td

    def test_non_windows_is_noop(self):
        import app.engine.ffmpeg_manager as mod

        if os.name == "nt":
            self.skipTest("requires a non-Windows platform check")
        self.assertEqual(mod.kill_bundled_ffmpeg_orphans(), 0)

    @unittest.skipUnless(os.name == "nt", "Windows-only behavior")
    def test_kill_only_bundled_processes(self):
        import app.engine.ffmpeg_manager as mod

        td = self._setup_bundled()
        bundled_ffmpeg = os.path.join(td.name, "ffmpeg.exe")
        rows = [
            {"ProcessId": 111, "ExecutablePath": bundled_ffmpeg},  # bundled -> kill
            {"ProcessId": 222, "ExecutablePath": "C:\\Windows\\System32\\ffmpeg.exe"},  # system -> spare
            {"ProcessId": 333, "ExecutablePath": ""},  # malformed -> skip
        ]
        calls: list[list[str]] = []

        def fake_run(cmd, capture_output=True, text=True, timeout=None):
            calls.append(list(cmd))
            out = json.dumps(rows) if "Get-CimInstance" in " ".join(cmd) else ""
            return SimpleNamespace(stdout=out, returncode=0)

        with patch.object(mod, "get_vendor_ffmpeg_dir", return_value=__import__("pathlib").Path(td.name)), \
             patch.object(mod.subprocess, "run", side_effect=fake_run):
            killed = mod.kill_bundled_ffmpeg_orphans()

        self.assertEqual(killed, 1)
        taskkill = [c for c in calls if c and c[0] == "taskkill"]
        self.assertEqual(len(taskkill), 1)
        self.assertIn("111", taskkill[0])

    @unittest.skipUnless(os.name == "nt", "Windows-only behavior")
    def test_powershell_failure_is_swallowed(self):
        import app.engine.ffmpeg_manager as mod

        def fake_run(*args, **kwargs):
            raise OSError("boom")

        with patch.object(mod.subprocess, "run", side_effect=fake_run):
            self.assertEqual(mod.kill_bundled_ffmpeg_orphans(), 0)


if __name__ == "__main__":
    unittest.main()
