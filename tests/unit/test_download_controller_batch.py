"""Unit tests for PERF-04 (batch playlist downloads) + schema migration v2."""

from __future__ import annotations

import importlib
import os
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

from app.controllers.download_controller import _PLAYLIST_BATCH_SIZE, DownloadController
from app.models.download_status import DownloadStatus


class _FakeRepo:
    """In-memory stand-in for DownloadsRepository."""

    def __init__(self) -> None:
        self.status_calls: list[dict[str, Any]] = []
        self.records: list[dict[str, Any]] = []
        self.stored: dict[str, dict[str, Any]] = {}

    def update_status(self, download_id: str, status, **kwargs) -> None:
        self.status_calls.append({"id": download_id, "status": status, **kwargs})

    def upsert(self, record: dict[str, Any]) -> None:
        self.records.append(record)
        self.stored[record["id"]] = record

    def get_by_id(self, download_id: str) -> dict[str, Any] | None:
        return self.stored.get(download_id)


class _FakeItemsRepo:
    """Records link_download calls; emulates get/list by download id."""

    def __init__(self) -> None:
        self.links: list[tuple[str, str, str]] = []
        self.items_by_download: dict[str, list[dict[str, Any]]] = {}

    def link_download(self, item_id: str, download_id: str, status: str = "Queued") -> None:
        self.links.append((item_id, download_id, status))
        self.items_by_download.setdefault(download_id, []).append({"id": item_id})

    def update_by_download_id(self, *a, **k) -> None:
        pass

    def get_by_download_id(self, download_id: str) -> dict[str, Any] | None:
        items = self.items_by_download.get(download_id) or []
        return items[0] if items else None

    def list_by_download_id(self, download_id: str) -> list[dict[str, Any]]:
        return list(self.items_by_download.get(download_id) or [])


def _entry(idx: int | None = None, url: str = "", item_id: str | None = None, available: bool = True):
    return SimpleNamespace(
        available=available,
        source_url=url,
        index=idx,
        title=f"Entry {idx}" if idx is not None else "Direct",
        thumbnail_url="",
        playlist_item_id=item_id,
    )


def _make_controller(repo: _FakeRepo, items: _FakeItemsRepo) -> DownloadController:
    QCoreApplication.instance() or QCoreApplication([])
    ctrl = DownloadController()
    ctrl.repo = repo
    ctrl.items_repo = items
    return ctrl


def _patch_enqueue_env(test: unittest.TestCase, ctrl: DownloadController):
    """Prevent real workers/settings/disk checks during enqueue-path tests."""
    import app.controllers.download_controller as mod

    ctrl._start_worker = lambda task_id, spec: None  # type: ignore[method-assign]
    orig_settings = mod.SettingsService
    mod.SettingsService = lambda: SimpleNamespace(get=lambda k, d=None: d)  # type: ignore[assignment]
    test.addCleanup(setattr, mod, "SettingsService", orig_settings)


