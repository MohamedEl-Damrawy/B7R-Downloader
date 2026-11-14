"""Playlists repository."""

from __future__ import annotations

from typing import Any

from app.database.connection import db_session


class PlaylistsRepository:
    def upsert(self, playlist: dict[str, Any]) -> None:
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO playlists(id, source_url, title, thumbnail_url, total_entries, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_url=excluded.source_url,
                    title=excluded.title,
                    thumbnail_url=excluded.thumbnail_url,
                    total_entries=excluded.total_entries
                """,
                (
                    playlist.get("id"),
                    playlist.get("source_url"),
                    playlist.get("title"),
                    playlist.get("thumbnail_url"),
                    playlist.get("total_entries"),
                    playlist.get("created_at"),
                ),
            )

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT * FROM playlists ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get(self, playlist_id: str) -> dict[str, Any] | None:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
            return dict(row) if row else None
