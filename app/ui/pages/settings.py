"""Settings page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import (
    DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    MAX_CONCURRENT_DOWNLOADS,
    MIN_CONCURRENT_DOWNLOADS,
    SETTINGS_COOKIEFILE,
    SETTINGS_DEFAULT_DOWNLOAD_PATH,
    SETTINGS_MAX_CONCURRENT_DOWNLOADS,
    SETTINGS_PROXY,
    SETTINGS_SPONSORBLOCK,
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

        # DL-07/FEAT-04/05: optional credentials/network options.
        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText("Path to a Netscape-format cookies.txt (optional)")
        self.cookie_browse_btn = QPushButton("Browse")
        self.cookie_browse_btn.clicked.connect(self._browse_cookiefile)
        cookie_row = QHBoxLayout()
        cookie_row.addWidget(self.cookie_input, 1)
        cookie_row.addWidget(self.cookie_browse_btn)
        form.addRow("Cookies file", cookie_row)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("e.g. http://127.0.0.1:8080 (optional)")
        form.addRow("Proxy", self.proxy_input)

        # FEAT-03: SponsorBlock segment marking.
        self.sponsorblock_check = QCheckBox("Mark SponsorBlock segments (sponsor/intro/outro/...)")
        form.addRow("SponsorBlock", self.sponsorblock_check)

        info = QLabel(
            "About and third-party notices are available below. Release metadata may require owner confirmation."
        )
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
        self.update_check_btn = QPushButton("Check yt-dlp Updates")
        self.about_btn = QPushButton("About")
        self.licenses_btn = QPushButton("Licenses")
        actions.addWidget(self.save_btn)
        actions.addWidget(self.update_check_btn)
        actions.addWidget(self.about_btn)
        actions.addWidget(self.licenses_btn)
        actions.addStretch(1)
        form.addRow("", actions)

        layout.addWidget(card)
        layout.addStretch(1)

        self.save_btn.clicked.connect(self._save)
        self.update_check_btn.clicked.connect(self._check_ytdlp_update)
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
        self.cookie_input.setText(str(self.settings.get(SETTINGS_COOKIEFILE) or ""))
        self.proxy_input.setText(str(self.settings.get(SETTINGS_PROXY) or ""))
        self.sponsorblock_check.setChecked(str(self.settings.get(SETTINGS_SPONSORBLOCK, "0")).strip() == "1")
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

    def _browse_cookiefile(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Select cookies.txt (Netscape format)", "", "Cookie files (*.txt);;All files (*)"
        )
        if file:
            self.cookie_input.setText(file)

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
        self.settings.set(SETTINGS_COOKIEFILE, self.cookie_input.text().strip())
        self.settings.set(SETTINGS_PROXY, self.proxy_input.text().strip())
        self.settings.set(SETTINGS_SPONSORBLOCK, "1" if self.sponsorblock_check.isChecked() else "0")
        QMessageBox.information(self, "Settings", "Settings saved.")

    def _check_ytdlp_update(self) -> None:
        """DL-10/FEAT-07: compare installed yt-dlp with the latest PyPI release."""
        from PySide6.QtCore import QThread, Signal

        class _CheckThread(QThread):
            done = Signal(str)

            def run(self) -> None:
                from app.engine.ytdlp_engine import get_ytdlp_version, latest_pypi_version

                self.done.emit(f"{get_ytdlp_version()}|{latest_pypi_version() or ''}")

        self.update_check_btn.setEnabled(False)
        self.update_check_btn.setText("Checking...")

        def _finished(result: str) -> None:
            self.update_check_btn.setEnabled(True)
            self.update_check_btn.setText("Check yt-dlp Updates")
            cur, latest = (result or "").split("|", 1)
            if not latest:
                QMessageBox.warning(self, "yt-dlp Update", f"Could not reach PyPI.\nInstalled yt-dlp: {cur}")
            elif latest == cur:
                QMessageBox.information(self, "yt-dlp Update", f"yt-dlp is up to date ({cur}).")
            else:
                QMessageBox.information(
                    self,
                    "yt-dlp Update",
                    f"Installed yt-dlp: {cur}\nLatest release: {latest}\n\n"
                    "Update by upgrading the installed yt-dlp package (pip install -U yt-dlp), "
                    "then rebuild/repackage the app.",
                )

        self._update_thread = _CheckThread()
        self._update_thread.done.connect(_finished)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.start()
