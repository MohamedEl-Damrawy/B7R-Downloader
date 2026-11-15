"""Unit tests for i18n/RTL support (translation install, RTL layout, fonts)."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.core.paths import get_resources_dir
from app.ui.i18n import ARABIC_FONT_FAMILY, install_language, resolve_language, translate_known_error
from app.ui.theme.style_loader import load_theme_qss


class TestI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._remove_translator = None

    def tearDown(self) -> None:
        # Remove any Arabic translator installed by a test so later tests see English.
        from app.ui import i18n as i18n_mod

        if i18n_mod._TRANSLATOR is not None:
            self.app.removeTranslator(i18n_mod._TRANSLATOR)
            i18n_mod._TRANSLATOR = None
        self.app.setLayoutDirection(Qt.LeftToRight)

    def test_qm_catalog_exists(self):
        self.assertTrue((get_resources_dir() / "i18n" / "app_ar.qm").exists())

    def test_default_language_is_english(self):
        self.assertEqual(resolve_language(), "en")
        self.assertEqual(install_language(self.app, "en"), "en")
        self.assertEqual(self.app.layoutDirection(), Qt.LeftToRight)

    def test_arabic_sets_rtl_and_translates(self):
        lang = install_language(self.app, "ar")
        self.assertEqual(lang, "ar")
        self.assertEqual(self.app.layoutDirection(), Qt.RightToLeft)
        # Sidebar context translated via the installed QTranslator.
        from app.ui.navigation import Sidebar

        self.assertEqual(Sidebar().tr("Dashboard"), "الرئيسية")
        # Known controller errors are localized for display.
        translated = translate_known_error("Not enough free disk space at destination.")
        self.assertNotEqual(translated, "Not enough free disk space at destination.")
        # Dynamic yt-dlp errors pass through unchanged.
        self.assertEqual(translate_known_error("some raw yt-dlp error"), "some raw yt-dlp error")
        self.assertEqual(translate_known_error(""), "")
        self.assertEqual(translate_known_error(None), "")

    def test_arabic_theme_uses_tajawal(self):
        qss = load_theme_qss("dark", lang="ar")
        self.assertIn(ARABIC_FONT_FAMILY, qss)
        self.assertIn("14px", qss)
        self.assertNotIn("Segoe UI", qss)
        # English keeps the default Latin stack.
        english_qss = load_theme_qss("dark", lang="en")
        self.assertIn("Segoe UI", english_qss)
        self.assertNotIn("Tajawal", english_qss)

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(install_language(self.app, "xx"), "en")
        self.assertEqual(self.app.layoutDirection(), Qt.LeftToRight)


if __name__ == "__main__":
    unittest.main()
