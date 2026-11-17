"""Downloads repository."""

from __future__ import annotations

from typing import Any

from app.database.connection import db_session
from app.models.download import utc_now_iso
from app.models.download_status import DownloadStatus


class DownloadsRepository:
    def upsert(self, task: dict[str, Any]) -> None:
        cols = [
            "id","source_url","title","thumbnail_url","selected_format","output_path","status",
            "progress","downloaded_bytes","total_bytes","speed","eta","error_code","error_message",
            "playlist_id","playlist_items","created_at","updated_at","completed_at"
        ]
        values = [task.get(c) for c in cols]
        placeholders = ",".join(["?"] * len(cols))
        updates = ",".join([f"{c}=excluded.{c}" for c in cols if c != "id"])
        with db_session() as conn:
            conn.execute(
                f"INSERT INTO downloads({','.join(cols)}) VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {updates}",
                values,
            )

    def update_status(self, download_id: str, status: DownloadStatus | str, progress: float | None = None,
                      error_code: str | None = None, error_message: str | None = None,
                      updated_at: str | None = None, completed_at: str | None = None,
                      downloaded_bytes: int | None = None, total_bytes: int | None = None,
                      speed: float | None = None, eta: int | None = None, output_path: str | None = None) -> None:
        fields = ["status = ?"]
        params: list[Any] = [str(status.value if isinstance(status, DownloadStatus) else status)]
        if progress is not None:
            fields.append("progress = ?")
            params.append(float(progress))
        if downloaded_bytes is not None:
            fields.append("downloaded_bytes = ?")
            params.append(int(downloaded_bytes))
        if total_bytes is not None:
            fields.append("total_bytes = ?")
            params.append(int(total_bytes))
        if speed is not None:
            fields.append("speed = ?")
            params.append(float(speed))
        if eta is not None:
            fields.append("eta = ?")
            params.append(int(eta))
        if output_path is not None:
            fields.append("output_path = ?")
            params.append(output_path)
        if error_code is not None:
            fields.append("error_code = ?")
            params.append(error_code)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        if updated_at is not None:
            fields.append("updated_at = ?")
            params.append(updated_at)
        if completed_at is not None:
            fields.append("completed_at = ?")
            params.append(completed_at)
        params.append(download_id)
        with db_session() as conn:
            conn.execute(f"UPDATE downloads SET {', '.join(fields)} WHERE id = ?", params)

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT * FROM downloads ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_by_id(self, download_id: str) -> dict[str, Any] | None:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM downloads WHERE id = ?", (download_id,)).fetchone()
            return dict(row) if row else None

    def list_by_statuses(self, statuses: list[str], limit: int = 200) -> list[dict[str, Any]]:
        if not statuses:
            return []
        placeholders = ",".join(["?"] * len(statuses))
        with db_session() as conn:
            rows = conn.execute(
                f"SELECT * FROM downloads WHERE status IN ({placeholders}) "
                "ORDER BY updated_at DESC, created_at DESC LIMIT ?",
                (*statuses, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def counts(self) -> dict[str, int]:
        with db_session() as conn:
            rows = conn.execute("SELECT status, COUNT(*) as c FROM downloads GROUP BY status").fetchall()
            return {str(r["status"]): int(r["c"]) for r in rows}

    def total_completed_bytes(self) -> int:
        with db_session() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(COALESCE(total_bytes, downloaded_bytes, 0)), 0) AS total "
                "FROM downloads WHERE status = 'Completed'"
            ).fetchone()
            return int(row["total"] or 0) if row else 0

    def delete(self, download_id: str) -> bool:
        """FEAT-11: remove a history record (metadata only; files stay on disk)."""
        with db_session() as conn:
            cur = conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            return (cur.rowcount or 0) > 0

    def delete_many(self, download_ids: list[str]) -> int:
        """Remove several history records at once; returns rows deleted."""
        ids = [str(i) for i in (download_ids or []) if str(i or "").strip()]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with db_session() as conn:
            cur = conn.execute(f"DELETE FROM downloads WHERE id IN ({placeholders})", ids)
            return cur.rowcount if cur.rowcount is not None else 0

    def delete_all(self) -> int:
        """Clear the entire history (metadata only; files stay on disk)."""
        with db_session() as conn:
            cur = conn.execute("DELETE FROM downloads")
            return cur.rowcount if cur.rowcount is not None else 0

    def mark_interrupted(self, message: str = "Interrupted by application restart") -> int:
        now_statuses = ("Extracting", "Downloading", "Processing")
        placeholders = ",".join(["?"] * len(now_statuses))
        # Consistent ISO-8601 UTC timestamps (QUAL-04): datetime('now') emits a
        # different format than utc_now_iso() used everywhere else.
        updated_at = utc_now_iso()
        with db_session() as conn:
            cur = conn.execute(
                f"UPDATE downloads SET status = 'Failed', error_message = COALESCE(error_message, ?), "
                f"updated_at = ? WHERE status IN ({placeholders})",
                (message, updated_at, *now_statuses),
            )
            return cur.rowcount if cur.rowcount is not None else 0
