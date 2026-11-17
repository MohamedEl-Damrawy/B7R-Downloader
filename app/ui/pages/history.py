"""History page."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.downloads_repo import DownloadsRepository
from app.ui.widgets.common import EmptyState, PageHeader


class HistoryPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.repo = DownloadsRepository()
        self._controller = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(PageHeader(self.tr("History"), self.tr("Past download attempts and outcomes")))

        # FEAT-11: client-side search over the loaded history.
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Filter by title or URL..."))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.refresh_data)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        actions = QHBoxLayout()
        self.open_btn = QPushButton(self.tr("Open Folder"))
        self.open_btn.clicked.connect(self._open_selected_folder)
        self.retry_btn = QPushButton(self.tr("Retry Selected"))
        self.retry_btn.clicked.connect(self._retry_selected)
        self.delete_btn = QPushButton(self.tr("Delete Selected"))
        self.delete_btn.setProperty("class", "Danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_all_btn = QPushButton(self.tr("Clear All"))
        self.clear_all_btn.setProperty("class", "Danger")
        self.clear_all_btn.clicked.connect(self._clear_all)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.retry_btn)
        actions.addWidget(self.delete_btn)
        actions.addWidget(self.clear_all_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.list_widget = QListWidget()
        # Multi-select so users can delete several records at once.
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.list_widget, 1)
        self.empty = EmptyState(self.tr("No history yet"), self.tr("Download history will appear here."))
        # stretch=1: fills the page when the list is hidden (no blank void).
        layout.addWidget(self.empty, 1)
        self._update_actions()

    def set_controller(self, controller) -> None:
        self._controller = controller
        self._update_actions()

    def refresh_data(self) -> None:
        self.list_widget.clear()
        try:
            rows = self.repo.list_recent(200)
        except Exception:
            rows = []
        needle = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        if needle:
            rows = [
                r for r in rows
                if needle in str(r.get("title") or "").lower() or needle in str(r.get("source_url") or "").lower()
            ]
        for r in rows:
            title = r.get("title") or r.get("source_url") or r.get("id")
            status = r.get("status", "")
            err = r.get("error_message")
            text = f"[{status}] {title}"
            if err and status in ("Failed", "Cancelled"):
                from app.ui.i18n import translate_known_error

                short = translate_known_error(err).strip().replace("\n", " ")
                if len(short) > 100:
                    short = short[:97] + "..."
                text += f"  -  {short}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r)
            self.list_widget.addItem(item)
        has = self.list_widget.count() > 0
        self.list_widget.setVisible(has)
        self.empty.setVisible(not has)
        self._update_actions()

    def _update_actions(self) -> None:
        item = self.list_widget.currentItem()
        rec = item.data(Qt.UserRole) if item else {}
        status = (rec or {}).get("status")
        selected = self.list_widget.selectedItems()
        self.open_btn.setEnabled(item is not None)
        self.retry_btn.setEnabled(
            self._controller is not None and status in ("Failed", "Cancelled")
        )
        self.delete_btn.setEnabled(bool(selected))
        self.clear_all_btn.setEnabled(self.list_widget.count() > 0)

    def _delete_selected(self) -> None:
        """FEAT-11 + UI/UX: delete one or several selected history records."""
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        from PySide6.QtWidgets import QMessageBox

        count = len(selected)
        if count == 1:
            msg = self.tr("Remove this entry from history? Downloaded files are not deleted.")
        else:
            msg = self.tr("Remove %d selected entries from history? Downloaded files are not deleted.") % count
        reply = QMessageBox.question(
            self,
            self.tr("Delete records"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ids = [str((it.data(Qt.UserRole) or {}).get("id")) for it in selected]
        ids = [i for i in ids if i and i != "None"]
        try:
            self.repo.delete_many(ids)
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Delete failed"), str(exc))
            return
        self.refresh_data()

    def _clear_all(self) -> None:
        """UI/UX: wipe the whole history in one action (files stay on disk)."""
        if self.list_widget.count() == 0:
            return
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            self.tr("Clear history"),
            self.tr("Remove ALL entries from history? Downloaded files are not deleted."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.repo.delete_all()
        except Exception as exc:
            QMessageBox.warning(self, self.tr("Delete failed"), str(exc))
            return
        self.refresh_data()

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

    def _retry_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item or not self._controller:
            return
        rec = item.data(Qt.UserRole) or {}
        if rec.get("status") not in ("Failed", "Cancelled"):
            return
        if hasattr(self._controller, "retry_download"):
            try:
                self._controller.retry_download(rec.get("id"))
            except Exception as exc:
                QMessageBox.warning(self, self.tr("Retry failed"), str(exc))

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_data()
