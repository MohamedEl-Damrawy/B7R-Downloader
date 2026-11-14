"""Configuration loading and persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_SETTINGS, SETTINGS_DEFAULT_DOWNLOAD_PATH
from app.core.paths import get_app_data_dir, get_default_download_dir


@dataclass
class AppConfig:
    values: dict[str, str] = field(default_factory=dict)

    @property
    def config_path(self) -> Path:
        return get_app_data_dir() / "config.json"

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls(values=dict(DEFAULT_SETTINGS))
        if not cfg.values.get(SETTINGS_DEFAULT_DOWNLOAD_PATH):
            cfg.values[SETTINGS_DEFAULT_DOWNLOAD_PATH] = str(get_default_download_dir())
        path = cfg.config_path
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        cfg.values[str(k)] = str(v)
            except Exception:
                # Keep defaults on malformed config; caller may log.
                pass
        return cfg

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.values, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = str(value)
