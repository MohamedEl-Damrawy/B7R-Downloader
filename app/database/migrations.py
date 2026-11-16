"""Simple schema migrations."""

from __future__ import annotations

from datetime import datetime, timezone

from app.database.connection import db_session
from app.database.schema import SCHEMA_STATEMENTS, SCHEMA_VERSION


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_current_version(conn) -> int:
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    if not row or row["v"] is None:
        # schema_version table may exist but empty
        try:
            row2 = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
            return int(row2["version"]) if row2 else 0
        except Exception:
            return 0
    return int(row["v"])


def apply_migrations() -> None:
    with db_session() as conn:
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)
        # Ensure schema_version table exists before querying in edge cases
        try:
            cur = conn.execute("SELECT 1 FROM schema_version LIMIT 1")
            cur.fetchone()
        except Exception:
            conn.execute(SCHEMA_STATEMENTS[0])
        # PERF-04 v2: persist playlist_items on downloads so batch tasks can be
        # retried exactly (without it, retrying a playlist-URL task would risk
        # re-downloading the whole playlist).
        if get_current_version(conn) < 2 and not _column_exists(conn, "downloads", "playlist_items"):
            conn.execute("ALTER TABLE downloads ADD COLUMN playlist_items TEXT")
        row = conn.execute("SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO schema_version(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utc_now()),
            )


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)
