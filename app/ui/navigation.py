"""Sidebar navigation widget (design spec section H)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

# Unicode glyphs instead of image assets; omit automatically on rendering
# issues. Direction-aware by nature: the glyph sits at the reading-start
# edge because it is part of the label text.
NAV_ICONS = {
    "dashboard": "\u2302",       # ⌂
    "new_download": "\uFF0B",    # ＋
    "playlists": "\u25A4",       # ▤
    "queue": "\u2193",           # ↓
    "completed": "\u2713",       # ✓
    "history": "\u21B6",         # ↶
    "settings": "\u2699",        # ⚙
}


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(232)
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        # Brand area ~88px: 16px top + 16px bottom margins + 2 labels.
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

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
            icon = NAV_ICONS.get(key, "")
            text = f"{icon}  {label}" if icon else label
            btn = QPushButton(text)
            btn.setProperty("class", "NavButton")
            btn.setMinimumHeight(44)
            # Reading-start alignment, direction-aware (Qt QSS lacks 'start').
            align = "right" if self.layoutDirection() == Qt.RightToLeft else "left"
            btn.setStyleSheet(f"text-align: {align};")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked=False, k=key: self._on_click(k))
            layout.addWidget(btn)
            layout.addSpacing(0 if key == items[-1][0] else 4)
            self._buttons[key] = btn

        layout.addStretch(1)

    def _on_click(self, key: str) -> None:
        self.set_active(key)
        self.navigate.emit(key)

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
