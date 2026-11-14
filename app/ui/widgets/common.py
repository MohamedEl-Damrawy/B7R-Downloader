"""Reusable UI widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


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
        layout.setContentsMargins(16, 14, 16, 14)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "Subtitle")
        self.title_label.setStyleSheet("color: #91A2B5;")
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class EmptyState(CardFrame):
    def __init__(self, title: str, message: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignCenter)
        t = QLabel(title)
        t.setProperty("class", "Title")
        t.setAlignment(Qt.AlignCenter)
        m = QLabel(message)
        m.setWordWrap(True)
        m.setAlignment(Qt.AlignCenter)
        m.setStyleSheet("color: #91A2B5;")
        layout.addWidget(t)
        layout.addSpacing(6)
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
            sub.setStyleSheet("color: #91A2B5;")
            layout.addWidget(sub)
        layout.addStretch(0)
