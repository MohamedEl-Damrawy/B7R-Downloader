"""Sidebar navigation widget (design spec section H + RTL pass).

RTL notes:
- The application-level layout direction (set in app.ui.i18n.install_language)
  mirrors every QHBoxLayout automatically, so this sidebar is added first in
  the root layout and lands on the RIGHT edge in Arabic/RTL.
- Each nav row is an icon label followed by a text label in a horizontal
  layout: in RTL the icon appears at the reading-start (right) edge with the
  label immediately to its left. No physical left/right coordinates anywhere.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.widgets.icons import (
    ICON_LABEL_GAP,
    ICON_SIZE,
    ROW_HEIGHT,
    render_svg_icon,
    theme_colors,
)


class NavButton(QPushButton):
    """One navigation row: 20x20 icon + label, 12px gap, 44px high.

    The icon and label are plain QLabels inside a direction-aware layout so
    the reading order mirrors automatically (icon right of label in RTL).
    Child labels are transparent to mouse events so the button keeps all
    hover/click behavior.
    """

    def __init__(self, key: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._key = key
        self._muted_color, self._active_color = theme_colors()

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._icon_label.setStyleSheet("background: transparent;")
        self._text_label = QLabel(label)
        self._text_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._text_label.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(ICON_LABEL_GAP)
        row.addWidget(self._icon_label)
        row.addWidget(self._text_label, 1)

        self.setFixedHeight(ROW_HEIGHT)
        self.setProperty("class", "NavButton")
        self.setCursor(Qt.PointingHandCursor)
        self._apply_state(False)

    def _apply_state(self, active: bool) -> None:
        color = self._active_color if active else self._muted_color
        weight = "600" if active else "400"
        self._text_label.setStyleSheet(
            f"background: transparent; color: {color}; font-weight: {weight};"
        )
        icon = render_svg_icon(self._key, color, dpr=self.devicePixelRatioF() or 1.0)
        if icon is not None:
            self._icon_label.setPixmap(icon.pixmap(ICON_SIZE, ICON_SIZE))
        else:
            # Text-only fallback if SVG rendering is unavailable.
            self._icon_label.hide()

    def set_active(self, active: bool) -> None:
        self._apply_state(active)


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(232)
        self._buttons: dict[str, NavButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        # Brand mark: bundled app icon rendered at 40px, theme-independent
        # (the SVG carries its own fixed brand colors).
        mark = QLabel()
        mark.setFixedHeight(40)
        mark.setAlignment(Qt.AlignCenter)
        try:
            from app.core.paths import get_resources_dir
            from app.ui.widgets.icons import render_svg_file_pixmap

            pm = render_svg_file_pixmap(
                get_resources_dir() / "icons" / "app_icon.svg",
                40,
                dpr=self.devicePixelRatioF() or 1.0,
            )
            if pm is not None:
                mark.setPixmap(pm)
            else:
                mark.hide()
        except Exception:
            mark.hide()
        layout.addWidget(mark)
        layout.addSpacing(8)

        brand = QLabel("VeloDownloader")
        brand.setObjectName("BrandTitle")  # 16px/600 via QSS
        sub = QLabel(self.tr("Premium Download Manager"))
        sub.setObjectName("BrandSubtitle")  # 11px secondary via QSS
        layout.addWidget(brand)
        layout.addWidget(sub)
        layout.addSpacing(24)

        items = [
            ("dashboard", self.tr("Dashboard")),
            ("new_download", self.tr("New Download")),
            ("playlists", self.tr("Playlists")),
            ("queue", self.tr("Download Queue")),
            ("completed", self.tr("Completed")),
            ("history", self.tr("History")),
            ("settings", self.tr("Settings")),
        ]
        for key, label in items:
            btn = NavButton(key, label)
            btn.clicked.connect(lambda checked=False, k=key: self._on_click(k))
            layout.addWidget(btn)
            if key != items[-1][0]:
                layout.addSpacing(4)
            self._buttons[key] = btn

        layout.addStretch(1)

    def _on_click(self, key: str) -> None:
        self.set_active(key)
        self.navigate.emit(key)

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            active = k == key
            btn.setProperty("active", "true" if active else "false")
            btn.set_active(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
