"""Database schema definitions."""

from __future__ import annotations

SCHEMA_VERSION = 3

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS downloads (
        id TEXT PRIMARY KEY,
        source_url TEXT NOT NULL,
        title TEXT,
        thumbnail_url TEXT,
        selected_format TEXT,
        output_path TEXT,
        status TEXT NOT NULL,
        progress REAL NOT NULL DEFAULT 0,
        downloaded_bytes INTEGER,
        total_bytes INTEGER,
        speed REAL,
        eta INTEGER,
        error_code TEXT,
        error_message TEXT,
        playlist_id TEXT,
        playlist_items TEXT,
        source_type TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        completed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS playlists (
        id TEXT PRIMARY KEY,
        source_url TEXT NOT NULL UNIQUE,
        title TEXT,
        thumbnail_url TEXT,
        total_entries INTEGER,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS download_items (
        id TEXT PRIMARY KEY,
        playlist_id TEXT NOT NULL,
        download_id TEXT,
        entry_index INTEGER,
        source_url TEXT,
        title TEXT,
        thumbnail_url TEXT,
        status TEXT NOT NULL,
        progress REAL NOT NULL DEFAULT 0,
        output_path TEXT,
        error_message TEXT,
        artist TEXT,
        album TEXT,
        cover_url TEXT,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
        FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_downloads_status_created ON downloads(status, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_download_items_playlist ON download_items(playlist_id);",
    "CREATE INDEX IF NOT EXISTS idx_download_items_download ON download_items(download_id);",
]
