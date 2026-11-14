"""Dashboard page."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.database.repositories.downloads_repo import DownloadsRepository
from app.ui.widgets.common import EmptyState, PageHeader, StatCard


class DashboardPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.repo = DownloadsRepository()
        self.on_quick_download = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = PageHeader("Dashboard", "Overview of downloads and recent activity")
        header_row.addWidget(header, 1)
        self.quick_btn = QPushButton("New Download")
        self.quick_btn.setProperty("class", "Primary")
        self.quick_btn.clicked.connect(self._quick_download)
        header_row.addWidget(self.quick_btn)
        layout.addLayout(header_row)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.active_card = StatCard("Active downloads", "0")
        self.completed_card = StatCard("Completed downloads", "0")
        self.failed_card = StatCard("Failed / Cancelled", "0")
        self.size_card = StatCard("Total downloaded size", "0 MB")
        stats.addWidget(self.active_card, 0, 0)
        stats.addWidget(self.completed_card, 0, 1)
        stats.addWidget(self.failed_card, 0, 2)
        stats.addWidget(self.size_card, 0, 3)
        layout.addLayout(stats)

        layout.addWidget(QLabel("Recent activity"))
        self.recent_list = QListWidget()
        layout.addWidget(self.recent_list, 1)
        self.empty = EmptyState("No recent activity", "Start a new download to see activity here.")
        layout.addWidget(self.empty)

    def refresh_data(self) -> None:
        try:
            counts = self.repo.counts()
            recent = self.repo.list_recent(10)
            total_bytes = self.repo.total_completed_bytes()
        except Exception:
            counts, recent, total_bytes = {}, [], 0
        active = sum(counts.get(s, 0) for s in ("Queued", "Extracting", "Downloading", "Processing"))
        completed = counts.get("Completed", 0)
        failed = counts.get("Failed", 0) + counts.get("Cancelled", 0)
        self.active_card.set_value(str(active))
        self.completed_card.set_value(str(completed))
        self.failed_card.set_value(str(failed))
        if total_bytes > 0:
            mb = total_bytes / (1024 * 1024)
            if mb >= 1024:
                self.size_card.set_value(f"{mb/1024:.2f} GB")
            else:
                self.size_card.set_value(f"{mb:.1f} MB")
        else:
            self.size_card.set_value("0 MB")

        self.recent_list.clear()
        for r in recent:
            title = r.get("title") or r.get("source_url") or r.get("id")
            self.recent_list.addItem(QListWidgetItem(f"[{r.get('status','')}] {title}"))
        has = self.recent_list.count() > 0
        self.recent_list.setVisible(has)
        self.empty.setVisible(not has)

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_data()

    def _quick_download(self) -> None:
        if callable(self.on_quick_download):
            self.on_quick_download()