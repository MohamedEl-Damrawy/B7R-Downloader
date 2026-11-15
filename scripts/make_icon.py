"""Generate the application icon (FEAT-14): resources/icons/app.ico (+ .png).

Run: python scripts/make_icon.py
Paints offscreen with PySide6 — no network, no display needed.
"""

from __future__ import annotations

import os
import sys

# Must run offscreen before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.paths import get_resources_dir  # noqa: E402

SIZE = 256


def paint_icon(size: int = SIZE) -> QPixmap:
    """Rounded-square teal gradient tile with a stylized "V" and a download arrow."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    m = size * 0.06
    rect = QRectF(m, m, size - 2 * m, size - 2 * m)
    radius = size * 0.20

    # Background: deep navy -> teal gradient (matches dark theme palette).
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#132440"))
    grad.setColorAt(1.0, QColor("#2FA0A0"))
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.fillPath(path, grad)
    p.setPen(QPen(QColor("#3B9797"), size * 0.012))
    p.drawPath(path)

    # Stylized "V" built from two strokes with rounded caps.
    stroke = size * 0.075
    pen = QPen(QColor("#F4F7FA"), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    cx = size / 2
    top = size * 0.30
    mid = size * 0.55
    left_x = size * 0.34
    right_x = size * 0.66
    v_path = QPainterPath()
    v_path.moveTo(left_x, top)
    v_path.lineTo(cx, mid)
    v_path.lineTo(right_x, top)
    p.drawPath(v_path)

    # Download arrow beneath the V.
    p.drawLine(cx, size * 0.62, cx, size * 0.78)
    aw = size * 0.05
    p.drawLine(cx, size * 0.78, cx - aw, size * 0.71)
    p.drawLine(cx, size * 0.78, cx + aw, size * 0.71)
    p.drawLine(cx - size * 0.10, size * 0.84, cx + size * 0.10, size * 0.84)

    p.end()
    return pm


def main() -> int:
    QApplication.instance() or QApplication([])  # ensure QGuiApplication is up for image formats
    icons_dir = get_resources_dir() / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    ico_path = icons_dir / "app.ico"
    png_path = icons_dir / "app.png"

    pm = paint_icon()
    ok_png = pm.save(str(png_path), "PNG")
    icon = QIcon(pm)
    ok_ico = icon.pixmap(256, 256).save(str(ico_path), "ICO")
    print(f"PNG: {png_path} ({'ok' if ok_png else 'FAILED'})")
    print(f"ICO: {ico_path} ({'ok' if ok_ico else 'FAILED'})")
    return 0 if (ok_png and ok_ico) else 1


if __name__ == "__main__":
    raise SystemExit(main())
