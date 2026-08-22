"""
database.py — Stage 2: SQLite Database Initialization

Provides a single init_db() function that creates all tables
if they do not already exist. Safe to run repeatedly.

No agent logic, no tool logic, no FastAPI here.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "campus_commander.db"


def get_connection() -> sqlite3.Connection:
    """
    Return a new SQLite connection in autocommit mode (isolation_level=None).

    isolation_level=None disables Python's implicit transaction management
    so every statement is committed immediately and readers always see the
    latest WAL data without holding stale transaction snapshots.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent readers during writes
    conn.execute("PRAGMA busy_timeout=5000")  # wait up to 5s if DB is locked
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def init_db() -> None:
    """
    Create all required tables if they do not already exist.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS equipment (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT,
            room             TEXT,
            status           TEXT,
            last_maintenance TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER,
            description  TEXT,
            date         TEXT,
            status       TEXT,
            resolution   TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS staff (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT,
            role  TEXT,
            email TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            room             TEXT,
            issue            TEXT,
            priority         TEXT,
            assigned_staff_id INTEGER,
            reported_by_id   INTEGER,
            status           TEXT,
            created_at       TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER,
            event_type TEXT,
            tool       TEXT,
            status     TEXT,
            result     TEXT,
            timestamp  TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            status     TEXT    NOT NULL DEFAULT 'RUNNING',
            goal       TEXT,
            outcome    TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER,
            memory_type TEXT,
            key         TEXT,
            value       TEXT,
            created_at  TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reporters (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            role  TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """,
    ]

    with get_connection() as conn:
        for stmt in ddl_statements:
            conn.execute(stmt)


        # Defensive migration for existing databases missing reported_by_id column
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN reported_by_id INTEGER")
        except Exception:
            pass

        conn.commit()
