"""Settings service (DB-backed primary, JSON config as compatibility fallback)."""

from __future__ import annotations

from app.core.config import AppConfig
from app.core.constants import DEFAULT_SETTINGS, SETTINGS_DEFAULT_DOWNLOAD_PATH
from app.core.paths import get_default_download_dir
from app.database.repositories.settings_repo import SettingsRepository


class SettingsService:
    def __init__(self) -> None:
        self.file_config = AppConfig.load()
        self.repo = SettingsRepository()

    def get(self, key: str, default=None):
        val = self.repo.get(key)
        if val is not None:
            return val
        fallback = self.file_config.get(key, None)
        if fallback is not None:
            # Migrate legacy file-backed value into DB for consistency.
            try:
                self.repo.set(key, str(fallback))
            except Exception:
                pass
            return fallback
        if default is not None:
            return default
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]
        if key == SETTINGS_DEFAULT_DOWNLOAD_PATH:
            return str(get_default_download_dir())
        return None

    def set(self, key: str, value) -> None:
        sval = str(value)
        self.repo.set(key, sval)
        try:
            self.file_config.set(key, value)
            self.file_config.save()
        except Exception:
            # DB is the source of truth; file persistence is best-effort.
            pass
