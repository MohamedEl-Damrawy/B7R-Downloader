"""Centralized UI color palettes (FEAT-08: dark + light themes)."""

from __future__ import annotations

from app.core import constants

# Design-spec palette (UI/UX redesign): calm premium utility aesthetic.
# Core tokens + semantic tokens; values differ per theme.
PALETTE = {
    "main_bg": constants.COLOR_MAIN_BG,
    "sidebar": constants.COLOR_SIDEBAR,
    "card": constants.COLOR_CARD,
    "primary": constants.COLOR_PRIMARY_TEAL,
    "secondary": constants.COLOR_SECONDARY_BLUE,
    "accent": constants.COLOR_ACCENT_RED,
    "text_main": constants.COLOR_TEXT_MAIN,
    "text_secondary": constants.COLOR_TEXT_SECONDARY,
    # Semantic tokens
    "border": "#30404A",
    "border_strong": "#465963",
    "surface_muted": "#202D37",
    "surface_selected": "#203C3C",
    "text_disabled": "#718087",
    "control_disabled": "#202A32",
    "focus": "#75D6C7",
    "success": "#65C49A",
    "warning": "#E7B86B",
    "error": "#E27B78",
    "on_primary": "#071D1B",
}

# Light theme tokens: same keys, light-friendly values.
LIGHT_PALETTE = {
    "main_bg": "#F4F3EF",
    "sidebar": "#ECEBE6",
    "card": "#FFFFFF",
    "primary": "#087F76",
    "secondary": "#E6E8E5",
    "accent": "#087F76",
    "text_main": "#202B2A",
    "text_secondary": "#5F6B68",
    "border": "#D9DDD8",
    "border_strong": "#BBC4BF",
    "surface_muted": "#F0F1ED",
    "surface_selected": "#E1F2EF",
    "text_disabled": "#929B96",
    "control_disabled": "#E9EAE6",
    "focus": "#087F76",
    "success": "#23784E",
    "warning": "#94600D",
    "error": "#B83D3A",
    "on_primary": "#FFFFFF",
}

# Registered themes; "dark" stays the default for existing installs.
THEMES = {
    "dark": PALETTE,
    "light": LIGHT_PALETTE,
}


def palette_for_theme(theme: str) -> dict[str, str]:
    return THEMES.get(str(theme or "dark").strip().lower(), PALETTE)
