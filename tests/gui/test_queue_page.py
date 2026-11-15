"""GUI test for the per-item progress rows on the Queue page (FEAT-12)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_queue_rows_show_progress_bars(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    from PySide6.QtWidgets import QProgressBar

    from app.ui.pages.queue import QueuePage

    page = QueuePage()
    qtbot.addWidget(page)
    page.show()

    page.upsert_task(
        {
            "id": "t1",
            "title": "Test Video",
            "status": "Downloading",
            "progress": 45.0,
            "downloaded_bytes": 450 * 1024 * 1024,
            "total_bytes": 1024 * 1024 * 1024,
            "speed": 2.5 * 1024 * 1024,
            "eta": 90,
        }
    )
    assert page.list_widget.count() == 1
    item = page.list_widget.item(0)
    row = page.list_widget.itemWidget(item)
    assert row is not None
    bars = row.findChildren(QProgressBar)
    assert len(bars) == 1
    assert bars[0].value() == 450  # 45.0% * 10 on a 0..1000 range
    assert "450.0/1024.0 MB" in row.info_label.text()
    assert "ETA 1m 30s" in row.info_label.text()

    # Update the same task id: row is reused, not duplicated.
    page.upsert_task({"id": "t1", "status": "Completed", "progress": 100.0})
    assert page.list_widget.count() == 1
    assert bars[0].value() == 1000

    # Clear finished removes it.
    page._clear_finished()
    assert page.list_widget.count() == 0
