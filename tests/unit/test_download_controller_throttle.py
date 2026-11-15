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
        self.records: list[dict[str, Any]] = []

    def update_status(self, download_id: str, status, **kwargs) -> None:
        self.status_calls.append({"id": download_id, "status": status, **kwargs})

    def upsert(self, record: dict[str, Any]) -> None:
        self.records.append(record)


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


class _FakeSettings:
    """SettingsService stand-in for enqueue-time option resolution."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values or {}

    def get(self, key: str, default=None):
        return self.values.get(key, default)


class TestDiskPrecheck(unittest.TestCase):
    """FEAT-06: enqueue is refused when the destination drive is nearly full."""

    def setUp(self) -> None:
        import tempfile

        import app.controllers.download_controller as mod

        self.mod = mod
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = _FakeRepo()
        self.ctrl = _make_controller(self.repo)
        self.ctrl.items_repo = SimpleNamespace(link_download=lambda *a, **k: None)
        # Prevent real worker threads from starting during enqueue tests.
        self.ctrl._start_worker = lambda task_id, spec: None  # type: ignore[method-assign]
        self._orig_settings_cls = self.mod.SettingsService
        self.mod.SettingsService = lambda: _FakeSettings({})  # type: ignore[assignment]
        self.addCleanup(setattr, self.mod, "SettingsService", self._orig_settings_cls)

    def _patch_disk(self, free_bytes: int) -> None:
        usage = SimpleNamespace(total=10**12, used=0, free=free_bytes)
        self._orig_shutil = self.mod.shutil
        self.mod.shutil = SimpleNamespace(disk_usage=lambda _p: usage)  # type: ignore[assignment]
        self.addCleanup(setattr, self.mod, "shutil", self._orig_shutil)

    def test_low_disk_space_fails_task_immediately(self):
        self._patch_disk(free_bytes=50 * 1024 * 1024)  # below MIN_FREE_SPACE_BYTES (100MB)
        task_id = self.ctrl.start_download(
            url="https://example.com/watch?v=1", output_dir=self.tmpdir.name, quality="best"
        )
        self.assertTrue(task_id)
        last = self.repo.status_calls[-1]
        self.assertEqual(last["status"], DownloadStatus.FAILED)
        self.assertIn("disk space", str(last["error_message"]).lower())
        # The task was never persisted as QUEUED nor enqueued.
        self.assertEqual(self.repo.records, [])

    def test_sufficient_space_enqueues(self):
        self._patch_disk(free_bytes=10 * 1024 * 1024 * 1024)
        task_id = self.ctrl.start_download(
            url="https://example.com/watch?v=1", output_dir=self.tmpdir.name, quality="audio_mp3",
            embed_metadata=True, embed_thumbnail=True, write_subs=True,
        )
        self.assertTrue(task_id)
        spec = self.ctrl._specs[task_id]
        self.assertEqual(spec["audio_format"], "mp3")
        self.assertTrue(spec["embed_metadata"])
        self.assertTrue(spec["embed_thumbnail"])
        self.assertTrue(spec["write_subs"])
        self.assertEqual(spec["format_selector"], "bestaudio/best")
        self.assertEqual(self.repo.records[-1]["status"], "Queued")


if __name__ == "__main__":
    unittest.main()
