"""About dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from app.core.constants import (
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_DEVELOPER,
    APP_DEVELOPER_GITHUB,
    APP_DEVELOPER_LINKEDIN,
    APP_LICENSE,
    APP_NAME,
    APP_PUBLISHER,
    APP_VERSION,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.resize(540, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{APP_NAME}</b>"))
        layout.addWidget(QLabel(f"Version: {APP_VERSION}"))
        desc = QLabel(APP_DESCRIPTION)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        dev = QLabel(
            f"Developer: {APP_DEVELOPER}<br>"
            f'LinkedIn: <a href="{APP_DEVELOPER_LINKEDIN}">{APP_DEVELOPER_LINKEDIN.replace("https://", "")}</a><br>'
            f'GitHub: <a href="{APP_DEVELOPER_GITHUB}">{APP_DEVELOPER_GITHUB.replace("https://", "")}</a>'
        )
        dev.setWordWrap(True)
        dev.setTextFormat(Qt.RichText)
        dev.setOpenExternalLinks(True)
        layout.addWidget(dev)

        legal = QLabel(
            f"{APP_COPYRIGHT}<br>"
            f"Publisher/Legal entity: {APP_PUBLISHER}<br>"
            f"Application license: {APP_LICENSE}"
        )
        legal.setWordWrap(True)
        legal.setTextFormat(Qt.RichText)
        legal.setStyleSheet("color: #91A2B5;")
        layout.addWidget(legal)

        note = QLabel(
            "For authorized sources only. No DRM/paywall/access-control circumvention. "
            "Not affiliated with YouTube or other third-party services."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #91A2B5;")
        layout.addWidget(note)
        layout.addStretch(1)