class TestMigrationV2(unittest.TestCase):
    """Schema v2: playlist_items column + recorded schema version."""

    def test_fresh_db_has_playlist_items_column(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.database.connection as connection
            import app.database.migrations as migrations
            import app.database.schema as schema

            importlib.reload(connection)
            importlib.reload(schema)
            importlib.reload(migrations)

            self.assertEqual(schema.SCHEMA_VERSION, 2)
            migrations.apply_migrations()
            with connection.db_session() as conn:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(downloads)").fetchall()]
                self.assertIn("playlist_items", cols)
                ver = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
                self.assertEqual(ver["v"], 2)

            # Re-running migrations is idempotent.
            migrations.apply_migrations()
            with connection.db_session() as conn:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(downloads)").fetchall()]
                self.assertIn("playlist_items", cols)


class TestPlaylistBatching(unittest.TestCase):
    """PERF-04: index-only entries batch into chunk tasks with combined playlist_items."""

    def setUp(self) -> None:
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = _FakeRepo()
        self.items = _FakeItemsRepo()
        self.ctrl = _make_controller(self.repo, self.items)
        _patch_enqueue_env(self, self.ctrl)
        self.playlist_url = "https://www.youtube.com/playlist?list=PL123"

    def _batches(self) -> list[dict[str, Any]]:
        return [r for r in self.repo.records if r["playlist_items"]]

    def test_index_only_entries_batched_in_chunks(self):
        entries = [_entry(idx=i, item_id=f"item{i}") for i in range(1, 31)]  # 30 entries
        ids = self.ctrl.start_playlist_downloads(
            playlist_url=self.playlist_url,
            output_dir=self.tmpdir.name,
            quality="best",
            entries=entries,
            playlist_title="My Playlist",
        )
        self.assertEqual(_PLAYLIST_BATCH_SIZE, 25)
        batches = self._batches()
        self.assertEqual(len(batches), 2)  # 25 + 5
        first, second = batches
        self.assertEqual(first["playlist_items"], ",".join(str(i) for i in range(1, 26)))
        self.assertEqual(second["playlist_items"], ",".join(str(i) for i in range(26, 31)))
        self.assertEqual(first["title"], "My Playlist (25 items)")
        self.assertEqual(second["title"], "My Playlist (5 items)")
        self.assertTrue(len(ids) == 2)
        # Every batch task uses the playlist URL (never per-entry URLs).
        for b in batches:
            self.assertEqual(b["source_url"], self.playlist_url)
        # Spec carries the batch size for progress aggregation.
        spec = self.ctrl._specs[ids[0]]
        self.assertEqual(spec["playlist_item_count"], 25)

    def test_direct_url_entries_stay_per_item(self):
        entries = [_entry(url="https://www.youtube.com/watch?v=A", item_id="iA"),
                   _entry(url="https://www.youtube.com/watch?v=B", item_id="iB")]
        self.ctrl.start_playlist_downloads(
            playlist_url=self.playlist_url,
            output_dir=self.tmpdir.name,
            quality="best",
            entries=entries,
        )
        batches = self._batches()
        self.assertEqual(batches, [])  # no batch tasks
        urls = [r["source_url"] for r in self.repo.records]
        self.assertEqual(urls, [entries[0].source_url, entries[1].source_url])
        for r in self.repo.records:
            self.assertIsNone(r["playlist_items"])

    def test_mixed_entries(self):
        entries = [
            _entry(idx=1, item_id="i1"),
            _entry(url="https://www.youtube.com/watch?v=D", item_id="iD"),
            _entry(idx=2, item_id="i2"),
            _entry(idx=3, item_id="i3", available=False),  # skipped
        ]
        self.ctrl.start_playlist_downloads(
            playlist_url=self.playlist_url,
            output_dir=self.tmpdir.name,
            quality="best",
            entries=entries,
            playlist_title="PL",
        )
        batches = self._batches()
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["playlist_items"], "1,2")  # unavailable entry skipped
        direct = [r for r in self.repo.records if r["playlist_items"] is None]
        self.assertEqual(len(direct), 1)
        self.assertEqual(direct[0]["source_url"], "https://www.youtube.com/watch?v=D")

    def test_batch_items_linked_to_task(self):
        entries = [_entry(idx=i, item_id=f"item{i}") for i in range(1, 4)]
        ids = self.ctrl.start_playlist_downloads(
            playlist_url=self.playlist_url,
            output_dir=self.tmpdir.name,
            quality="best",
            entries=entries,
        )
        task_id = ids[0]
        linked_items = {item for item, tid, _s in self.items.links if tid == task_id}
        self.assertEqual(linked_items, {"item1", "item2", "item3"})

    def test_batches_sorted_by_index(self):
        entries = [_entry(idx=i, item_id=f"item{i}") for i in (5, 2, 9, 1)]
        self.ctrl.start_playlist_downloads(
            playlist_url=self.playlist_url,
            output_dir=self.tmpdir.name,
            quality="best",
            entries=entries,
        )
        batch = self._batches()[0]
        self.assertEqual(batch["playlist_items"], "1,2,5,9")


