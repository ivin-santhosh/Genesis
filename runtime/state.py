"""Durable SQLite checkpoint storage for deterministic local tasks."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any

class CheckpointStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        self.connection.commit()

    def save(self, task_id: str, state: dict[str, Any]) -> None:
        if not task_id or len(task_id) > 128:
            raise ValueError("Invalid task ID")
        data = json.dumps(state, ensure_ascii=False, allow_nan=False)
        with self.connection:
            self.connection.execute(
                """INSERT INTO tasks (id,status,payload) VALUES (?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                payload=excluded.payload,updated_at=CURRENT_TIMESTAMP""",
                (task_id, state["status"], data))

    def load(self, task_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.connection.close()
