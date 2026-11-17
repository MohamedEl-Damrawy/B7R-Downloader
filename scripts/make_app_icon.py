"""Generate resources/icons/app.ico (multi-size) from app_icon.svg.

Run: python scripts/make_app_icon.py
Requires: PySide6 (offscreen SVG rendering) + Pillow (ICO assembly).
"""
from __future__ import annotations

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_png(svg_path: str, size: int) -> QImage:
    svg = open(svg_path, encoding="utf-8").read()
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    assert renderer.isValid(), f"invalid SVG: {svg_path}"
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def main() -> None:
    from PIL import Image

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    svg_path = os.path.join(root, "resources", "icons", "app_icon.svg")
    ico_path = os.path.join(root, "resources", "icons", "app.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = []
    for s in sizes:
        img = render_png(svg_path, s)
        tmp = os.path.join(os.environ.get("TEMP", "."), f"velo_icon_{s}.png")
        img.save(tmp)
        frames.append(Image.open(tmp))
    # Largest frame as the base so the ICO plugin can downscale to all sizes.
    base = frames[-1]
    base.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"wrote {ico_path}")


if __name__ == "__main__":
    main()
