"""SQLite connection + schema for the decision audit log.

Zero-config: the database file is created on first use at the path given by
``AGRI_AI_DB_PATH`` (default ``data/agri.db``).  SQLite is part of the Python
standard library so no extra dependency is required.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_DB_PATH = Path(os.environ.get("AGRI_AI_DB_PATH", "data/agri.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT    NOT NULL,
    greenhouse_id      TEXT,
    crop               TEXT,
    intent             TEXT,
    query              TEXT    NOT NULL,
    decision           TEXT,
    confidence         REAL,
    risk_level         TEXT,
    judge_mode         TEXT,
    need_human_review  INTEGER DEFAULT 0,
    action_plan        TEXT,
    traces             TEXT,
    debate             TEXT,
    judge_analysis     TEXT,
    feedback           TEXT,
    feedback_note      TEXT,
    feedback_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at DESC);
"""

def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Add feedback columns to pre-existing databases (idempotent)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(decisions)").fetchall()}
    for col, decl in [("feedback", "TEXT"), ("feedback_note", "TEXT"), ("feedback_at", "TEXT")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} {decl}")


def get_connection() -> sqlite3.Connection:
    """Return a connection with the schema initialised (idempotent)."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    _ensure_columns(conn)
    conn.commit()
    return conn

def db_path() -> Path:
    return _DB_PATH
