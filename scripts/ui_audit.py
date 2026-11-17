"""Offscreen visual audit: render every page in light + dark, save PNGs."""
from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("LOCALAPPDATA", os.path.join(os.environ.get("TEMP", "."), "velo_audit"))

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget

from app.ui.theme.style_loader import load_theme_qss

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "_ui_audit")
os.makedirs(OUT, exist_ok=True)

app = QApplication.instance() or QApplication([])


def shots(theme: str, rtl: bool = False) -> None:
    from PySide6.QtCore import Qt

    app.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
    suffix = "_rtl" if rtl else ""
    app.setStyleSheet(load_theme_qss(theme, lang="ar" if rtl else ""))
    from app.ui.navigation import Sidebar
    from app.ui.pages import completed, dashboard, history, new_download, playlist, queue, settings

    pages = []
    for name, cls, needs in [
        ("dashboard", dashboard.DashboardPage, ()),
        ("new_download", new_download.NewDownloadPage, ()),
        ("queue", queue.QueuePage, ()),
        ("history", history.HistoryPage, ()),
        ("completed", completed.CompletedPage, ()),
        ("playlist", playlist.PlaylistsPage, ()),
        ("settings", settings.SettingsPage, ()),
    ]:
        try:
            page = cls()
            pages.append((name, page))
        except Exception as exc:  # noqa: BLE001
            print(f"[{theme}] FAIL init {name}: {exc}")

    # Window-level shot: sidebar + dashboard (checks nav rail, brand, icons).
    try:
        win = QWidget()
        win.setObjectName("Root")
        wl = QHBoxLayout(win)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        sb = Sidebar()
        sb.set_active("dashboard")
        wl.addWidget(sb)
        dash = dashboard.DashboardPage()
        wl.addWidget(dash, 1)
        win.resize(1280, 800)
        win.show()
        app.processEvents()
        win.grab().save(os.path.join(OUT, f"{theme}{suffix}_window.png"))
        win.close()
        pages.append(("window_only_dashboard", dash))
    except Exception as exc:  # noqa: BLE001
        print(f"[{theme}] FAIL window: {exc}")
    return pages

    for name, page in pages:
        # Real app hosts pages inside a QWidget#Root container; replicate so
        # the QSS background/color cascade matches production.
        root = QWidget()
        root.setObjectName("Root")
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(page)
        root.resize(1000, 720)
        root.show()
        app.processEvents()
        path = os.path.join(OUT, f"{theme}{suffix}_{name}.png")
        root.grab().save(path)
        print(f"[{theme}] {name} -> {path}")
        root.close()


shots("light")
shots("dark")
shots("dark", rtl=True)
print("DONE")
