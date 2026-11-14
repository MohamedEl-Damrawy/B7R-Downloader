"""Settings repository."""

from __future__ import annotations

from typing import Optional

from app.database.connection import db_session


class SettingsRepository:
    def get(self, key: str) -> Optional[str]:
        with db_session() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row else None

    def set(self, key: str, value: str) -> None:
        with db_session() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def get_all(self) -> dict[str, str]:
        with db_session() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {str(r["key"]): str(r["value"]) for r in rows}
