"""Main application window shell."""

from __future__ import annotations

import hashlib
import uuid

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QStatusBar, QWidget

from app.controllers.download_controller import DownloadController
from app.core.constants import APP_NAME, APP_VERSION
from app.database.repositories.download_items_repo import DownloadItemsRepository
from app.database.repositories.playlists_repo import PlaylistsRepository
from app.models.download import utc_now_iso
from app.ui.navigation import Sidebar
from app.ui.pages.completed import CompletedPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.history import HistoryPage
from app.ui.pages.new_download import NewDownloadPage
from app.ui.pages.playlist import PlaylistsPage
from app.ui.pages.queue import QueuePage
from app.ui.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1200, 760)

        self.download_controller = DownloadController(self)

        # Debounced refresh: progress events arrive at high frequency; re-reading
        # dashboard/completed/history from the DB on every tick froze the UI.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_views)

        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.navigate_to)
        self.stack = QStackedWidget()

        self.pages = {
            "dashboard": DashboardPage(),
            "new_download": NewDownloadPage(),
            "playlists": PlaylistsPage(),
            "queue": QueuePage(),
            "completed": CompletedPage(),
            "history": HistoryPage(),
            "settings": SettingsPage(),
        }
        if hasattr(self.pages["dashboard"], "on_quick_download"):
            self.pages["dashboard"].on_quick_download = lambda: self.navigate_to("new_download")
        self.page_index: dict[str, int] = {}
        for key, page in self.pages.items():
            self.page_index[key] = self.stack.addWidget(page)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.status = QStatusBar()
        self.status.showMessage("Ready")
        self.setStatusBar(self.status)

        self._wire_controllers()
        self.navigate_to("dashboard")

    def _wire_controllers(self) -> None:
        nd = self.pages["new_download"]
        if hasattr(nd, "set_controller"):
            nd.set_controller(self.download_controller)
        q = self.pages.get("queue")
        if q and hasattr(q, "set_controller"):
            q.set_controller(self.download_controller)
        pl = self.pages.get("playlists")
        if pl and hasattr(pl, "set_controller"):
            pl.set_controller(self.download_controller)
        hist = self.pages.get("history")
        if hist and hasattr(hist, "set_controller"):
            hist.set_controller(self.download_controller)
        comp = self.pages.get("completed")
        if comp and hasattr(comp, "set_controller"):
            comp.set_controller(self.download_controller)

        self.download_controller.metadata_result.connect(self._on_metadata_result)
        self.download_controller.task_added.connect(self._on_task_added)
        self.download_controller.task_updated.connect(self._on_task_updated)
        self.download_controller.task_error.connect(self._on_task_error)
        self.download_controller.task_finished.connect(self._on_task_finished)

    def _on_metadata_result(self, payload: dict) -> None:
        playlist = (payload or {}).get("playlist")
        if playlist and "playlists" in self.pages:
            self._persist_playlist(playlist)
            self.pages["playlists"].set_playlist(playlist)
            self.navigate_to("playlists")

    def _persist_playlist(self, playlist) -> str | None:
        try:
            source_url = getattr(playlist, "source_url", "") or ""
            if not source_url:
                return None
            pid = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:16]
            PlaylistsRepository().upsert(
                {
                    "id": pid,
                    "source_url": source_url,
                    "title": getattr(playlist, "title", "") or "Playlist",
                    "thumbnail_url": getattr(playlist, "thumbnail_url", "") or "",
                    "total_entries": int(
                        getattr(playlist, "total_entries", 0) or len(getattr(playlist, "entries", []) or [])
                    ),
                    "created_at": utc_now_iso(),
                }
            )
            try:
                setattr(playlist, "playlist_id", pid)
            except Exception:
                pass
            items = []
            for e in (getattr(playlist, "entries", []) or []):
                idx = getattr(e, "index", None)
                eid = getattr(e, "entry_id", None) or idx or uuid.uuid4().hex
                item_id = f"{pid}:{eid}"
                try:
                    setattr(e, "playlist_item_id", item_id)
                except Exception:
                    pass
                items.append(
                    {
                        "id": item_id,
                        "playlist_id": pid,
                        "download_id": None,
                        "entry_index": idx,
                        "source_url": getattr(e, "source_url", "") or "",
                        "title": getattr(e, "title", "") or "",
                        "thumbnail_url": getattr(e, "thumbnail_url", "") or "",
                        "status": "Available" if getattr(e, "available", True) else "Unavailable",
                        "progress": 0.0,
                        "output_path": None,
                        "error_message": None,
                    }
                )
            if items:
                DownloadItemsRepository().upsert_many(items)
            return pid
        except Exception:
            return None

    def _on_task_added(self, task: dict) -> None:
        if "queue" in self.pages:
            self.pages["queue"].upsert_task(task)
        self.status.showMessage("Download started")
        self._refresh_views_soon()

    def _on_task_updated(self, task: dict) -> None:
        if "queue" in self.pages:
            self.pages["queue"].upsert_task(task)
        self._refresh_views_soon()

    def _on_task_error(self, task_id: str, message: str) -> None:
        self.status.showMessage(f"Task {task_id[:8]}: {message}")

    def _on_task_finished(self, task_id: str) -> None:
        self.status.showMessage("Ready")
        self._refresh_views_soon()

    def _refresh_views_soon(self) -> None:
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def _refresh_views(self) -> None:
        for key in ("dashboard", "completed", "history"):
            page = self.pages.get(key)
            if page and hasattr(page, "refresh_data"):
                try:
                    page.refresh_data()
                except Exception:
                    pass
        pl = self.pages.get("playlists")
        if pl and hasattr(pl, "refresh_item_statuses"):
            try:
                pl.refresh_item_statuses()
            except Exception:
                pass

    def navigate_to(self, key: str) -> None:
        idx = self.page_index.get(key)
        if idx is not None:
            self.stack.setCurrentIndex(idx)
            self.sidebar.set_active(key)
            page = self.pages.get(key)
            if page and hasattr(page, "refresh_data"):
                try:
                    page.refresh_data()
                except Exception:
                    pass
