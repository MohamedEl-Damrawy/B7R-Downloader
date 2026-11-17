"""GUI tests for the History page: multi-select deletion + clear-all."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _make_page(monkeypatch, tmp_path, rows):
    """HistoryPage with a fake repo; modal dialogs are stubbed offscreen."""
    _ensure_app()
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    from app.ui.pages.history import HistoryPage

    page = HistoryPage()
    page.repo = _FakeRepo(rows)
    return page


class _FakeRepo:
    def __init__(self, rows):
        self.rows = list(rows)
        self.deleted: list[str] = []
        self.all_deleted = False

    def list_recent(self, limit=200):
        return [r for r in self.rows if r["id"] not in self.deleted and not self.all_deleted]

    def delete_many(self, ids):
        self.deleted.extend(ids)
        return len(ids)

    def delete_all(self):
        self.all_deleted = True
        return 4


def _row(tid, title):
    return {"id": tid, "title": title, "source_url": "https://example.com/v", "status": "Completed", "output_path": ""}


def test_history_multiselect_delete_selected(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    page = _make_page(monkeypatch, tmp_path, [_row("a", "One"), _row("b", "Two"), _row("c", "Three")])
    qtbot.addWidget(page)
    page.show()
    page.refresh_data()
    assert page.list_widget.count() == 3
    assert page.list_widget.selectionMode() == page.list_widget.SelectionMode.ExtendedSelection

    # select first and third rows programmatically
    page.list_widget.setCurrentRow(0)
    page.list_widget.item(2).setSelected(True)
    assert len(page.list_widget.selectedItems()) == 2
    page._delete_selected()
    assert sorted(page.repo.deleted) == ["a", "c"]
    page.refresh_data()
    assert page.list_widget.count() == 1


def test_history_clear_all(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    page = _make_page(monkeypatch, tmp_path, [_row("a", "One"), _row("b", "Two")])
    qtbot.addWidget(page)
    page.show()
    page.refresh_data()
    assert page.clear_all_btn.isEnabled()
    page._clear_all()
    assert page.repo.all_deleted
    page.refresh_data()
    assert page.list_widget.count() == 0
    assert not page.clear_all_btn.isEnabled()
    assert page.empty.isVisible()
