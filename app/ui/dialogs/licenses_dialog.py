"""Licenses and legal notices dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout

from app.core.paths import get_licenses_dir, get_resources_dir


def _read_if_exists(path: Path) -> str | None:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


class LicensesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Licenses & Legal Notices"))
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Third-party notices and legal information (draft until audited).")))
        text = QPlainTextEdit()
        text.setReadOnly(True)

        parts = []
        notices = _read_if_exists(get_licenses_dir() / "THIRD_PARTY_NOTICES.txt")
        parts.append(notices or "THIRD_PARTY_NOTICES.txt: pending audit.\n")
        privacy = _read_if_exists(get_resources_dir() / "legal" / "privacy_notice.txt")
        if privacy:
            parts.append("\n--- Privacy Information ---\n" + privacy)
        usage = _read_if_exists(get_resources_dir() / "legal" / "usage_notice.txt")
        if usage:
            parts.append("\n--- Usage Notice ---\n" + usage)
        text.setPlainText("\n".join(parts))
        layout.addWidget(text)
