from __future__ import annotations

import importlib
import os
import unittest
from tempfile import TemporaryDirectory


class TestPlaylistRepos(unittest.TestCase):
    def test_playlists_and_items_repos(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.core.paths as paths
            import app.database.migrations as migrations
            import app.database.repositories.download_items_repo as items_repo_mod
            import app.database.repositories.playlists_repo as pl_repo_mod

            importlib.reload(paths)
            importlib.reload(migrations)
            importlib.reload(pl_repo_mod)
            importlib.reload(items_repo_mod)

            migrations.apply_migrations()
            pl_repo = pl_repo_mod.PlaylistsRepository()
            items_repo = items_repo_mod.DownloadItemsRepository()

            pl_repo.upsert({
                "id": "pl1",
                "source_url": "https://example.com/playlist",
                "title": "My Playlist",
                "thumbnail_url": "",
                "total_entries": 2,
                "created_at": "2026-01-01T00:00:00+00:00",
            })
            self.assertEqual(pl_repo.get("pl1")["title"], "My Playlist")
            self.assertEqual(len(pl_repo.list_recent(10)), 1)

            # Create a download row to satisfy FK when linking playlist item
            import app.database.repositories.downloads_repo as dl_repo_mod
            importlib.reload(dl_repo_mod)
            dl_repo = dl_repo_mod.DownloadsRepository()
            dl_repo.upsert({
                "id": "d1",
                "source_url": "https://example.com/v1",
                "title": "V1",
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
                "playlist_id": "pl1",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None,
            })

            items_repo.upsert_many([
                {"id": "pl1:1", "playlist_id": "pl1", "download_id": None, "entry_index": 1,
                 "source_url": "https://example.com/v1", "title": "V1", "thumbnail_url": "",
                 "status": "Available", "progress": 0.0, "output_path": None, "error_message": None},
                {"id": "pl1:2", "playlist_id": "pl1", "download_id": None, "entry_index": 2,
                 "source_url": "https://example.com/v2", "title": "V2", "thumbnail_url": "",
                 "status": "Available", "progress": 0.0, "output_path": None, "error_message": None},
            ])
            rows = items_repo.list_by_playlist("pl1")
            self.assertEqual(len(rows), 2)
            items_repo.link_download("pl1:1", "d1", "Queued")
            items_repo.update_by_download_id("d1", "Completed", progress=100.0)
            got = items_repo.get_by_download_id("d1")
            self.assertIsNotNone(got)
            self.assertEqual(got["status"], "Completed")
            self.assertEqual(got["progress"], 100.0)

    def test_mark_interrupted_items(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.core.paths as paths
            import app.database.migrations as migrations
            import app.database.repositories.download_items_repo as items_repo_mod
            import app.database.repositories.downloads_repo as dl_repo_mod
            import app.database.repositories.playlists_repo as pl_repo_mod

            importlib.reload(paths)
            importlib.reload(migrations)
            importlib.reload(pl_repo_mod)
            importlib.reload(items_repo_mod)
            importlib.reload(dl_repo_mod)

            migrations.apply_migrations()
            pl_repo = pl_repo_mod.PlaylistsRepository()
            items_repo = items_repo_mod.DownloadItemsRepository()
            dl_repo = dl_repo_mod.DownloadsRepository()

            pl_repo.upsert({
                "id": "pl2", "source_url": "https://example.com/pl", "title": "PL",
                "thumbnail_url": "", "total_entries": 1, "created_at": "2026-01-01T00:00:00+00:00",
            })
            dl_repo.upsert({
                "id": "d2", "source_url": "https://example.com/v", "title": "V", "thumbnail_url": "",
                "selected_format": "best", "output_path": td, "status": "Downloading", "progress": 50.0,
                "downloaded_bytes": None, "total_bytes": None, "speed": None, "eta": None,
                "error_code": None, "error_message": None, "playlist_id": "pl2",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00", "completed_at": None,
            })
            items_repo.upsert_many([{
                "id": "pl2:1", "playlist_id": "pl2", "download_id": "d2", "entry_index": 1,
                "source_url": "https://example.com/v", "title": "V", "thumbnail_url": "",
                "status": "Downloading", "progress": 50.0, "output_path": None, "error_message": None,
            }])
            changed = items_repo.mark_interrupted("Interrupted by application restart")
            self.assertEqual(changed, 1)
            got = items_repo.get_by_download_id("d2")
            self.assertIsNotNone(got)
            self.assertEqual(got["status"], "Failed")


if __name__ == "__main__":
    unittest.main()
