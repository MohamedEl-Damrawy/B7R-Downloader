"""Load Qt stylesheets and apply theme tokens."""

from __future__ import annotations

from app.core.paths import get_resources_dir
from app.ui.theme.palette import palette_for_theme


def _replace_tokens(qss: str, palette: dict[str, str]) -> str:
    out = qss
    for key, value in palette.items():
        out = out.replace(f"@{key}@", value)
    return out


def load_theme_qss(theme: str = "dark") -> str:
    """Load the QSS file for a theme ("dark"/"light") with tokens replaced."""
    name = "light.qss" if str(theme or "dark").strip().lower() == "light" else "dark.qss"
    path = get_resources_dir() / "styles" / name
    if path.exists():
        return _replace_tokens(path.read_text(encoding="utf-8"), palette_for_theme(theme))
    return ""


def load_dark_qss() -> str:
    """Backwards-compatible alias for the default (dark) theme."""
    return load_theme_qss("dark")
