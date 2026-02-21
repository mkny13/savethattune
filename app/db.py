from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    show_date TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(request_id) REFERENCES requests(id)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_request(self, artist: str, title: str, show_date: str | None) -> tuple[int, str]:
        created = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO requests(artist,title,show_date,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (artist, title, show_date, "queued", created, created),
            )
            return int(cur.lastrowid), created

    def log_action(self, request_id: int, phase: str, status: str, details: dict | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO actions(request_id,phase,status,details_json,created_at) VALUES(?,?,?,?,?)",
                (request_id, phase, status, json.dumps(details or {}), now_iso()),
            )

    def set_status(self, request_id: int, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE requests SET status=?, updated_at=? WHERE id=?",
                (status, now_iso(), request_id),
            )

    def recent_requests(self, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, artist, title, show_date, status, created_at, updated_at FROM requests ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
