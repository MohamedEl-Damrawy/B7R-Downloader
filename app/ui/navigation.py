"""Sidebar navigation widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(8)

        brand = QLabel("Velo Downloader")
        brand.setObjectName("BrandTitle")
        brand.setStyleSheet("font-size: 18px; font-weight: 700;")
        sub = QLabel(self.tr("Premium Download Manager"))
        sub.setProperty("class", "Subtitle")
        sub.setStyleSheet("font-size: 11px;")
        layout.addWidget(brand)
        layout.addWidget(sub)
        layout.addSpacing(12)

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
            btn = QPushButton(label)
            btn.setProperty("class", "NavButton")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked=False, k=key: self._on_click(k))
            layout.addWidget(btn)
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
