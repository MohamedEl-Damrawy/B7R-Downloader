"""Unit tests for controller start_source_plan (Spotify plan → tasks)."""

from __future__ import annotations

import json
import os
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QCoreApplication

from app.controllers.download_controller import DownloadController
from app.sources.base import SourcePlan, TrackSpec


class _FakeRepo:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.stored: dict[str, dict[str, Any]] = {}
        self.status_calls: list[dict[str, Any]] = []

    def update_status(self, download_id: str, status, **kwargs) -> None:
        self.status_calls.append({"id": download_id, "status": status, **kwargs})

    def upsert(self, record: dict[str, Any]) -> None:
        self.records.append(record)
        self.stored[record["id"]] = record

    def get_by_id(self, download_id: str) -> dict[str, Any] | None:
        return self.stored.get(download_id)


class _FakeItemsRepo:
    def link_download(self, *a, **k) -> None: ...
    def update_by_download_id(self, *a, **k) -> None: ...
    def get_by_download_id(self, *a, **k) -> None: return None
    def list_by_download_id(self, *a, **k) -> list: return []


def _make_controller(test: unittest.TestCase) -> tuple[DownloadController, _FakeRepo]:
    QCoreApplication.instance() or QCoreApplication([])
    ctrl = DownloadController()
    repo = _FakeRepo()
    ctrl.repo = repo
    ctrl.items_repo = _FakeItemsRepo()
    ctrl._start_worker = lambda task_id, spec: None  # type: ignore[method-assign]
    import app.controllers.download_controller as mod

    orig_settings = mod.SettingsService
    mod.SettingsService = lambda: SimpleNamespace(get=lambda k, d=None: d)  # type: ignore[assignment]
    test.addCleanup(setattr, mod, "SettingsService", orig_settings)
    return ctrl, repo


def _track_spec(title="Blinding Lights", artist="The Weeknd", **kwargs) -> TrackSpec:
    defaults = dict(
        title=title,
        artist=artist,
        album="After Hours",
        duration_sec=200,
        cover_url="https://img/c.jpg",
        source_url="https://open.spotify.com/track/id1",
        source_type="spotify",
        search_query="The Weeknd - Blinding Lights",
        index=1,
        available=True,
    )
    defaults.update(kwargs)
    return TrackSpec(**defaults)


class TestStartSourcePlan(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        os.environ.setdefault("LOCALAPPDATA", self._tmp.name)

    def test_track_plan_creates_single_matched_task(self):
        ctrl, repo = _make_controller(self)
        plan = SourcePlan(
            kind="track",
            title="Blinding Lights",
            entries=[_track_spec()],
            source_url="https://open.spotify.com/track/id1",
        )
        ids = ctrl.start_source_plan(plan, self._tmp.name, "mp3_320")
        self.assertEqual(len(ids), 1)
        rec = repo.records[0]
        self.assertEqual(rec["source_type"], "spotify")
        self.assertEqual(rec["selected_format"], "mp3_320")
        meta = json.loads(rec["source_meta"])
        self.assertEqual(meta["search_query"], "The Weeknd - Blinding Lights")
        self.assertEqual(meta["duration_sec"], 200)
        self.assertEqual(meta["artist"], "The Weeknd")
        spec = ctrl._specs[ids[0]]
        self.assertEqual(spec["search_query"], "The Weeknd - Blinding Lights")
        self.assertEqual(spec["audio_format"], "mp3")
        self.assertEqual(spec["audio_quality"], "320")

    def test_playlist_plan_creates_per_track_tasks(self):
        ctrl, repo = _make_controller(self)
        entries = [
            _track_spec(title=f"S{i}", artist="A", source_url=f"https://open.spotify.com/track/id{i}")
            for i in range(3)
        ]
        plan = SourcePlan(kind="playlist", title="P", entries=entries, source_url="https://open.spotify.com/playlist/pid")
        ids = ctrl.start_source_plan(plan, self._tmp.name, "m4a_256")
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(repo.records), 3)
        self.assertTrue(all(r["source_type"] == "spotify" for r in repo.records))
        # Each entry is its own task (no playlist_items batching for Spotify).
        self.assertTrue(all(not r["playlist_items"] for r in repo.records))

    def test_unavailable_entries_skipped(self):
        ctrl, repo = _make_controller(self)
        entries = [
            _track_spec(title="Ok", artist="A", source_url="https://open.spotify.com/track/ok"),
            _track_spec(title="Local", artist="A", available=False, source_url=""),
        ]
        plan = SourcePlan(kind="playlist", title="P", entries=entries, source_url="url")
        ids = ctrl.start_source_plan(plan, self._tmp.name, "mp3_320")
        self.assertEqual(len(ids), 1)
        self.assertEqual(repo.records[0]["title"], "Ok")

    def test_empty_plan_returns_empty(self):
        ctrl, _ = _make_controller(self)
        self.assertEqual(ctrl.start_source_plan(None, ".", "mp3_320"), [])
        self.assertEqual(ctrl.start_source_plan(SourcePlan(kind="playlist", title="P", entries=[]), ".", "mp3_320"), [])


class TestSpotifyRetryReconstruction(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        os.environ.setdefault("LOCALAPPDATA", self._tmp.name)

    def test_retry_rebuilds_search_from_source_meta(self):
        ctrl, repo = _make_controller(self)
        meta = {
            "title": "Blinding Lights",
            "artist": "The Weeknd",
            "album": "After Hours",
            "cover_url": "https://img/c.jpg",
            "duration_sec": 200,
            "search_query": "The Weeknd - Blinding Lights",
        }
        rec = {
            "id": "t1",
            "source_url": "https://open.spotify.com/track/id1",
            "title": "Blinding Lights",
            "thumbnail_url": "",
            "selected_format": "mp3_320",
            "output_path": self._tmp.name,
            "status": "Failed",
            "playlist_id": None,
            "playlist_items": None,
            "source_type": "spotify",
            "source_meta": json.dumps(meta),
        }
        repo.stored["t1"] = rec
        new_id = ctrl.retry_download("t1")
        self.assertIsNotNone(new_id)
        new_rec = repo.records[-1]
        self.assertEqual(new_rec["source_type"], "spotify")
        self.assertEqual(json.loads(new_rec["source_meta"]), meta)
        spec = ctrl._specs[new_id]
        self.assertEqual(spec["search_query"], "The Weeknd - Blinding Lights")
        self.assertEqual(spec["meta"]["artist"], "The Weeknd")

    def test_retry_refuses_spotify_task_without_search_meta(self):
        ctrl, repo = _make_controller(self)
        rec = {
            "id": "t2",
            "source_url": "https://open.spotify.com/track/id1",
            "title": "X",
            "thumbnail_url": "",
            "selected_format": "mp3_320",
            "output_path": self._tmp.name,
            "status": "Failed",
            "playlist_id": None,
            "playlist_items": None,
            "source_type": "spotify",
            "source_meta": None,
        }
        repo.stored["t2"] = rec
        self.assertIsNone(ctrl.retry_download("t2"))


if __name__ == "__main__":
    unittest.main()
