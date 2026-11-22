"""Tiny SQLite layer that stores every coaching session so you can track your progress."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("PROMPT_COACH_DB", Path(__file__).resolve().parent.parent / "prompt_coach.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                original_prompt TEXT NOT NULL,
                overall_score INTEGER NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )


def save_session(original_prompt: str, report: dict) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (created_at, original_prompt, overall_score, report_json) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                original_prompt,
                report["overall_score"],
                json.dumps(report),
            ),
        )
        return cur.lastrowid


def list_sessions(limit: int = 50) -> list:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "original_prompt": r["original_prompt"],
            "overall_score": r["overall_score"],
            "report": json.loads(r["report_json"]),
        }
        for r in rows
    ]


def delete_session(session_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0
