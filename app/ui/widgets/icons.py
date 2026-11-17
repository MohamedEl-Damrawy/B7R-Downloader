"""Shared SVG icon rendering (Lucide outline family).

All icons live in resources/icons/nav as editable 24x24 SVGs (2px stroke,
round caps/joins, no fill). Nav icons use the #STROKE placeholder so one
file serves both the muted and active states; empty-state icons reuse the
same mechanism at larger sizes.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer  # noqa: F401  (ensures PyInstaller bundling)

from app.core.paths import get_resources_dir

ICON_DIR = "nav"
ICON_SIZE = 20  # nav row rendered size (px)
ICON_LABEL_GAP = 12
ROW_HEIGHT = 44


def resolve_theme() -> str:
    """Same resolution rule as application.run (FEAT-08)."""
    try:
        from app.core.constants import SETTINGS_THEME
        from app.services.settings_service import SettingsService

        value = str(SettingsService().get(SETTINGS_THEME, "dark") or "dark").strip().lower()
        return value if value in ("dark", "light") else "dark"
    except Exception:
        return "dark"


def theme_colors() -> tuple[str, str]:
    """(muted, active) icon/label colors from the active theme palette."""
    from app.ui.theme.palette import palette_for_theme

    palette = palette_for_theme(resolve_theme())
    return palette.get("text_secondary", "#AAB8B8"), palette.get("primary", "#24A99A")


def render_svg_file_pixmap(svg_path, size: int, dpr: float = 1.0) -> QPixmap | None:
    """Render an arbitrary bundled SVG file (own colors, no placeholder) at
    `size` px as a transparent QPixmap; None on failure."""
    try:
        renderer = QSvgRenderer(QByteArray(svg_path.read_text(encoding="utf-8").encode("utf-8")))
        if not renderer.isValid():
            return None
        pm = QPixmap(int(size * dpr), int(size * dpr))
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        renderer.render(painter, QRectF(0, 0, size * dpr, size * dpr))
        painter.end()
        pm.setDevicePixelRatio(dpr)
        return pm
    except Exception:
        return None


def render_svg_icon(key: str, color: str, size: int = ICON_SIZE, dpr: float = 1.0) -> QIcon | None:
    """Render a bundled Lucide SVG in the given stroke color as a QIcon.

    Returns None when unavailable (missing file / QtSvg failure) so callers
    can fall back gracefully.
    """
    path = get_resources_dir() / "icons" / ICON_DIR / f"{key}.svg"
    if not path.exists():
        return None
    try:
        svg = path.read_text(encoding="utf-8").replace("#STROKE", QColor(color).name())
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            return None
        pm = QPixmap(int(size * dpr), int(size * dpr))
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        renderer.render(painter, QRectF(0, 0, size * dpr, size * dpr))
        painter.end()
        pm.setDevicePixelRatio(dpr)
        return QIcon(pm)
    except Exception:
        return None
