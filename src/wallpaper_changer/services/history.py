from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from wallpaper_changer.models import Wallpaper


@dataclass(frozen=True, slots=True)
class HistoryItem:
    row_id: int
    wallpaper_id: str
    url: str
    local_path: str
    previous_path: str
    title: str
    category: str
    applied_at: str
    success: bool
    monitor_id: str
    error: str


class HistoryRepository:
    def __init__(self, database: Path):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallpaper_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    local_path TEXT NOT NULL DEFAULT '',
                    previous_path TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    applied_at TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 1,
                    monitor_id TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_history_wallpaper ON history(wallpaper_id, success);
                CREATE INDEX IF NOT EXISTS idx_history_applied ON history(applied_at DESC);
                CREATE TABLE IF NOT EXISTS favorites (
                    wallpaper_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    thumbnail_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS blocked (
                    wallpaper_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );
                """
            )

    def record(
        self,
        wallpaper: Wallpaper,
        *,
        local_path: Path | None,
        previous_path: Path | None = None,
        success: bool,
        monitor_id: str = "",
        error: str = "",
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO history (
                    wallpaper_id, url, local_path, previous_path, title, category,
                    applied_at, success, monitor_id, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    wallpaper.id,
                    wallpaper.url,
                    str(local_path or ""),
                    str(previous_path or ""),
                    wallpaper.title,
                    wallpaper.category,
                    datetime.now(UTC).isoformat(),
                    1 if success else 0,
                    monitor_id,
                    error[:2000],
                ),
            )

    def recent(self, limit: int = 50, *, successful_only: bool = False) -> list[HistoryItem]:
        where = "WHERE success = 1" if successful_only else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM history {where} ORDER BY id DESC LIMIT ?",  # noqa: S608 - static clause
                (max(1, limit),),
            ).fetchall()
        return [self._history_item(row) for row in rows]

    def used_ids(self, limit: int = 5000) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT wallpaper_id FROM history WHERE success = 1 ORDER BY id DESC LIMIT ?",
                (max(1, limit),),
            ).fetchall()
        return {str(row[0]) for row in rows}

    def last_successful(self) -> HistoryItem | None:
        items = self.recent(1, successful_only=True)
        return items[0] if items else None

    def toggle_favorite(self, wallpaper: Wallpaper) -> bool:
        with self._lock, self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM favorites WHERE wallpaper_id = ?", (wallpaper.id,)
            ).fetchone()
            if exists:
                connection.execute("DELETE FROM favorites WHERE wallpaper_id = ?", (wallpaper.id,))
                return False
            connection.execute(
                """
                INSERT INTO favorites (wallpaper_id, url, title, category, thumbnail_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    wallpaper.id,
                    wallpaper.url,
                    wallpaper.title,
                    wallpaper.category,
                    wallpaper.thumbnail_url or "",
                    datetime.now(UTC).isoformat(),
                ),
            )
            return True

    def is_favorite(self, wallpaper_id: str) -> bool:
        with self._connect() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM favorites WHERE wallpaper_id = ?", (wallpaper_id,)
                ).fetchone()
                is not None
            )

    def favorites(self) -> list[Wallpaper]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM favorites ORDER BY created_at DESC").fetchall()
        return [
            Wallpaper(
                id=str(row["wallpaper_id"]),
                url=str(row["url"]),
                thumbnail_url=str(row["thumbnail_url"]) or None,
                title=str(row["title"]) or "Untitled",
                category=str(row["category"]) or "all",
                source="favorites",
            )
            for row in rows
        ]

    def block(self, wallpaper_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO blocked (wallpaper_id, created_at) VALUES (?, ?)",
                (wallpaper_id, datetime.now(UTC).isoformat()),
            )

    def blocked_ids(self) -> set[str]:
        with self._connect() as connection:
            return {str(row[0]) for row in connection.execute("SELECT wallpaper_id FROM blocked")}

    def trim(self, max_items: int) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                (max(20, max_items),),
            )

    def clear_history(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM history")

    def protected_paths(self, limit: int = 20) -> set[Path]:
        paths: set[Path] = set()
        for item in self.recent(limit, successful_only=True):
            if item.local_path:
                paths.add(Path(item.local_path))
            if item.previous_path:
                paths.add(Path(item.previous_path))
        return paths

    @staticmethod
    def _history_item(row: sqlite3.Row) -> HistoryItem:
        return HistoryItem(
            row_id=int(row["id"]),
            wallpaper_id=str(row["wallpaper_id"]),
            url=str(row["url"]),
            local_path=str(row["local_path"]),
            previous_path=str(row["previous_path"]),
            title=str(row["title"]),
            category=str(row["category"]),
            applied_at=str(row["applied_at"]),
            success=bool(row["success"]),
            monitor_id=str(row["monitor_id"]),
            error=str(row["error"]),
        )
