"""Download Queue page."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.common import EmptyState, PageHeader


class _QueueRow(QWidget):
    """FEAT-12: per-item row widget with title, live info text and progress bar."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(10)
        self.title_label = QLabel()
        self.title_label.setObjectName("QueueRowTitle")
        self.info_label = QLabel()
        self.info_label.setObjectName("QueueRowInfo")
        top.addWidget(self.title_label, 1)
        top.addWidget(self.info_label, 0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setRange(0, 1000)
        layout.addLayout(top)
        layout.addWidget(self.progress)

    def update_from(self, task: dict) -> None:
        title = task.get("title") or task.get("source_url") or task.get("id", "")
        self.title_label.setText(str(title))
        self.title_label.setToolTip(str(title))
        self.info_label.setText(_summary_info(task))
        status = task.get("status", "Queued")
        if status in ("Completed",):
            self.progress.setValue(1000)
        else:
            try:
                progress = float(task.get("progress") or 0.0)
            except Exception:
                progress = 0.0
            self.progress.setValue(max(0, min(1000, int(progress * 10))))
        self.progress.setVisible(status not in ("Failed", "Cancelled", "Completed") or self.progress.value() > 0)


def _summary_info(task: dict) -> str:
    """Compact right-side info text: status, size, speed and ETA."""
    from app.ui.i18n import translate_known_error

    status = task.get("status", "Queued")
    parts = [f"[{status}]"]
    dl = task.get("downloaded_bytes")
    total = task.get("total_bytes")
    if dl is not None and total:
        try:
            parts.append(f"{float(dl)/1024/1024:.1f}/{float(total)/1024/1024:.1f} MB")
        except Exception:
            pass
    elif dl is not None:
        try:
            parts.append(f"{float(dl)/1024/1024:.1f} MB")
        except Exception:
            pass
    speed = task.get("speed")
    if speed:
        try:
            parts.append(f"{float(speed)/1024/1024:.2f} MB/s")
        except Exception:
            pass
    eta = task.get("eta")
    if eta:
        try:
            e = int(eta)
            if e >= 3600:
                parts.append(f"ETA {e//3600}h {(e%3600)//60}m")
            elif e >= 60:
                parts.append(f"ETA {e//60}m {e%60}s")
            else:
                parts.append(f"ETA {e}s")
        except Exception:
            pass
    text = "  ".join(parts)
    err = task.get("error_message")
    if err and status in ("Failed", "Cancelled"):
        text += f"   -  {translate_known_error(err)}"
    return text


class QueuePage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)
        layout.addWidget(PageHeader(self.tr("Download Queue"), self.tr("Monitor active and queued downloads")))

        actions = QHBoxLayout()
        self.cancel_btn = QPushButton(self.tr("Cancel Selected"))
        self.cancel_btn.setProperty("class", "Danger")
        self.cancel_btn.clicked.connect(self._cancel_selected)
        self.retry_btn = QPushButton(self.tr("Retry Selected"))
        self.retry_btn.clicked.connect(self._retry_selected)
        self.open_btn = QPushButton(self.tr("Open Folder"))
        self.open_btn.clicked.connect(self._open_selected_folder)
        self.clear_btn = QPushButton(self.tr("Clear Finished"))
        self.clear_btn.clicked.connect(self._clear_finished)
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.retry_btn)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.clear_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._update_action_buttons)
        layout.addWidget(self.list_widget, 1)
        self.empty = EmptyState(
            self.tr("Your queue is clear"),
            self.tr("Downloads you start will appear here."),
            icon="\u2193",  # ↓
        )
        # stretch=1: when the list is hidden, the empty state fills the page
        # instead of leaving a large blank area above a bottom-pinned card.
        layout.addWidget(self.empty, 1)
        self._refresh_empty()
        self._update_action_buttons()

    def set_controller(self, controller) -> None:
        self._controller = controller

    def _refresh_empty(self) -> None:
        has = self.list_widget.count() > 0
        self.list_widget.setVisible(has)
        self.empty.setVisible(not has)

    def _row_for_item(self, item: QListWidgetItem) -> _QueueRow:
        row = self.list_widget.itemWidget(item)
        if not isinstance(row, _QueueRow):
            row = _QueueRow()
            self.list_widget.setItemWidget(item, row)
            item.setSizeHint(row.sizeHint())
        return row

    def upsert_task(self, task: dict) -> None:
        tid = task.get("id")
        if not tid:
            return
        status = task.get("status")
        if hasattr(status, "value"):
            task = {**task, "status": status.value}
        # merge with existing
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == tid:
                existing = item.data(Qt.UserRole + 1) or {}
                merged = {**existing, **{k: v for k, v in task.items() if v is not None}}
                item.setData(Qt.UserRole + 1, merged)
                self._row_for_item(item).update_from(merged)
                self._refresh_empty()
                self._update_action_buttons()
                return
        item = QListWidgetItem()
        item.setData(Qt.UserRole, tid)
        item.setData(Qt.UserRole + 1, task)
        self.list_widget.insertItem(0, item)
        self._row_for_item(item).update_from(task)
        self._refresh_empty()
        self._update_action_buttons()

    def refresh_data(self) -> None:
        # Load active/recent tasks from DB for visibility after restart/UI refresh
        try:
            from app.database.repositories.downloads_repo import DownloadsRepository
            repo = DownloadsRepository()
            rows = repo.list_by_statuses(["Queued", "Extracting", "Downloading", "Processing"], limit=200)
            failed_recent = repo.list_by_statuses(["Failed", "Cancelled"], limit=20)
            rows = rows + [r for r in failed_recent if r.get("id") not in {x.get("id") for x in rows}]
        except Exception:
            return
        # upsert from DB
        for r in rows:
            self.upsert_task(r)
        self._refresh_empty()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_data()

    def _cancel_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item or not self._controller:
            return
        tid = item.data(Qt.UserRole)
        task = item.data(Qt.UserRole + 1) or {}
        if task.get("status") in ("Completed", "Failed", "Cancelled"):
            return
        if hasattr(self._controller, "cancel_download"):
            self._controller.cancel_download(tid)

    def _retry_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item or not self._controller:
            return
        task = item.data(Qt.UserRole + 1) or {}
        tid = item.data(Qt.UserRole)
        if task.get("status") not in ("Failed", "Cancelled"):
            return
        if hasattr(self._controller, "retry_download"):
            self._controller.retry_download(tid)

    def _clear_finished(self) -> None:
        to_remove = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            task = item.data(Qt.UserRole + 1) or {}
            if task.get("status") in ("Completed", "Failed", "Cancelled"):
                to_remove.append(i)
        for i in reversed(to_remove):
            self.list_widget.takeItem(i)
        self._refresh_empty()
        self._update_action_buttons()

    def _open_selected_folder(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        task = item.data(Qt.UserRole + 1) or {}
        path = (task.get("output_path") or "").strip()
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

    def _update_action_buttons(self) -> None:
        item = self.list_widget.currentItem()
        status = None
        task = {}
        if item:
            task = item.data(Qt.UserRole + 1) or {}
            status = task.get("status")
        self.cancel_btn.setEnabled(status in ("Queued", "Extracting", "Downloading", "Processing"))
        self.retry_btn.setEnabled(status in ("Failed", "Cancelled"))
        self.open_btn.setEnabled(bool(task.get("output_path")))
