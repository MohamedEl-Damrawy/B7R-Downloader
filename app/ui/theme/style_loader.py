"""Load Qt stylesheets and apply theme tokens."""

from __future__ import annotations

from pathlib import Path

from app.core.paths import get_resources_dir
from app.ui.theme.palette import PALETTE


def _replace_tokens(qss: str) -> str:
    out = qss
    for key, value in PALETTE.items():
        out = out.replace(f"@{key}@", value)
    return out


def load_dark_qss() -> str:
    path = get_resources_dir() / "styles" / "dark.qss"
    if path.exists():
        return _replace_tokens(path.read_text(encoding="utf-8"))
    return ""
