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
    APP_REPO_URL,
    APP_VERSION,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("About %s") % APP_NAME)
        self.resize(540, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{APP_NAME}</b>"))
        layout.addWidget(QLabel(self.tr("Version: %s") % APP_VERSION))
        desc = QLabel(APP_DESCRIPTION)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        repo = QLabel(
            f'{self.tr("Project page / downloads:")} '
            f'<a href="{APP_REPO_URL}">{APP_REPO_URL.replace("https://", "")}</a>'
        )
        repo.setWordWrap(True)
        repo.setTextFormat(Qt.RichText)
        repo.setOpenExternalLinks(True)
        layout.addWidget(repo)

        dev = QLabel(
            f"{self.tr('Developer: %s') % APP_DEVELOPER}<br>"
            f'{self.tr("LinkedIn:")} '
            f'<a href="{APP_DEVELOPER_LINKEDIN}">{APP_DEVELOPER_LINKEDIN.replace("https://", "")}</a><br>'
            f'{self.tr("GitHub:")} '
            f'<a href="{APP_DEVELOPER_GITHUB}">{APP_DEVELOPER_GITHUB.replace("https://", "")}</a>'
        )
        dev.setWordWrap(True)
        dev.setTextFormat(Qt.RichText)
        dev.setOpenExternalLinks(True)
        layout.addWidget(dev)

        legal = QLabel(
            f"{APP_COPYRIGHT}<br>"
            f"{self.tr('Publisher/Legal entity:')} {APP_PUBLISHER}<br>"
            f"{self.tr('Application license:')} {APP_LICENSE}"
        )
        legal.setWordWrap(True)
        legal.setTextFormat(Qt.RichText)
        legal.setProperty("class", "Subtitle")
        layout.addWidget(legal)

        note = QLabel(
            self.tr("For authorized sources only. No DRM/paywall/access-control circumvention. "
                    "Not affiliated with YouTube or other third-party services.")
        )
        note.setWordWrap(True)
        note.setProperty("class", "Subtitle")
        layout.addWidget(note)
        layout.addStretch(1)