class TestBatchProgressAggregation(unittest.TestCase):
    """PERF-04: monotonic overall percentage across per-item restarts."""

    def setUp(self) -> None:
        self.repo = _FakeRepo()
        self.ctrl = _make_controller(self.repo, _FakeItemsRepo())
        self.addCleanup(self.ctrl.deleteLater)
        import app.controllers.download_controller as mod

        self.mod = mod
        self.task_id = "batch1"
        self.ctrl._specs[self.task_id] = {"playlist_item_count": 4}
        self.ctrl._batch_state[self.task_id] = {"completed": 0, "last_progress": 0.0}

    def _progress(self, pct, status="downloading"):
        self.ctrl._on_progress({"task_id": self.task_id, "percentage": pct, "status": status})

    def _last_ui_progress(self) -> float:
        # The UI payload is emitted on every call (unthrottled); DB writes are
        # throttled, so assertions check the live task cache instead.
        return self.ctrl._tasks[self.task_id]["progress"]

    def test_item_restarts_are_aggregated(self):
        # Realistic hook sequence: an item's first hook always starts low.
        self._progress(100.0)  # item 1 done
        self.assertAlmostEqual(self._last_ui_progress(), 25.0)
        self._progress(2.0)  # item 2 starts -> drop detected
        self.assertAlmostEqual(self._last_ui_progress(), (1 + 0.02) / 4 * 100)
        self._progress(100.0)  # item 2 done
        self.assertAlmostEqual(self._last_ui_progress(), 50.0)
        self._progress(3.0)  # item 3 starts -> drop detected
        self.assertAlmostEqual(self._last_ui_progress(), (2 + 0.03) / 4 * 100)
        self._progress(80.0)  # item 3 mid-download
        self.assertAlmostEqual(self._last_ui_progress(), (2 + 0.8) / 4 * 100)

    def test_small_fluctuations_do_not_count_as_new_item(self):
        self._progress(60.0)
        self._progress(55.0)  # small dip -> NOT a restart
        state = self.ctrl._batch_state[self.task_id]
        self.assertEqual(state["completed"], 0)
        self.assertAlmostEqual(state["last_progress"], 55.0)

    def test_postprocessing_keeps_last_percentage(self):
        self._progress(50.0)
        self._progress(None, status="postprocessing")
        self.assertAlmostEqual(self._last_ui_progress(), 12.5)

    def test_single_item_tasks_unaffected(self):
        self.ctrl._on_progress({"task_id": "solo", "percentage": 42.0, "status": "downloading"})
        self.assertAlmostEqual(self.ctrl._tasks["solo"]["progress"], 42.0)


class TestRetryBatchTasks(unittest.TestCase):
    """PERF-04: retry preserves playlist_items; guard blocks full-playlist retries."""

    def setUp(self) -> None:
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.repo = _FakeRepo()
        self.items = _FakeItemsRepo()
        self.ctrl = _make_controller(self.repo, self.items)
        _patch_enqueue_env(self, self.ctrl)
        self.playlist_url = "https://www.youtube.com/playlist?list=PL123"
        self._pl_patch = patch(
            "app.database.repositories.playlists_repo.PlaylistsRepository",
            lambda: SimpleNamespace(get=lambda _id: {"source_url": self.playlist_url}),
        )
        self._pl_patch.start()
        self.addCleanup(self._pl_patch.stop)

    def _record(self, **overrides) -> dict[str, Any]:
        rec = {
            "id": "old1",
            "source_url": self.playlist_url,
            "title": "My Playlist (25 items)",
            "thumbnail_url": "",
            "selected_format": "best",
            "output_path": self.tmpdir.name,
            "status": DownloadStatus.FAILED.value,
            "progress": 0.0,
            "playlist_id": "p1",
            "playlist_items": None,
        }
        rec.update(overrides)
        self.repo.stored["old1"] = rec
        return rec

    def test_retry_blocked_for_playlist_url_without_selection(self):
        self._record()
        result = self.ctrl.retry_download("old1")
        self.assertIsNone(result)
        self.assertEqual(self.repo.records, [])  # nothing enqueued

    def test_retry_uses_persisted_playlist_items(self):
        self._record(playlist_items="1,2,3")
        new_id = self.ctrl.retry_download("old1")
        self.assertTrue(new_id)
        self.assertEqual(self.repo.records[-1]["playlist_items"], "1,2,3")

    def test_retry_relinks_batch_items(self):
        self._record(playlist_items="1,2")
        self.items.items_by_download["old1"] = [{"id": "i1"}, {"id": "i2"}]
        new_id = self.ctrl.retry_download("old1")
        self.assertTrue(new_id)
        relinked = {item for item, tid, _s in self.items.links if tid == new_id}
        self.assertEqual(relinked, {"i1", "i2"})

    def test_direct_url_retry_unaffected(self):
        rec = self._record(source_url="https://www.youtube.com/watch?v=D", playlist_items=None)
        self.items.items_by_download["old1"] = [{"id": "iD", "entry_index": None}]
        new_id = self.ctrl.retry_download("old1")
        self.assertTrue(new_id)
        self.assertIsNone(self.repo.records[-1]["playlist_items"])
        self.assertEqual(rec["source_url"], "https://www.youtube.com/watch?v=D")


if __name__ == "__main__":
    unittest.main()
