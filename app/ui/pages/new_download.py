"""New Download page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import UnsupportedSourceError
from app.ui.widgets.common import CardFrame, PageHeader


class NewDownloadPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = None
        self._last_video = None
        self._last_playlist = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(PageHeader("New Download", "Paste a supported URL to extract metadata and choose quality"))

        card = CardFrame()
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        self.paste_btn = QPushButton("Paste")
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.paste_btn)
        form.addRow("URL", url_row)

        self.format_combo = QComboBox()
        self.format_combo.addItem("Best available (recommended)", "best")
        self.format_combo.addItem("1080p (if available)", "1080p")
        self.format_combo.addItem("720p (if available)", "720p")
        self.format_combo.addItem("480p (if available)", "480p")
        form.addRow("Quality", self.format_combo)

        dest_row = QHBoxLayout()
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Default download folder (configured in Settings)")
        self.browse_dest_btn = QPushButton("Browse")
        self.browse_dest_btn.clicked.connect(self._browse_destination)
        dest_row.addWidget(self.dest_input, 1)
        dest_row.addWidget(self.browse_dest_btn)
        form.addRow("Destination", dest_row)
        self._apply_default_destination()

        self.thumb_label = QLabel("Thumbnail preview: none")
        self.thumb_label.setMinimumHeight(120)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("color: #91A2B5; background-color: #0f1a29; border: 1px solid #2a3c56; border-radius: 8px;")
        self.thumb_label.setWordWrap(True)
        form.addRow("Thumbnail", self.thumb_label)

        self.preview_label = QLabel("Metadata preview will appear here after extraction.")
        self.preview_label.setStyleSheet("color: #91A2B5;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Preview", self.preview_label)

        actions = QHBoxLayout()
        self.extract_btn = QPushButton("Extract Metadata")
        self.extract_btn.setProperty("class", "Primary")
        self.download_btn = QPushButton("Download")
        self.download_btn.setEnabled(False)
        actions.addWidget(self.extract_btn)
        actions.addWidget(self.download_btn)
        actions.addStretch(1)
        form.addRow("", actions)

        layout.addWidget(card)
        layout.addStretch(1)

        self.paste_btn.clicked.connect(self._paste_from_clipboard)
        self.extract_btn.clicked.connect(self._on_extract)
        self.download_btn.clicked.connect(self._on_download)

    def set_controller(self, controller) -> None:
        self.controller = controller
        self.controller.metadata_result.connect(self.on_metadata_result)
        self.controller.metadata_error.connect(self.on_metadata_error)
        self.controller.metadata_finished.connect(self.on_metadata_finished)
        if hasattr(controller, "task_error"):
            controller.task_error.connect(self.on_task_error)

    def _paste_from_clipboard(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            self.url_input.setText(cb.text().strip())

    def _browse_destination(self) -> None:
        current = self.dest_input.text().strip()
        if not current:
            try:
                from app.core.paths import get_default_download_dir
                current = str(get_default_download_dir())
            except Exception:
                current = ""
        folder = QFileDialog.getExistingDirectory(self, "Select download folder", current)
        if folder:
            self.dest_input.setText(folder)

    def _on_extract(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a supported video or playlist URL.")
            return
        from app.core.validators import is_http_url
        if not is_http_url(url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid http(s) URL.")
            return
        if not self.controller:
            QMessageBox.critical(self, "Unavailable", "Metadata controller is not initialized.")
            return
        self._last_video = None
        self._last_playlist = None
        self._set_thumbnail("", "")
        self.extract_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.preview_label.setText("Extracting metadata...")
        self.controller.extract_metadata(url)

    def on_metadata_result(self, payload: dict) -> None:
        video = (payload or {}).get("video")
        playlist = (payload or {}).get("playlist")
        self._last_video = video
        self._last_playlist = playlist
        # Reset quality options to defaults, then enrich for single video
        self.format_combo.clear()
        self.format_combo.addItem("Best available (recommended)", "best")
        self.format_combo.addItem("1080p (if available)", "1080p")
        self.format_combo.addItem("720p (if available)", "720p")
        self.format_combo.addItem("480p (if available)", "480p")
        if playlist:
            count = len(getattr(playlist, "entries", []) or [])
            thumb = getattr(playlist, "thumbnail_url", "") or ""
            self._set_thumbnail(thumb, getattr(playlist, "title", "Playlist"))
            thumb_line = f"\nThumbnail: {'available' if thumb else 'not available'}"
            self.preview_label.setText(
                f"Playlist detected: {getattr(playlist, 'title', 'Playlist')}\nEntries: {count}{thumb_line}\nURL: {getattr(playlist, 'source_url', '')}\n\nOpen Playlists to review and select items."
            )
            self.download_btn.setEnabled(False)
        elif video:
            formats = getattr(video, "formats", []) or []
            # Add a few concrete format options from metadata for user choice
            seen = set()
            added = 0
            for f in formats:
                fid = getattr(f, "format_id", None)
                label = getattr(f, "label", None) or fid
                height = getattr(f, "height", None)
                if not fid or fid in seen:
                    continue
                # prefer video-capable or notable entries, limit count
                if height and added < 12:
                    self.format_combo.addItem(f"{label}", f"id:{fid}")
                    seen.add(fid)
                    added += 1
            duration = getattr(video, "duration", None)
            uploader = getattr(video, "uploader", None)
            thumb = getattr(video, "thumbnail_url", "") or ""
            self._set_thumbnail(thumb, getattr(video, "title", "Video"))
            extra = []
            if duration:
                try:
                    mins, secs = divmod(int(duration), 60)
                    hrs, mins = divmod(mins, 60)
                    extra.append(f"Duration: {hrs:d}:{mins:02d}:{secs:02d}" if hrs else f"Duration: {mins:d}:{secs:02d}")
                except Exception:
                    pass
            if uploader:
                extra.append(f"Uploader: {uploader}")
            extra.append(f"Thumbnail: {'available' if thumb else 'not available'}")
            extra_text = ("\n" + "\n".join(extra)) if extra else ""
            self.preview_label.setText(
                f"Title: {getattr(video, 'title', '')}\nURL: {getattr(video, 'source_url', '')}{extra_text}\nFormats found: {len(formats)}\n"
                "Quality selection uses sensible fallbacks when requested quality is unavailable."
            )
            self.download_btn.setEnabled(True)
        else:
            self._set_thumbnail("", "")
            self.preview_label.setText("No metadata could be extracted.")
            self.download_btn.setEnabled(False)

    def _on_download(self) -> None:
        url = self.url_input.text().strip()
        if not url or not self._last_video:
            QMessageBox.warning(self, "Not ready", "Extract video metadata first.")
            return
        if not self.controller or not hasattr(self.controller, "start_download"):
            QMessageBox.critical(self, "Unavailable", "Download controller is not available.")
            return
        output_dir = self.dest_input.text().strip()
        if not output_dir:
            from app.core.paths import get_default_download_dir
            output_dir = str(get_default_download_dir())
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid output folder", f"Cannot use output folder:\n{exc}")
            return
        try:
            from app.engine.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
            if not get_ffmpeg_path() and not get_ffprobe_path():
                reply = QMessageBox.warning(
                    self,
                    "FFmpeg not detected",
                    "FFmpeg/FFprobe were not found. Some downloads or merges may fail.\nContinue anyway?",
                    QMessageBox.Ok | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                if reply != QMessageBox.Ok:
                    return
        except Exception:
            pass
        quality = self.format_combo.currentData() or "best"
        task_id = self.controller.start_download(
            url=self._last_video.source_url or url,
            output_dir=output_dir,
            quality=str(quality),
            title=getattr(self._last_video, "title", ""),
            thumbnail_url=getattr(self._last_video, "thumbnail_url", ""),
        )
        self.preview_label.setText(self.preview_label.text() + f"\n\nQueued download task: {task_id[:8]}...")
        self.download_btn.setEnabled(False)

    def on_task_error(self, task_id: str, message: str) -> None:
        QMessageBox.critical(self, "Download Error", message or "Download failed.")

    def on_metadata_error(self, message: str) -> None:
        self.preview_label.setText("Failed to extract metadata.")
        QMessageBox.critical(self, "Metadata Error", message or "Unable to extract metadata.")

    def on_metadata_finished(self) -> None:
        self.extract_btn.setEnabled(True)

    def _apply_default_destination(self) -> None:
        try:
            from app.core.constants import SETTINGS_DEFAULT_DOWNLOAD_PATH
            from app.core.paths import get_default_download_dir
            from app.services.settings_service import SettingsService
            path = SettingsService().get(SETTINGS_DEFAULT_DOWNLOAD_PATH) or str(get_default_download_dir())
            self.dest_input.setText(str(path))
        except Exception:
            pass

    def _set_thumbnail(self, url: str, title: str = "") -> None:
        # Best-effort async thumbnail load when Qt network stack is available at runtime.
        self.thumb_label.clear()
        self.thumb_label.setText("Thumbnail preview: none")
        if not url:
            return
        self.thumb_label.setText("Thumbnail: available (loading preview...)")
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QPixmap
            from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
        except Exception:
            self.thumb_label.setText("Thumbnail: available (preview requires network-capable runtime)")
            return
        if not hasattr(self, "_netman") or self._netman is None:
            self._netman = QNetworkAccessManager(self)

        req = QNetworkRequest(QUrl(url))
        # Harden: bounded transfer time and payload size for a metadata URL.
        try:
            req.setTransferTimeout(8000)
        except Exception:
            pass
        reply = self._netman.get(req)

        def _done():
            try:
                data = bytes(reply.readAll())
                if len(data) > 5 * 1024 * 1024:
                    self.thumb_label.setText("Thumbnail: available (preview too large)")
                    return
                pix = QPixmap()
                if pix.loadFromData(data):
                    scaled = pix.scaledToHeight(120, Qt.SmoothTransformation)
                    self.thumb_label.setPixmap(scaled)
                    self.thumb_label.setText("")
                else:
                    self.thumb_label.setText("Thumbnail: available (could not render)")
            except Exception:
                self.thumb_label.setText("Thumbnail: available (could not render)")
            finally:
                reply.deleteLater()

        reply.finished.connect(_done)

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if not self.dest_input.text().strip():
            self._apply_default_destination()
