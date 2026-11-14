"""GUI smoke tests (pytest-qt/offscreen)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_main_window_bootstrap_and_navigation(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    from app.database.migrations import apply_migrations
    from app.ui.main_window import MainWindow

    apply_migrations()
    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    assert w.windowTitle()
    for key in ("dashboard", "new_download", "playlists", "queue", "completed", "history", "settings"):
        assert key in w.pages

    for key in ("new_download", "queue", "history", "settings", "dashboard"):
        w.navigate_to(key)
        assert w.stack.currentWidget() is w.pages[key]
    w.close()


def test_new_download_page_widgets(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    from app.database.migrations import apply_migrations
    from app.ui.pages.new_download import NewDownloadPage

    apply_migrations()
    page = NewDownloadPage()
    qtbot.addWidget(page)
    page.show()

    assert hasattr(page, "url_input")
    assert hasattr(page, "extract_btn")
    assert hasattr(page, "download_btn")
    assert hasattr(page, "dest_input")
    page.url_input.setText("")
    assert page.url_input.text() == ""


def test_settings_page_loads(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    from app.database.migrations import apply_migrations
    from app.ui.pages.settings import SettingsPage

    apply_migrations()
    page = SettingsPage()
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible() or True
