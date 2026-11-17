"""Completed downloads page."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.database.repositories.downloads_repo import DownloadsRepository
from app.ui.widgets.common import EmptyState, PageHeader


class CompletedPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.repo = DownloadsRepository()
        self._controller = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)
        layout.addWidget(PageHeader(self.tr("Completed"), self.tr("Successfully completed downloads")))

        actions = QHBoxLayout()
        self.open_btn = QPushButton(self.tr("Open Folder"))
        self.open_btn.clicked.connect(self._open_selected_folder)
        actions.addWidget(self.open_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.list_widget, 1)
        self.empty = EmptyState(
            self.tr("Nothing completed yet"),
            self.tr("Your completed downloads will appear here."),
            icon="completed",  # Lucide circle-check
        )
        # stretch=1: fills the page when the list is hidden (no blank void).
        layout.addWidget(self.empty, 1)
        self._update_actions()

    def set_controller(self, controller) -> None:
        self._controller = controller
        self._update_actions()

    def refresh_data(self) -> None:
        self.list_widget.clear()
        try:
            rows = self.repo.list_by_statuses(["Completed"], limit=200)
        except Exception:
            rows = []
        for r in rows:
            title = r.get("title") or r.get("source_url") or r.get("id")
            path = r.get("output_path") or ""
            item = QListWidgetItem(f"{title}   -   {path}")
            item.setData(Qt.UserRole, r)
            self.list_widget.addItem(item)
        has = self.list_widget.count() > 0
        self.list_widget.setVisible(has)
        self.empty.setVisible(not has)
        self._update_actions()

    def _update_actions(self) -> None:
        item = self.list_widget.currentItem()
        self.open_btn.setEnabled(item is not None)

    def _open_selected_folder(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        rec = item.data(Qt.UserRole) or {}
        path = (rec.get("output_path") or "").strip()
        if not path:
            QMessageBox.information(self, self.tr("No path"), self.tr("No output folder is recorded for this item."))
            return
        if not os.path.isdir(path):
            # if a file path was stored, open its parent
            parent = os.path.dirname(path)
            if parent and os.path.isdir(parent):
                path = parent
            else:
                QMessageBox.warning(self, self.tr("Not found"), self.tr("The output folder could not be found."))
                return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Open failed"), str(exc))

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_data()
