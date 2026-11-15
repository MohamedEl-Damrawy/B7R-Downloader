"""Centralized UI color palettes (FEAT-08: dark + light themes)."""

from __future__ import annotations

from app.core import constants

PALETTE = {
    "main_bg": constants.COLOR_MAIN_BG,
    "sidebar": constants.COLOR_SIDEBAR,
    "card": constants.COLOR_CARD,
    "primary": constants.COLOR_PRIMARY_TEAL,
    "secondary": constants.COLOR_SECONDARY_BLUE,
    "deep_navy": constants.COLOR_DEEP_NAVY,
    "accent": constants.COLOR_ACCENT_RED,
    "text_main": constants.COLOR_TEXT_MAIN,
    "text_secondary": constants.COLOR_TEXT_SECONDARY,
}

# Light theme tokens: same keys, light-friendly values.
LIGHT_PALETTE = {
    "main_bg": "#F2F5F8",
    "sidebar": "#FFFFFF",
    "card": "#FFFFFF",
    "primary": "#1F7A78",
    "secondary": "#D8E6F2",
    "deep_navy": "#0F2438",
    "accent": "#C22545",
    "text_main": "#1B2430",
    "text_secondary": "#5B6B7C",
}

# Registered themes; "dark" stays the default for existing installs.
THEMES = {
    "dark": PALETTE,
    "light": LIGHT_PALETTE,
}


def palette_for_theme(theme: str) -> dict[str, str]:
    return THEMES.get(str(theme or "dark").strip().lower(), PALETTE)
