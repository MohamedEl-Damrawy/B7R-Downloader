"""Application language / i18n support.

Qt-native translation: class-level tr() calls + .ts/.qm catalogs under
resources/i18n/. English is the default (LTR); Arabic ("ar") ships a full
catalog, drives the RightToLeft layout direction, and activates the bundled
Tajawal font via the style-loader font tokens.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTranslator
from PySide6.QtWidgets import QApplication

from app.core.constants import SETTINGS_LANGUAGE
from app.core.logger import get_logger
from app.core.paths import get_resources_dir

SUPPORTED_LANGUAGES: dict[str, str] = {"en": "English", "ar": "العربية"}
RTL_LANGUAGES = {"ar"}
ARABIC_FONT_FAMILY = "Tajawal"

_TRANSLATOR: QTranslator | None = None
_fonts_loaded = False


def resolve_language() -> str:
    """Read the configured language from settings; fall back to English."""
    try:
        from app.services.settings_service import SettingsService

        value = str(SettingsService().get(SETTINGS_LANGUAGE, "en") or "en").strip().lower()
        return value if value in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"


def load_bundled_fonts() -> None:
    """Register the bundled Tajawal family once per process."""
    global _fonts_loaded
    if _fonts_loaded:
        return
    try:
        from PySide6.QtGui import QFontDatabase

        fonts_dir = get_resources_dir() / "fonts"
        for name in ("Tajawal-Regular.ttf", "Tajawal-Medium.ttf", "Tajawal-Bold.ttf"):
            path = fonts_dir / name
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))
        _fonts_loaded = True
    except Exception:
        get_logger(__name__).debug("Bundled font loading failed", exc_info=True)


def install_language(app: QApplication, lang: str = "") -> str:
    """Install the Qt translator and set the layout direction for `lang`.

    Must be called before any window is created. Returns the resolved language.
    """
    global _TRANSLATOR
    language = lang if lang in SUPPORTED_LANGUAGES else resolve_language()
    load_bundled_fonts()

    if _TRANSLATOR is not None:
        app.removeTranslator(_TRANSLATOR)
        _TRANSLATOR = None
    if language in RTL_LANGUAGES:
        qm = get_resources_dir() / "i18n" / f"app_{language}.qm"
        if qm.exists():
            translator = QTranslator(app)
            if translator.load(str(qm)):
                app.installTranslator(translator)
                _TRANSLATOR = translator
            else:
                get_logger(__name__).warning("Could not load translation catalog: %s", qm)
        else:
            get_logger(__name__).warning("Translation catalog missing: %s", qm)
    app.setLayoutDirection(Qt.RightToLeft if language in RTL_LANGUAGES else Qt.LeftToRight)
    return language


def translate_known_error(message: str | None) -> str:
    """Translate controller-generated error messages for display.

    Raw yt-dlp/YouTube errors are shown as-is (they are dynamic English text);
    only this app's own fixed messages are localized. Keep the keys in sync
    with app/controllers/download_controller.py.
    """
    if not message:
        return ""
    msg = str(message).strip()
    known = [
        "Not enough free disk space at destination.",
        "Interrupted by application restart",
        "Cancelled by user.",
        "Cancelled by user",
        "Download timed out.",
        "Download failed. Check the URL, network connection, FFmpeg availability, or output path.",
        "Download failed.",
    ]
    for candidate in known:
        if msg.startswith(candidate):
            translated = translate_known_error_key(candidate)
            return translated + msg[len(candidate):]
    return msg


def translate_known_error_key(key: str) -> str:
    """tr() hook for known error messages (exposes them to lupdate)."""
    return QApplication.tr(key)
