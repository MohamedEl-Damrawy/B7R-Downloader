"""Schema v3 migration tests: fresh DB + idempotent re-apply."""

from __future__ import annotations

import importlib
import os
import unittest
from tempfile import TemporaryDirectory


class TestSchemaV3(unittest.TestCase):
    def _reload_db_modules(self):
        import app.core.paths as paths
        import app.database.connection as connection
        import app.database.migrations as migrations

        importlib.reload(paths)
        importlib.reload(connection)
        importlib.reload(migrations)
        return migrations

    def test_fresh_db_has_v3_columns_and_version(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            migrations = self._reload_db_modules()
            migrations.apply_migrations()
            self.assertEqual(migrations.SCHEMA_VERSION, 3)
            from app.database.connection import get_connection

            conn = get_connection()
            try:
                self.assertEqual(migrations.get_current_version(conn), 3)
                downloads_cols = {r["name"] for r in conn.execute("PRAGMA table_info(downloads)").fetchall()}
                items_cols = {r["name"] for r in conn.execute("PRAGMA table_info(download_items)").fetchall()}
            finally:
                conn.close()
            self.assertIn("source_type", downloads_cols)
            self.assertIn("playlist_items", downloads_cols)
            for col in ("artist", "album", "cover_url"):
                self.assertIn(col, items_cols)

    def test_migration_is_idempotent(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            migrations = self._reload_db_modules()
            migrations.apply_migrations()
            # Applying again must not raise (guards: _column_exists + version check)
            migrations.apply_migrations()
            from app.database.connection import get_connection

            conn = get_connection()
            try:
                self.assertEqual(migrations.get_current_version(conn), 3)
            finally:
                conn.close()

    def test_upgrade_from_v2_db(self):
        """A pre-v3 DB (v2 layout) gains the new columns via ALTER, keeping data."""
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            migrations = self._reload_db_modules()

            import sqlite3

            from app.core.paths import get_database_path

            db_path = get_database_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("PRAGMA foreign_keys = ON;")
                # Recreate the v2 downloads/download_items layout.
                conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
                conn.execute(
                    """CREATE TABLE downloads (
                        id TEXT PRIMARY KEY, source_url TEXT NOT NULL, title TEXT, thumbnail_url TEXT,
                        selected_format TEXT, output_path TEXT, status TEXT NOT NULL,
                        progress REAL NOT NULL DEFAULT 0, downloaded_bytes INTEGER, total_bytes INTEGER,
                        speed REAL, eta INTEGER, error_code TEXT, error_message TEXT,
                        playlist_id TEXT, playlist_items TEXT,
                        created_at TEXT NOT NULL, updated_at TEXT, completed_at TEXT)"""
                )
                conn.execute(
                    """CREATE TABLE download_items (
                        id TEXT PRIMARY KEY, playlist_id TEXT NOT NULL, download_id TEXT,
                        entry_index INTEGER, source_url TEXT, title TEXT, thumbnail_url TEXT,
                        status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, output_path TEXT,
                        error_message TEXT)"""
                )
                conn.execute(
                    "INSERT INTO downloads(id, source_url, status, progress, created_at) "
                    "VALUES ('old1', 'https://youtu.be/x', 'Completed', 100.0, '2026-01-01T00:00:00+00:00')"
                )
                conn.execute(
                    "INSERT INTO schema_version(version, applied_at) VALUES (2, '2026-01-01T00:00:00+00:00')"
                )
                conn.commit()
            finally:
                conn.close()

            migrations.apply_migrations()

            from app.database.connection import get_connection

            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT id, source_type FROM downloads WHERE id = 'old1'"
                ).fetchone()
                self.assertIsNotNone(row)
                # Existing rows get NULL source_type; code treats NULL as youtube.
                self.assertIsNone(row["source_type"])
                v = migrations.get_current_version(conn)
                self.assertEqual(v, 3)
                cols = {r["name"] for r in conn.execute("PRAGMA table_info(download_items)").fetchall()}
                self.assertIn("artist", cols)
                self.assertIn("album", cols)
                self.assertIn("cover_url", cols)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
