"""Download items repository."""

from __future__ import annotations

from typing import Any

from app.database.connection import db_session


class DownloadItemsRepository:
    def upsert_many(self, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        with db_session() as conn:
            conn.executemany(
                """
                INSERT INTO download_items(
                    id, playlist_id, download_id, entry_index, source_url, title, thumbnail_url,
                    status, progress, output_path, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    playlist_id=excluded.playlist_id,
                    download_id=excluded.download_id,
                    entry_index=excluded.entry_index,
                    source_url=excluded.source_url,
                    title=excluded.title,
                    thumbnail_url=excluded.thumbnail_url,
                    status=excluded.status,
                    progress=excluded.progress,
                    output_path=excluded.output_path,
                    error_message=excluded.error_message
                """,
                [
                    (
                        it.get("id"), it.get("playlist_id"), it.get("download_id"), it.get("entry_index"),
                        it.get("source_url"), it.get("title"), it.get("thumbnail_url"), it.get("status"),
                        it.get("progress", 0.0), it.get("output_path"), it.get("error_message"),
                    )
                    for it in items
                ],
            )

    def link_download(self, item_id: str, download_id: str, status: str = "Queued") -> None:
        with db_session() as conn:
            conn.execute(
                "UPDATE download_items SET download_id = ?, status = ?, error_message = NULL WHERE id = ?",
                (download_id, status, item_id),
            )

    def update_by_download_id(self, download_id: str, status: str, progress: float | None = None,
                              output_path: str | None = None, error_message: str | None = None) -> None:
        fields = ["status = ?"]
        params: list[Any] = [status]
        if progress is not None:
            fields.append("progress = ?")
            params.append(float(progress))
        if output_path is not None:
            fields.append("output_path = ?")
            params.append(output_path)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        params.append(download_id)
        with db_session() as conn:
            conn.execute(f"UPDATE download_items SET {', '.join(fields)} WHERE download_id = ?", params)

    def mark_interrupted(self, message: str = "Interrupted by application restart") -> int:
        with db_session() as conn:
            cur = conn.execute(
                """
                UPDATE download_items SET status = 'Failed',
                    error_message = COALESCE(error_message, ?)
                WHERE download_id IN (
                    SELECT id FROM downloads WHERE status IN ('Extracting','Downloading','Processing')
                )
                """,
                (message,),
            )
            return cur.rowcount if cur.rowcount is not None else 0

    def list_by_playlist(self, playlist_id: str) -> list[dict[str, Any]]:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM download_items
                WHERE playlist_id = ?
                ORDER BY CASE WHEN entry_index IS NULL THEN 1 ELSE 0 END, entry_index ASC, id ASC
                """,
                (playlist_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_by_download_id(self, download_id: str) -> dict[str, Any] | None:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM download_items WHERE download_id = ? LIMIT 1",
                (download_id,),
            ).fetchone()
            return dict(row) if row else None

    def get(self, item_id: str) -> dict[str, Any] | None:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM download_items WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None
