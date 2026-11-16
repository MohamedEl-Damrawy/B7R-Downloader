"""Settings page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    SETTINGS_LANGUAGE,
    SETTINGS_MAX_CONCURRENT_DOWNLOADS,
    SETTINGS_PROXY,
    SETTINGS_SPONSORBLOCK,
    SETTINGS_THEME,
)
from app.core.paths import get_default_download_dir
from app.services.settings_service import SettingsService
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.licenses_dialog import LicensesDialog
from app.ui.widgets.common import CardFrame, PageHeader


class _YtdlpCheckThread:
    """PySide6 QThread subclass created lazily to keep module import Qt-light."""

    @staticmethod
    def make() -> "object":
        from PySide6.QtCore import QThread, Signal

        class _Thread(QThread):
            done = Signal(str)

            def run(self) -> None:
                from app.engine.ytdlp_engine import get_ytdlp_version, latest_pypi_version

                self.done.emit(f"{get_ytdlp_version()}|{latest_pypi_version() or ''}")

        return _Thread()


class _AppCheckThread:
    """Background thread for the app self-update check (GitHub Releases)."""

    @staticmethod
    def make() -> "object":
        from PySide6.QtCore import QThread, Signal

        class _Thread(QThread):
            done = Signal(str)

            def run(self) -> None:
                from app.services.app_update_service import check_for_app_update

                r = check_for_app_update()
                self.done.emit(f"{r['status']}|{r['latest']}|{r['url']}")

        return _Thread()


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = SettingsService()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(
            PageHeader(self.tr("Settings"), self.tr("Configure defaults, concurrency, and application information"))
        )

        card = CardFrame()
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.browse_btn = QPushButton(self.tr("Browse"))
        self.browse_btn.clicked.connect(self._browse_path)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(self.browse_btn)
        form.addRow(self.tr("Default download path"), path_row)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(MIN_CONCURRENT_DOWNLOADS, MAX_CONCURRENT_DOWNLOADS)
        form.addRow(self.tr("Max concurrent downloads"), self.concurrent_spin)

        # DL-07/FEAT-04/05: optional credentials/network options.
        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText(self.tr("Path to a Netscape-format cookies.txt (optional)"))
        self.cookie_browse_btn = QPushButton(self.tr("Browse"))
        self.cookie_browse_btn.clicked.connect(self._browse_cookiefile)
        cookie_row = QHBoxLayout()
        cookie_row.addWidget(self.cookie_input, 1)
        cookie_row.addWidget(self.cookie_browse_btn)
        form.addRow(self.tr("Cookies file"), cookie_row)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText(self.tr("e.g. http://127.0.0.1:8080 (optional)"))
        form.addRow(self.tr("Proxy"), self.proxy_input)

        # FEAT-03: SponsorBlock segment marking.
        self.sponsorblock_check = QCheckBox(self.tr("Mark SponsorBlock segments (sponsor/intro/outro/...)"))
        form.addRow(self.tr("SponsorBlock"), self.sponsorblock_check)

        # FEAT-08: theme selection (applied on next launch).
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.tr("Dark"), "dark")
        self.theme_combo.addItem(self.tr("Light"), "light")
        self.theme_hint = QLabel(self.tr("Applies after restarting the app."))
        self.theme_hint.setStyleSheet("color: #91A2B5; font-size: 11px;")
        theme_row = QHBoxLayout()
        theme_row.addWidget(self.theme_combo, 0)
        theme_row.addWidget(self.theme_hint, 1)
        form.addRow(self.tr("Theme"), theme_row)

        # i18n: language selection (applied on next launch).
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("العربية (Arabic)", "ar")
        self.language_hint = QLabel(self.tr("Applies after restarting the app."))
        self.language_hint.setStyleSheet("color: #91A2B5; font-size: 11px;")
        language_row = QHBoxLayout()
        language_row.addWidget(self.language_combo, 0)
        language_row.addWidget(self.language_hint, 1)
        form.addRow(self.tr("Language"), language_row)

        info = QLabel(
            self.tr(
                "About and third-party notices are available below. "
                "Release metadata may require owner confirmation."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #91A2B5;")
        form.addRow(self.tr("Legal"), info)

        self.ffmpeg_label = QLabel()
        self.ffmpeg_label.setWordWrap(True)
        self.ffmpeg_label.setStyleSheet("color: #91A2B5;")
        form.addRow(self.tr("FFmpeg"), self.ffmpeg_label)

        actions = QHBoxLayout()
        self.save_btn = QPushButton(self.tr("Save Settings"))
        self.save_btn.setProperty("class", "Primary")
        self.app_update_btn = QPushButton(self.tr("Check App Updates"))
        self.update_check_btn = QPushButton(self.tr("Check yt-dlp Updates"))
        self.about_btn = QPushButton(self.tr("About"))
        self.licenses_btn = QPushButton(self.tr("Licenses"))
        actions.addWidget(self.save_btn)
        actions.addWidget(self.app_update_btn)
        actions.addWidget(self.update_check_btn)
        actions.addWidget(self.about_btn)
        actions.addWidget(self.licenses_btn)
        actions.addStretch(1)
        form.addRow("", actions)

        layout.addWidget(card)
        layout.addStretch(1)

        self.save_btn.clicked.connect(self._save)
        self.app_update_btn.clicked.connect(self._check_app_update)
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
        theme = str(self.settings.get(SETTINGS_THEME, "dark") or "dark").strip().lower()
        idx = self.theme_combo.findData(theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        language = str(self.settings.get(SETTINGS_LANGUAGE, "en") or "en").strip().lower()
        idx = self.language_combo.findData(language)
        self.language_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._refresh_ffmpeg_status()

    def _refresh_ffmpeg_status(self) -> None:
        try:
            from app.engine.ffmpeg_manager import get_ffmpeg_path, get_ffprobe_path
            ff = get_ffmpeg_path()
            fp = get_ffprobe_path()
            if ff and fp:
                self.ffmpeg_label.setText(
                    self.tr("Detected: ffmpeg (%s) | ffprobe (%s)") % (ff, fp)
                )
            elif ff or fp:
                self.ffmpeg_label.setText(
                    self.tr("Partial detection: ensure both ffmpeg and ffprobe are bundled/available.")
                )
            else:
                self.ffmpeg_label.setText(
                    self.tr("Not detected. Bundle FFmpeg/FFprobe in vendor/ffmpeg for packaged builds.")
                )
        except Exception:
            self.ffmpeg_label.setText(self.tr("Status unavailable."))

    def _browse_path(self) -> None:
        current = self.path_input.text().strip() or str(get_default_download_dir())
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select default download folder"), current)
        if folder:
            self.path_input.setText(folder)

    def _browse_cookiefile(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select cookies.txt (Netscape format)"), "", "Cookie files (*.txt);;All files (*)"
        )
        if file:
            self.cookie_input.setText(file)

    def _save(self) -> None:
        path = self.path_input.text().strip() or str(get_default_download_dir())
        try:
            import os
            os.makedirs(path, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Invalid folder"), self.tr("Cannot use download folder:\n%s") % exc)
            return
        self.settings.set(SETTINGS_DEFAULT_DOWNLOAD_PATH, path)
        self.settings.set(SETTINGS_MAX_CONCURRENT_DOWNLOADS, str(self.concurrent_spin.value()))
        self.settings.set(SETTINGS_COOKIEFILE, self.cookie_input.text().strip())
        self.settings.set(SETTINGS_PROXY, self.proxy_input.text().strip())
        self.settings.set(SETTINGS_SPONSORBLOCK, "1" if self.sponsorblock_check.isChecked() else "0")
        self.settings.set(SETTINGS_THEME, self.theme_combo.currentData() or "dark")
        self.settings.set(SETTINGS_LANGUAGE, self.language_combo.currentData() or "en")
        QMessageBox.information(
            self,
            self.tr("Settings"),
            self.tr("Settings saved. Theme and language changes apply after restart."),
        )

    def _check_ytdlp_update(self) -> None:
        """DL-10/FEAT-07: compare installed yt-dlp with the latest PyPI release."""
        self.update_check_btn.setEnabled(False)
        self.update_check_btn.setText(self.tr("Checking..."))

        def _finished(result: str) -> None:
            self.update_check_btn.setEnabled(True)
            self.update_check_btn.setText(self.tr("Check yt-dlp Updates"))
            cur, latest = (result or "").split("|", 1)
            if not latest:
                QMessageBox.warning(
                    self,
                    self.tr("yt-dlp Update"),
                    self.tr("Could not reach PyPI.\nInstalled yt-dlp: %s") % cur,
                )
            elif latest == cur:
                QMessageBox.information(self, self.tr("yt-dlp Update"), self.tr("yt-dlp is up to date (%s).") % cur)
            else:
                QMessageBox.information(
                    self,
                    self.tr("yt-dlp Update"),
                    self.tr("Installed yt-dlp: %s\nLatest release: %s\n\n"
                            "Update by upgrading the installed yt-dlp package (pip install -U yt-dlp), "
                            "then rebuild/repackage the app.") % (cur, latest),
                )

        self._update_thread = _YtdlpCheckThread.make()
        self._update_thread.done.connect(_finished)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.start()

    def _check_app_update(self) -> None:
        """App self-update check against the project's GitHub Releases."""
        from app.core.constants import APP_REPO_URL, APP_VERSION

        self.app_update_btn.setEnabled(False)
        self.app_update_btn.setText(self.tr("Checking..."))

        def _finished(result: str) -> None:
            self.app_update_btn.setEnabled(True)
            self.app_update_btn.setText(self.tr("Check App Updates"))
            status, latest, url = (result or "unreachable||").split("|", 2)
            url = url or APP_REPO_URL
            if status == "update_available":
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle(self.tr("App Update"))
                box.setText(self.tr("A new version is available.\nInstalled: %s\nLatest: %s") % (APP_VERSION, latest))
                open_btn = box.addButton(self.tr("Open Releases Page"), QMessageBox.AcceptRole)
                box.addButton(QMessageBox.Close)
                box.exec()
                if box.clickedButton() is open_btn:
                    from PySide6.QtCore import QUrl
                    from PySide6.QtGui import QDesktopServices

                    QDesktopServices.openUrl(QUrl(url))
            elif status == "up_to_date":
                QMessageBox.information(
                    self,
                    self.tr("App Update"),
                    self.tr("The app is up to date (version %s).") % APP_VERSION,
                )
            elif status == "no_releases":
                no_releases_msg = self.tr(
                    "No published releases yet (installed: %s).\n"
                    "Check the project's GitHub page for new versions:\n%s"
                )
                QMessageBox.information(self, self.tr("App Update"), no_releases_msg % (APP_VERSION, url))
            else:
                QMessageBox.warning(
                    self,
                    self.tr("App Update"),
                    self.tr("Could not reach GitHub.\nInstalled: %s") % APP_VERSION,
                )

        self._app_update_thread = _AppCheckThread.make()
        self._app_update_thread.done.connect(_finished)
        self._app_update_thread.finished.connect(self._app_update_thread.deleteLater)
        self._app_update_thread.start()
