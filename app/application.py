"""Qt application factory and lifecycle."""

from __future__ import annotations

import sys

from app.core.constants import APP_NAME, APP_VERSION
from app.ui.theme.style_loader import load_theme_qss


def _resolve_theme() -> str:
    """FEAT-08: theme comes from settings; falls back to dark on any failure."""
    try:
        from app.core.constants import SETTINGS_THEME
        from app.services.settings_service import SettingsService

        value = str(SettingsService().get(SETTINGS_THEME, "dark") or "dark").strip().lower()
        return value if value in ("dark", "light") else "dark"
    except Exception:
        return "dark"


def run() -> int:
    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.main_window import MainWindow
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        raise RuntimeError(
            "PySide6 is required to run the GUI. Install dependencies and retry."
        ) from exc

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # i18n: language (translator + RTL layout) must be in place before any
    # widget is built; English is the default, Arabic flips to RTL + Tajawal.
    from app.ui.i18n import install_language

    language = install_language(app)

    # FEAT-14: window/taskbar icon (best effort; icon may not exist in dev checkouts).
    try:
        from PySide6.QtGui import QIcon

        from app.core.paths import get_resources_dir

        icon_path = get_resources_dir() / "icons" / "app.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass

    qss = load_theme_qss(_resolve_theme(), lang=language)
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    return app.exec()
