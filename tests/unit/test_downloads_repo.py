from __future__ import annotations

import importlib
import os
import unittest
from tempfile import TemporaryDirectory


class TestDownloadsRepo(unittest.TestCase):
    def test_downloads_repo_upsert_and_list(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.core.paths as paths
            import app.database.migrations as migrations
            import app.database.repositories.downloads_repo as repo_mod

            importlib.reload(paths)
            importlib.reload(migrations)
            importlib.reload(repo_mod)

            migrations.apply_migrations()
            repo = repo_mod.DownloadsRepository()
            repo.upsert({
                "id": "t1",
                "source_url": "https://example.com/v",
                "title": "Video",
                "thumbnail_url": "",
                "selected_format": "best",
                "output_path": td,
                "status": "Queued",
                "progress": 0.0,
                "downloaded_bytes": None,
                "total_bytes": None,
                "speed": None,
                "eta": None,
                "error_code": None,
                "error_message": None,
                "playlist_id": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None,
            })
            rows = repo.list_recent(10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "t1")
            self.assertEqual(rows[0]["status"], "Queued")
            got = repo.get_by_id("t1")
            self.assertIsNotNone(got)
            self.assertEqual(got["title"], "Video")
            repo.update_status("t1", "Completed", progress=100.0, total_bytes=1024 * 1024, updated_at="2026-01-01T00:01:00+00:00", completed_at="2026-01-01T00:01:00+00:00")
            self.assertEqual(repo.counts().get("Completed"), 1)
            self.assertEqual(repo.total_completed_bytes(), 1024 * 1024)

    def test_mark_interrupted_marks_active_tasks_failed(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.core.paths as paths
            import app.database.migrations as migrations
            import app.database.repositories.downloads_repo as repo_mod

            importlib.reload(paths)
            importlib.reload(migrations)
            importlib.reload(repo_mod)

            migrations.apply_migrations()
            repo = repo_mod.DownloadsRepository()
            base = {
                "source_url": "https://example.com/v", "title": "V", "thumbnail_url": "",
                "selected_format": "best", "output_path": td, "progress": 10.0,
                "downloaded_bytes": None, "total_bytes": None, "speed": None, "eta": None,
                "error_code": None, "error_message": None, "playlist_id": None,
                "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None,
            }
            for tid, status in [("a1", "Downloading"), ("a2", "Queued"), ("a3", "Completed")]:
                repo.upsert({**base, "id": tid, "status": status})
            changed = repo.mark_interrupted("Interrupted by application restart")
            self.assertEqual(changed, 1)
            self.assertEqual(repo.get_by_id("a1")["status"], "Failed")
            self.assertEqual(repo.get_by_id("a2")["status"], "Queued")
            self.assertEqual(repo.get_by_id("a3")["status"], "Completed")


if __name__ == "__main__":
    unittest.main()
