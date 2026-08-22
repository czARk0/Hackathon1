"""
memory.py -- Stage 7: Persistent Agent Memory

Provides:
  - save_memory(task_id, memory_type, key, value) -> dict
  - retrieve_memories(key, limit=5) -> list

Persists contextual agent memory in SQLite `memories` table.
Does not hard-code demo memories.
"""

from datetime import datetime, timezone

from database import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_memory(
    task_id: int,
    memory_type: str,
    key: str,
    value: str,
) -> dict:
    """
    Persist a new memory entry into the SQLite memories table.

    Parameters
    ----------
    task_id : int
        The task ID associated with this memory.
    memory_type : str
        Category of the memory (e.g. 'task_outcome', 'preference').
    key : str
        Lookup key (e.g. room name like 'Lab 3').
    value : str
        Structured text content of the memory.

    Returns
    -------
    dict
        Details of the saved memory record.
    """
    created_at = _now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO memories (task_id, memory_type, key, value, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, memory_type, key, value, created_at),
        )
        memory_id = cursor.lastrowid

    return {
        "id": memory_id,
        "task_id": task_id,
        "memory_type": memory_type,
        "key": key,
        "value": value,
        "created_at": created_at,
    }


def retrieve_memories(
    key: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve the most recent memories matching key (case-insensitive).

    Parameters
    ----------
    key : str
        Lookup key to match against memories.key (e.g. 'Lab 3').
    limit : int
        Maximum number of memories to return (default: 5).

    Returns
    -------
    list[dict]
        List of memory dicts in reverse chronological order (newest first).
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, task_id, memory_type, key, value, created_at
            FROM memories
            WHERE LOWER(key) = LOWER(?)
            ORDER BY id DESC
            LIMIT ?
            """,
            (key, limit),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "task_id": row["task_id"],
            "memory_type": row["memory_type"],
            "key": row["key"],
            "value": row["value"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
