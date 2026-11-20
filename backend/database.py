import sqlite3
from contextlib import closing, contextmanager
from functools import lru_cache
from pathlib import Path

from backend.config import ROOT


SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    match_id TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    venue_name TEXT NOT NULL,
    venue_address TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS plans_start ON plans(start_at, id);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    conditions TEXT NOT NULL,
    summary TEXT NOT NULL,
    permissions TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_events (
    session_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    node_name TEXT,
    tool_name TEXT,
    payload TEXT NOT NULL,
    PRIMARY KEY (session_id, run_id, sequence_no)
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self, *, write=False):
        with closing(sqlite3.connect(self.path, timeout=2)) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                if write:
                    conn.execute('BEGIN IMMEDIATE')
                yield conn


@lru_cache
def get_database() -> Database:
    return Database(ROOT / 'data' / 'kbl-go.sqlite3')
