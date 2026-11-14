"""Settings page."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget

from app.core.constants import (
    DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    MAX_CONCURRENT_DOWNLOADS,
    MIN_CONCURRENT_DOWNLOADS,
    SETTINGS_DEFAULT_DOWNLOAD_PATH,
    SETTINGS_MAX_CONCURRENT_DOWNLOADS,
)
from app.core.paths import get_default_download_dir
from app.services.settings_service import SettingsService
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.licenses_dialog import LicensesDialog
from app.ui.widgets.common import CardFrame, PageHeader


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = SettingsService()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(PageHeader("Settings", "Configure defaults, concurrency, and application information"))

        card = CardFrame()
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self._browse_path)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(self.browse_btn)
        form.addRow("Default download path", path_row)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(MIN_CONCURRENT_DOWNLOADS, MAX_CONCURRENT_DOWNLOADS)
        form.addRow("Max concurrent downloads", self.concurrent_spin)

        info = QLabel("About and third-party notices are available below. Release metadata may require owner confirmation.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #91A2B5;")
        form.addRow("Legal", info)

        self.ffmpeg_label = QLabel()
        self.ffmpeg_label.setWordWrap(True)
        self.ffmpeg_label.setStyleSheet("color: #91A2B5;")
        form.addRow("FFmpeg", self.ffmpeg_label)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setProperty("class", "Primary")
        self.about_btn = QPushButton("About")
        self.licenses_btn = QPushButton("Licenses")
        actions.addWidget(self.save_btn)
        actions.addWidget(self.about_btn)
        actions.addWidget(self.licenses_btn)
        actions.addStretch(1)
        form.addRow("", actions)

        layout.addWidget(card)
        layout.addStretch(1)

        self.save_btn.clicked.connect(self._save)
        self.about_btn.clicked.connect(lambda: AboutDialog(self).exec())
        self.licenses_btn.clicked.connect(lambda: LicensesDialog(self).exec())
        self._load()

    def _load(self) -> None:
        self.settings = SettingsService()
        path = self.settings.get(SETTINGS_DEFAULT_DOWNLOAD_PATH) or str(get_default_download_dir())
        self.path_input.setText(str(path))
        try:
            mc = int(self.settings.get(SETTINGS_MAX_CONCURRENT_DOWNLOADS, DEFAULT_MAX_CONCURRENT_DOWNLOADS))
        except Exception:
            mc = DEFAULT_MAX_CONCURRENT_DOWNLOADS
        self.concurrent_spin.setValue(max(MIN_CONCURRENT_DOWNLOADS, min(MAX_CONCURRENT_DOWNLOADS, mc)))
        self._refresh_ffmpeg_status()

    def _refresh_ffmpeg_status(self) -> None:
        try:
            from app.engine.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
            ff = get_ffmpeg_path()
            fp = get_ffprobe_path()
            if ff and fp:
                self.ffmpeg_label.setText(f"Detected: ffmpeg ({ff}) | ffprobe ({fp})")
            elif ff or fp:
                self.ffmpeg_label.setText("Partial detection: ensure both ffmpeg and ffprobe are bundled/available.")
            else:
                self.ffmpeg_label.setText("Not detected. Bundle FFmpeg/FFprobe in vendor/ffmpeg for packaged builds.")
        except Exception:
            self.ffmpeg_label.setText("Status unavailable.")

    def _browse_path(self) -> None:
        current = self.path_input.text().strip() or str(get_default_download_dir())
        folder = QFileDialog.getExistingDirectory(self, "Select default download folder", current)
        if folder:
            self.path_input.setText(folder)

    def _save(self) -> None:
        path = self.path_input.text().strip() or str(get_default_download_dir())
        try:
            import os
            os.makedirs(path, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid folder", f"Cannot use download folder:\n{exc}")
            return
        self.settings.set(SETTINGS_DEFAULT_DOWNLOAD_PATH, path)
        self.settings.set(SETTINGS_MAX_CONCURRENT_DOWNLOADS, str(self.concurrent_spin.value()))
        QMessageBox.information(self, "Settings", "Settings saved.")