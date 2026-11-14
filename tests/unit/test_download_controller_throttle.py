"""Unit tests for the DownloadController DB-write throttle (PERF-01)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QCoreApplication

from app.controllers.download_controller import DownloadController
from app.models.download import utc_now_iso
from app.models.download_status import DownloadStatus


class _FakeRepo:
    """In-memory stand-in for DownloadsRepository recording update_status calls."""

    def __init__(self) -> None:
        self.status_calls: list[dict[str, Any]] = []

    def update_status(self, download_id: str, status, **kwargs) -> None:
        self.status_calls.append({"id": download_id, "status": status, **kwargs})


def _make_controller(repo: _FakeRepo) -> DownloadController:
    QCoreApplication.instance() or QCoreApplication([])
    ctrl = DownloadController()
    ctrl.repo = repo
    ctrl.items_repo = SimpleNamespace(
        update_by_download_id=lambda *a, **k: None
    )
    return ctrl


class _MonotonicPatch:
    """Replace DownloadController module's time.monotonic with a controllable clock."""

    def __init__(self, module, start: float) -> None:
        self._module = module
        self._orig_time = module.time
        self.now = start
        module.time = SimpleNamespace(monotonic=lambda: self.now)

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def restore(self) -> None:
        self._module.time = self._orig_time


class TestStatusThrottle(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = _FakeRepo()
        self.ctrl = _make_controller(self.repo)
        import app.controllers.download_controller as mod

        self.mod = mod
        self.clock = _MonotonicPatch(mod, start=1000.0)
        self.addCleanup(self.clock.restore)
        self.addCleanup(self.ctrl.deleteLater)

    def test_progress_only_writes_are_throttled(self):
        # First call: no persisted status yet -> writes immediately.
        self.ctrl._update_status("t1", DownloadStatus.DOWNLOADING, progress=10.0)
        self.assertEqual(len(self.repo.status_calls), 1)

        # Nine rapid progress-only updates within the interval -> no extra writes.
        for i in range(9):
            self.clock.advance(0.05)  # total +0.45s < _DB_WRITE_INTERVAL_SEC (0.5)
            self.ctrl._update_status("t1", DownloadStatus.DOWNLOADING, progress=float(20 + i))
        self.assertEqual(len(self.repo.status_calls), 1)

        # One more update past the interval -> one throttled write.
        self.clock.advance(0.5)
        self.ctrl._update_status("t1", DownloadStatus.DOWNLOADING, progress=50.0)
        self.assertEqual(len(self.repo.status_calls), 2)

    def test_status_change_always_persists_even_within_interval(self):
        self.ctrl._update_status("t2", DownloadStatus.DOWNLOADING, progress=5.0)
        self.assertEqual(len(self.repo.status_calls), 1)

        # Immediately switch status (no time elapsed) -> still persists.
        self.clock.advance(0.01)
        self.ctrl._update_status("t2", DownloadStatus.PROCESSING, progress=100.0, completed=True)
        self.assertEqual(len(self.repo.status_calls), 2)
        self.assertEqual(self.repo.status_calls[-1]["status"], DownloadStatus.PROCESSING)

    def test_terminal_status_persists_with_timestamps(self):
        before = utc_now_iso()
        self.ctrl._update_status(
            "t3",
            DownloadStatus.COMPLETED,
            progress=100.0,
            completed=True,
            downloaded_bytes=1024,
            total_bytes=1024,
        )
        self.assertEqual(len(self.repo.status_calls), 1)
        call = self.repo.status_calls[0]
        self.assertEqual(call["status"], DownloadStatus.COMPLETED)
        self.assertEqual(call["completed_at"], before)
        self.assertEqual(call["downloaded_bytes"], 1024)

    def test_interval_constant_is_half_second(self):
        self.assertEqual(self.mod._DB_WRITE_INTERVAL_SEC, 0.5)

    def test_invalid_transition_is_flagged_but_applied(self):
        # State-machine enforcement (Phase 2): an invalid transition is logged
        # loudly, but still applied so a mis-classified edge cannot strand a
        # task in a stale status.
        self.ctrl._update_status("t4", DownloadStatus.COMPLETED, progress=100.0, completed=True)
        with self.assertLogs(self.mod.logger, level="ERROR") as logs:
            self.ctrl._update_status("t4", DownloadStatus.DOWNLOADING, progress=50.0)
        self.assertTrue(any("Invalid status transition" in m for m in logs.output))
        last = self.repo.status_calls[-1]
        self.assertEqual(last["status"], DownloadStatus.DOWNLOADING)

    def test_valid_transition_logs_no_error(self):
        self.ctrl._update_status("t5", DownloadStatus.EXTRACTING, progress=0.0)
        with self.assertNoLogs(level="ERROR"):
            self.ctrl._update_status("t5", DownloadStatus.DOWNLOADING, progress=10.0)


if __name__ == "__main__":
    unittest.main()
