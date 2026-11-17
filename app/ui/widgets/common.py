"""Reusable UI widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class CardFrame(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("class", "Card")
        self.setFrameShape(QFrame.StyledPanel)


class StatCard(CardFrame):
    def __init__(self, title: str, value: str = "0", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # Card padding per design spec (20px); 8px rhythm.
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")  # size/weight via QSS
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "Subtitle")
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class EmptyState(CardFrame):
    """Centered empty-state card (design spec section G).

    icon: key of a bundled Lucide SVG (resources/icons/nav/<key>.svg),
    rendered 40px in the theme's muted tone; omit for text-only.
    """

    def __init__(self, title: str, message: str, icon: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("EmptyCard")  # 12px radius + 28px padding via QSS
        # Spec G: compact card (360-480px wide, >=176px tall), centered in the
        # content region — pages align it, never stretch it full-bleed.
        self.setMinimumHeight(176)
        self.setMaximumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        if icon:
            try:
                from app.ui.widgets.icons import render_svg_icon, theme_colors

                muted, _ = theme_colors()
                ic = QLabel()
                ic.setObjectName("EmptyIcon")
                ic.setAlignment(Qt.AlignCenter)
                ic.setFixedSize(40, 40)
                pixmap_icon = render_svg_icon(icon, muted, size=40, dpr=self.devicePixelRatioF() or 1.0)
                if pixmap_icon is not None:
                    ic.setPixmap(pixmap_icon.pixmap(40, 40))
                    layout.addWidget(ic, 0, Qt.AlignHCenter)
                    layout.addSpacing(8)
            except Exception:
                pass
        t = QLabel(title)
        t.setProperty("class", "EmptyTitle")
        t.setAlignment(Qt.AlignCenter)
        layout.addWidget(t)
        layout.addSpacing(6)
        m = QLabel(message)
        m.setWordWrap(True)
        m.setAlignment(Qt.AlignCenter)
        m.setProperty("class", "Subtitle")
        m.setMaximumWidth(440)
        layout.addWidget(m)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setProperty("class", "Title")
        layout.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setProperty("class", "Subtitle")
            layout.addWidget(sub)
        layout.addStretch(0)
