"""New Download page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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

from app.ui.widgets.common import CardFrame, PageHeader


class NewDownloadPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = None
        self._last_video = None
        self._last_playlist = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(24)
        layout.addWidget(
            PageHeader(self.tr("New Download"), self.tr("Paste a supported URL to extract metadata and choose quality"))
        )

        card = CardFrame()
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        self.paste_btn = QPushButton(self.tr("Paste"))
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.paste_btn)
        form.addRow(self.tr("URL"), url_row)

        self.format_combo = QComboBox()
        self._add_default_quality_items()
        form.addRow(self.tr("Quality"), self.format_combo)

        dest_row = QHBoxLayout()
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText(self.tr("Default download folder (configured in Settings)"))
        self.browse_dest_btn = QPushButton(self.tr("Browse"))
        self.browse_dest_btn.clicked.connect(self._browse_destination)
        dest_row.addWidget(self.dest_input, 1)
        dest_row.addWidget(self.browse_dest_btn)
        form.addRow(self.tr("Destination"), dest_row)
        self._apply_default_destination()

        # FEAT-02: optional extras applied by yt-dlp postprocessors.
        extras_row = QHBoxLayout()
        self.subs_check = QCheckBox(self.tr("Download subtitles (en/ar)"))
        self.meta_check = QCheckBox(self.tr("Embed metadata"))
        self.thumb_check = QCheckBox(self.tr("Embed thumbnail"))
        for cb in (self.subs_check, self.meta_check, self.thumb_check):
            extras_row.addWidget(cb)
        extras_row.addStretch(1)
        form.addRow(self.tr("Extras"), extras_row)

        self.thumb_label = QLabel(self.tr("Thumbnail preview: none"))
        # Design spec: 16:9 thumbnail preview, 160x90 minimum.
        self.thumb_label.setMinimumSize(160, 90)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setObjectName("ThumbPreview")
        self.thumb_label.setWordWrap(True)
        form.addRow(self.tr("Thumbnail"), self.thumb_label)

        self.preview_label = QLabel(
            self.tr("No preview yet — paste a video link and extract its details to see a preview.")
        )
        self.preview_label.setProperty("class", "Subtitle")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(self.tr("Preview"), self.preview_label)

        actions = QHBoxLayout()
        self.extract_btn = QPushButton(self.tr("Extract Metadata"))
        self.extract_btn.setProperty("class", "Primary")
        self.download_btn = QPushButton(self.tr("Download"))
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

    def _add_default_quality_items(self) -> None:
        """Reset the quality combo to the default presets (FEAT-01 incl. audio-only)."""
        self.format_combo.clear()
        self.format_combo.addItem(self.tr("Best available (recommended)"), "best")
        self.format_combo.addItem(self.tr("1080p (if available)"), "1080p")
        self.format_combo.addItem(self.tr("720p (if available)"), "720p")
        self.format_combo.addItem(self.tr("480p (if available)"), "480p")
        # FEAT-01: audio-only presets (converted with FFmpegExtractAudio).
        self.format_combo.addItem(self.tr("Audio only — MP3"), "audio_mp3")
        self.format_combo.addItem(self.tr("Audio only — M4A"), "audio_m4a")

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
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select download folder"), current)
        if folder:
            self.dest_input.setText(folder)

    def _on_extract(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(
                self,
                self.tr("Missing URL"),
                self.tr("Please enter a supported video or playlist URL."),
            )
            return
        from app.core.validators import is_http_url
        if not is_http_url(url):
            QMessageBox.warning(self, self.tr("Invalid URL"), self.tr("Please enter a valid http(s) URL."))
            return
        if not self.controller:
            QMessageBox.critical(
                self,
                self.tr("Unavailable"),
                self.tr("Metadata controller is not initialized."),
            )
            return
        self._last_video = None
        self._last_playlist = None
        self._set_thumbnail("", "")
        self.extract_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.preview_label.setText(self.tr("Extracting metadata..."))
        self.controller.extract_metadata(url)

    def on_metadata_result(self, payload: dict) -> None:
        video = (payload or {}).get("video")
        playlist = (payload or {}).get("playlist")
        self._last_video = video
        self._last_playlist = playlist
        # Reset quality options to defaults, then enrich for single video
        self._add_default_quality_items()
        if playlist:
            count = len(getattr(playlist, "entries", []) or [])
            thumb = getattr(playlist, "thumbnail_url", "") or ""
            self._set_thumbnail(thumb, getattr(playlist, "title", "Playlist"))
            playlist_text = (
                self.tr("Playlist detected: %s\nEntries: %d%s\nURL: %s\n\nOpen Playlists to review and select items.")
                % (
                    getattr(playlist, "title", "Playlist"),
                    count,
                    f"\n{self._thumb_availability(thumb)}",
                    getattr(playlist, "source_url", ""),
                )
            )
            self.preview_label.setText(playlist_text)
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
                    extra.append(
                        self.tr("Duration: %d:%02d:%02d") % (hrs, mins, secs)
                        if hrs else self.tr("Duration: %d:%02d") % (mins, secs)
                    )
                except Exception:
                    pass
            if uploader:
                extra.append(self.tr("Uploader: %s") % uploader)
            extra.append(self._thumb_availability(thumb))
            extra_text = ("\n" + "\n".join(extra)) if extra else ""
            self.preview_label.setText(
                self.tr("Title: %s\nURL: %s%s\nFormats found: %d\n"
                        "Quality selection uses sensible fallbacks when requested quality is unavailable.")
                % (getattr(video, "title", ""), getattr(video, "source_url", ""), extra_text, len(formats))
            )
            self.download_btn.setEnabled(True)
        else:
            self._set_thumbnail("", "")
            self.preview_label.setText(self.tr("No metadata could be extracted."))
            self.download_btn.setEnabled(False)

    def _thumb_availability(self, thumb) -> str:
        """Localized 'Thumbnail: available/not available' wording used in previews."""
        return self.tr("Thumbnail: available") if thumb else self.tr("Thumbnail: not available")

    def _on_download(self) -> None:
        url = self.url_input.text().strip()
        if not url or not self._last_video:
            QMessageBox.warning(self, self.tr("Not ready"), self.tr("Extract video metadata first."))
            return
        if not self.controller or not hasattr(self.controller, "start_download"):
            QMessageBox.critical(self, self.tr("Unavailable"), self.tr("Download controller is not available."))
            return
        output_dir = self.dest_input.text().strip()
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
        quality = self.format_combo.currentData() or "best"
        task_id = self.controller.start_download(
            url=self._last_video.source_url or url,
            output_dir=output_dir,
            quality=str(quality),
            title=getattr(self._last_video, "title", ""),
            thumbnail_url=getattr(self._last_video, "thumbnail_url", ""),
            embed_metadata=self.meta_check.isChecked(),
            embed_thumbnail=self.thumb_check.isChecked(),
            write_subs=self.subs_check.isChecked(),
        )
        queued_note = self.tr("Queued download task: %s") % task_id[:8]
        self.preview_label.setText(self.preview_label.text() + "\n\n" + queued_note)
        self.download_btn.setEnabled(False)

    def on_task_error(self, task_id: str, message: str) -> None:
        from app.ui.i18n import translate_known_error

        QMessageBox.critical(
            self,
            self.tr("Download Error"),
            translate_known_error(message) or self.tr("Download failed."),
        )

    def on_metadata_error(self, message: str) -> None:
        self.preview_label.setText(self.tr("Failed to extract metadata."))
        QMessageBox.critical(self, self.tr("Metadata Error"), message or self.tr("Unable to extract metadata."))

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
        self.thumb_label.setText(self.tr("Thumbnail preview: none"))
        if not url:
            return
        self.thumb_label.setText(self.tr("Thumbnail: available (loading preview...)"))
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QPixmap
            from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
        except Exception:
            self.thumb_label.setText(self.tr("Thumbnail: available (preview requires network-capable runtime)"))
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
                    self.thumb_label.setText(self.tr("Thumbnail: available (preview too large)"))
                    return
                pix = QPixmap()
                if pix.loadFromData(data):
                    scaled = pix.scaledToHeight(120, Qt.SmoothTransformation)
                    self.thumb_label.setPixmap(scaled)
                    self.thumb_label.setText("")
                else:
                    self.thumb_label.setText(self.tr("Thumbnail: available (could not render)"))
            except Exception:
                self.thumb_label.setText(self.tr("Thumbnail: available (could not render)"))
            finally:
                reply.deleteLater()

        reply.finished.connect(_done)

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if not self.dest_input.text().strip():
            self._apply_default_destination()
