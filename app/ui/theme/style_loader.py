"""Load Qt stylesheets and apply theme + typography tokens."""

from __future__ import annotations

from app.core.paths import get_resources_dir
from app.ui.theme.palette import palette_for_theme


def _font_tokens(lang: str = "") -> dict[str, str]:
    """Typography tokens per language (Tajawal only for Arabic RTL)."""
    if lang.strip().lower() == "ar":
        return {"font_family": "Tajawal", "font_size": "14px"}
    return {"font_family": '"Segoe UI", "Inter", sans-serif', "font_size": "13px"}


def _replace_tokens(qss: str, palette: dict[str, str]) -> str:
    out = qss
    for key, value in palette.items():
        out = out.replace(f"@{key}@", value)
    return out


def load_theme_qss(theme: str = "dark", lang: str = "") -> str:
    """Load the QSS file for a theme ("dark"/"light") with tokens replaced."""
    name = "light.qss" if str(theme or "dark").strip().lower() == "light" else "dark.qss"
    path = get_resources_dir() / "styles" / name
    if not path.exists():
        return ""
    tokens = {**palette_for_theme(theme), **_font_tokens(lang)}
    return _replace_tokens(path.read_text(encoding="utf-8"), tokens)


def load_dark_qss() -> str:
    """Backwards-compatible alias for the default (dark, English) theme."""
    return load_theme_qss("dark")
