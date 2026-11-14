"""Qt application factory and lifecycle."""

from __future__ import annotations

import sys

from app.core.constants import APP_NAME, APP_VERSION
from app.ui.theme.style_loader import load_dark_qss


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

    qss = load_dark_qss()
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    return app.exec()
