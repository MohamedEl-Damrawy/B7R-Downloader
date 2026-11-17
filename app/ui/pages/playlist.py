"""Playlists page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.download_items_repo import DownloadItemsRepository
from app.database.repositories.playlists_repo import PlaylistsRepository
from app.models.playlist import PlaylistEntry, PlaylistMetadata
from app.ui.widgets.common import CardFrame, EmptyState, PageHeader


class PlaylistsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = None
        self._playlist = None
        self._item_widgets: dict[str, QListWidgetItem] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)
        layout.addWidget(
            PageHeader(self.tr("Playlists"), self.tr("Inspect playlists and select individual items to download"))
        )

        saved_row = QHBoxLayout()
        saved_row.addWidget(QLabel(self.tr("Saved playlists:")))
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(280)
        self.load_saved_btn = QPushButton(self.tr("Load"))
        saved_row.addWidget(self.saved_combo, 1)
        saved_row.addWidget(self.load_saved_btn)
        layout.addLayout(saved_row)

        self.opts_row = QWidget()
        opts_layout = QHBoxLayout(self.opts_row)
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(QLabel(self.tr("Quality:")))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem(self.tr("Best available"), "best")
        self.quality_combo.addItem(self.tr("1080p (if available)"), "1080p")
        self.quality_combo.addItem(self.tr("720p (if available)"), "720p")
        self.quality_combo.addItem(self.tr("480p (if available)"), "480p")
        # FEAT-01: audio-only presets (converted with FFmpegExtractAudio).
        self.quality_combo.addItem(self.tr("Audio only — MP3"), "audio_mp3")
        self.quality_combo.addItem(self.tr("Audio only — M4A"), "audio_m4a")
        opts_layout.addWidget(self.quality_combo)
        opts_layout.addWidget(QLabel(self.tr("Output:")))
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText(self.tr("Default download folder"))
        opts_layout.addWidget(self.output_input, 1)
        layout.addWidget(self.opts_row)

        # Actions row wrapped in a container so it can be hidden with the
        # quality/output row when no playlist is loaded.
        self.actions_row = QWidget()
        actions = QHBoxLayout(self.actions_row)
        actions.setContentsMargins(0, 0, 0, 0)
        self.refresh_btn = QPushButton(self.tr("Refresh Status"))
        self.select_all_btn = QPushButton(self.tr("Select All"))
        self.deselect_all_btn = QPushButton(self.tr("Deselect All"))
        self.retry_failed_btn = QPushButton(self.tr("Retry Failed"))
        self.download_selected_btn = QPushButton(self.tr("Download Selected"))
        self.download_selected_btn.setProperty("class", "Primary")
        self.download_selected_btn.setEnabled(False)
        self.selected_label = QLabel(self.tr("Selected: %d") % 0)
        self.selected_label.setProperty("class", "Subtitle")
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.select_all_btn)
        actions.addWidget(self.deselect_all_btn)
        actions.addWidget(self.retry_failed_btn)
        actions.addWidget(self.download_selected_btn)
        actions.addStretch(1)
        actions.addWidget(self.selected_label)
        layout.addWidget(self.actions_row)

        self.card = CardFrame()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        self.meta_label = QLabel(self.tr("No playlist loaded."))
        self.meta_label.setWordWrap(True)
        self.meta_label.setProperty("class", "Subtitle")
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)
        card_layout.addWidget(self.meta_label)
        card_layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.card, 1)

        self.empty_state = EmptyState(
            self.tr("No playlist loaded"),
            self.tr("Choose a saved playlist and select Load to view its videos."),
            icon="playlists",  # Lucide list-video
        )
        self.empty_state.setVisible(False)
        # stretch=1: fills the page when the card is hidden (no blank void).
        layout.addWidget(self.empty_state, 1, Qt.AlignHCenter | Qt.AlignVCenter)

        self.load_saved_btn.clicked.connect(self._load_saved_playlist)
        self.refresh_btn.clicked.connect(self.refresh_item_statuses)
        self.retry_failed_btn.clicked.connect(self._retry_failed)
        self.select_all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.deselect_all_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        self.list_widget.itemChanged.connect(self._update_selected_count)
        self.download_selected_btn.clicked.connect(self._download_selected)
        self._show_empty(True)

    def set_controller(self, controller) -> None:
        self._controller = controller

    def _show_empty(self, empty: bool) -> None:
        self.card.setVisible(not empty)
        self.empty_state.setVisible(empty)
        # Quality/Output + action rows are meaningless with no playlist loaded.
        self.opts_row.setVisible(not empty)
        self.actions_row.setVisible(not empty)

    def refresh_saved_playlists(self) -> None:
        current = self.saved_combo.currentData()
        self.saved_combo.blockSignals(True)
        self.saved_combo.clear()
        self.saved_combo.addItem(self.tr("Select a saved playlist..."), None)
        try:
            rows = PlaylistsRepository().list_recent(30)
            for r in rows:
                title = r.get("title") or "Playlist"
                count = r.get("total_entries") or 0
                self.saved_combo.addItem(f"{title} ({count})", r.get("id"))
        except Exception:
            pass
        # restore selection if possible
        if current:
            idx = self.saved_combo.findData(current)
            if idx >= 0:
                self.saved_combo.setCurrentIndex(idx)
        self.saved_combo.blockSignals(False)

    def _load_saved_playlist(self) -> None:
        pid = self.saved_combo.currentData()
        if not pid:
            QMessageBox.information(self, self.tr("Select playlist"), self.tr("Choose a saved playlist to load."))
            return
        try:
            pl = PlaylistsRepository().get(str(pid))
            items = DownloadItemsRepository().list_by_playlist(str(pid))
            if not pl:
                QMessageBox.warning(self, self.tr("Not found"), self.tr("Saved playlist could not be found."))
                return
            entries = []
            for it in items:
                raw_id = str(it.get("id") or "")
                entry_id = raw_id.split(":", 1)[1] if ":" in raw_id else (str(it.get("entry_index") or raw_id))
                status = str(it.get("status") or "Available")
                available = status not in ("Unavailable",)
                entries.append(
                    PlaylistEntry(
                        entry_id=entry_id,
                        source_url=it.get("source_url") or "",
                        title=it.get("title") or "",
                        thumbnail_url=it.get("thumbnail_url") or "",
                        index=it.get("entry_index"),
                        available=available,
                    )
                )
            meta = PlaylistMetadata(
                source_url=pl.get("source_url") or "",
                title=pl.get("title") or "Playlist",
                thumbnail_url=pl.get("thumbnail_url") or "",
                entries=entries,
                total_entries=int(pl.get("total_entries") or len(entries)),
            )
            try:
                setattr(meta, "playlist_id", str(pid))
            except Exception:
                pass
            for e in entries:
                try:
                    setattr(e, "playlist_item_id", f"{pid}:{e.entry_id}")
                except Exception:
                    pass
            self.set_playlist(meta)
            self.refresh_item_statuses()
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to load saved playlist: %s") % exc)

    def _item_id_for_entry(self, playlist_id: str | None, entry) -> str | None:
        if not playlist_id:
            return getattr(entry, "playlist_item_id", None)
        eid = getattr(entry, "entry_id", None)
        if eid is None:
            eid = getattr(entry, "index", None)
        if eid is None:
            return getattr(entry, "playlist_item_id", None)
        return f"{playlist_id}:{eid}"

    def _format_entry_text(
        self,
        title: str,
        available: bool,
        status: str | None = None,
        progress: float | None = None,
        error: str | None = None,
    ) -> str:
        from app.ui.i18n import translate_known_error

        suffix = "" if available else self.tr(" (Unavailable)")
        text = f"{title}{suffix}"
        if status and status not in ("Available", "Unavailable"):
            if progress is not None and status in ("Queued", "Extracting", "Downloading", "Processing"):
                text += f"  [{status} {float(progress):.0f}%]"
            else:
                text += f"  [{status}]"
            if error and status in ("Failed", "Cancelled"):
                short = translate_known_error(error).strip().replace("\n", " ")
                if len(short) > 80:
                    short = short[:77] + "..."
                if short:
                    text += f"  -  {short}"
        return text

    def set_playlist(self, playlist) -> None:
        self._playlist = playlist
        self.list_widget.clear()
        self._item_widgets = {}
        if not playlist:
            self.meta_label.setText(self.tr("No playlist loaded."))
            self._show_empty(True)
            self._update_selected_count()
            return
        try:
            from app.core.paths import get_default_download_dir
            if not self.output_input.text().strip():
                self.output_input.setText(str(get_default_download_dir()))
        except Exception:
            pass
        entries = getattr(playlist, "entries", []) or []
        self.meta_label.setText(self.tr("%s   -   %d entries") % (getattr(playlist, "title", "Playlist"), len(entries)))
        playlist_id = getattr(playlist, "playlist_id", None)
        status_map = self._load_status_map(playlist_id)
        for e in entries:
            title = getattr(e, "title", "") or self.tr("Untitled")
            available = bool(getattr(e, "available", True))
            item_id = self._item_id_for_entry(playlist_id, e)
            if item_id:
                try:
                    setattr(e, "playlist_item_id", item_id)
                except Exception:
                    pass
            st = status_map.get(item_id or "", {})
            status = st.get("status") if st else ("Unavailable" if not available else "Available")
            progress = st.get("progress") if st else None
            error = st.get("error_message") if st else None
            item = QListWidgetItem(self._format_entry_text(title, available, status, progress, error))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, e)
            item.setData(Qt.UserRole + 1, {"title": title, "available": available, "item_id": item_id})
            if not available:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setForeground(Qt.gray)
            self.list_widget.addItem(item)
            if item_id:
                self._item_widgets[item_id] = item
        self._show_empty(len(entries) == 0)
        self._update_selected_count()
        self.refresh_saved_playlists()

    def _load_status_map(self, playlist_id: str | None) -> dict[str, dict]:
        if not playlist_id:
            return {}
        try:
            from app.database.repositories.download_items_repo import DownloadItemsRepository
            rows = DownloadItemsRepository().list_by_playlist(playlist_id)
            return {str(r.get("id")): r for r in rows if r.get("id")}
        except Exception:
            return {}

    def refresh_item_statuses(self) -> None:
        playlist = self._playlist
        if not playlist:
            return
        playlist_id = getattr(playlist, "playlist_id", None)
        if not playlist_id:
            return
        status_map = self._load_status_map(playlist_id)
        for item_id, item in self._item_widgets.items():
            meta = item.data(Qt.UserRole + 1) or {}
            title = meta.get("title") or self.tr("Untitled")
            available = bool(meta.get("available", True))
            st = status_map.get(item_id, {})
            status = st.get("status") or ("Unavailable" if not available else "Available")
            progress = st.get("progress")
            error = st.get("error_message")
            item.setText(self._format_entry_text(title, available, status, progress, error))

    def _set_all(self, state: Qt.CheckState) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            entry = item.data(Qt.UserRole)
            if entry is not None and not getattr(entry, "available", True):
                item.setCheckState(Qt.Unchecked)
                continue
            item.setCheckState(state)
        self._update_selected_count()

    def _selected_entries(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                entry = item.data(Qt.UserRole)
                if entry is not None and getattr(entry, "available", True):
                    selected.append(entry)
        return selected

    def _update_selected_count(self) -> None:
        count = len(self._selected_entries())
        self.selected_label.setText(self.tr("Selected: %d") % count)
        self.download_selected_btn.setEnabled(count > 0 and self._controller is not None and self._playlist is not None)

    def _download_selected(self) -> None:
        if not self._controller or not self._playlist:
            return
        selected = self._selected_entries()
        if not selected:
            QMessageBox.information(
                self,
                self.tr("No selection"),
                self.tr("Select at least one available playlist item."),
            )
            return
        output_dir = self.output_input.text().strip()
        if not output_dir:
            from app.core.paths import get_default_download_dir
            output_dir = str(get_default_download_dir())
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Invalid output folder"), self.tr("Cannot use output folder:\n%s") % exc)
            return
        try:
            from app.engine.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
            if not get_ffmpeg_path() and not get_ffprobe_path():
                reply = QMessageBox.warning(
                    self,
                    self.tr("FFmpeg not detected"),
                    self.tr("FFmpeg/FFprobe were not found. Some downloads or merges may fail.\nContinue anyway?"),
                    QMessageBox.Ok | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                if reply != QMessageBox.Ok:
                    return
        except Exception:
            pass
        quality = self.quality_combo.currentData() or "best"
        playlist_url = getattr(self._playlist, "source_url", "")
        playlist_id = getattr(self._playlist, "playlist_id", None)
        try:
            ids = self._controller.start_playlist_downloads(
                playlist_url=playlist_url,
                output_dir=output_dir,
                quality=quality,
                entries=selected,
                playlist_id=playlist_id,
                playlist_title=str(getattr(self._playlist, "title", "") or ""),
            )
            QMessageBox.information(
                self,
                self.tr("Downloads queued"),
                self.tr("Queued %d selected item(s).") % len(ids),
            )
            self.refresh_item_statuses()
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Error"), str(exc))

    def _retry_failed(self) -> None:
        if not self._controller or not self._playlist:
            QMessageBox.information(
                self,
                self.tr("Unavailable"),
                self.tr("Load a playlist and ensure controller is ready."),
            )
            return
        playlist_id = getattr(self._playlist, "playlist_id", None)
        if not playlist_id:
            QMessageBox.information(
                self,
                self.tr("Not saved"),
                self.tr("Playlist must be saved/loaded with an ID to retry items."),
            )
            return
        # Determine target item IDs: selected failed/cancelled, else all failed/cancelled
        selected_items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                meta = item.data(Qt.UserRole + 1) or {}
                iid = meta.get("item_id")
                if iid:
                    selected_items.append(iid)
        try:
            status_map = self._load_status_map(playlist_id)
        except Exception:
            status_map = {}
        if selected_items:
            targets = [
                iid for iid in selected_items
                if (status_map.get(iid, {}).get("status") in ("Failed", "Cancelled"))
            ]
        else:
            targets = [iid for iid, st in status_map.items() if st.get("status") in ("Failed", "Cancelled")]
        if not targets:
            QMessageBox.information(
                self,
                self.tr("Nothing to retry"),
                self.tr("No failed or cancelled items to retry."),
            )
            return
        retried = 0
        missing = 0
        for iid in targets:
            st = status_map.get(iid, {})
            dlid = st.get("download_id")
            if not dlid:
                missing += 1
                continue
            if hasattr(self._controller, "retry_download"):
                try:
                    new_id = self._controller.retry_download(str(dlid))
                    if new_id:
                        retried += 1
                except Exception:
                    pass
        msg = self.tr("Queued retry for %d item(s).") % retried
        if missing:
            msg += " " + self.tr("%d item(s) had no previous download task to retry.") % missing
        QMessageBox.information(self, self.tr("Retry"), msg)

        self.refresh_item_statuses()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_saved_playlists()
        self.refresh_item_statuses()
