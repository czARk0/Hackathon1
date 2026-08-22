"""
test_memory.py -- Stage 7: Persistent Memory Unit Tests

Tests:
  1. Save memory -> verifies SQLite storage
  2. Retrieve memory -> verifies retrieval by key
  3. Isolation -> verifies non-matching keys return empty results
  4. Persistence -> closes connection and verifies memory in a new connection/process
"""

import sys
from database import get_connection, init_db
from memory import retrieve_memories, save_memory

SEP = "=" * 70
PASS = "  PASS"
FAIL = "  FAIL"

all_ok = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_ok
    tag = PASS if cond else FAIL
    msg = f"{tag}  {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    if not cond:
        all_ok = False
    return cond


def main() -> None:
    global all_ok
    print(SEP)
    print("STAGE 7: PERSISTENT MEMORY UNIT TESTS")
    print(SEP)

    # Initialize DB & clean up memories table for test isolation
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM memories")
        try:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'memories'")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Test 1 -- Save
    # ------------------------------------------------------------------
    print()
    print("TEST 1 -- Save memory")
    mem_saved = save_memory(
        task_id=100,
        memory_type="task_outcome",
        key="Lab 3",
        value="Projector issue. Ticket #100. Technician notified.",
    )
    print(f"  save_memory returned: {mem_saved}")
    check("save_memory returns dict", isinstance(mem_saved, dict))
    check("save_memory returns id", isinstance(mem_saved.get("id"), int))
    check("save_memory returns key='Lab 3'", mem_saved.get("key") == "Lab 3")

    # Direct SQLite query to verify storage
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (mem_saved["id"],)
        ).fetchone()

    check("Memory row exists in SQLite", row is not None)
    if row:
        check("SQLite row task_id == 100", row["task_id"] == 100)
        check("SQLite row memory_type == 'task_outcome'", row["memory_type"] == "task_outcome")
        check("SQLite row key == 'Lab 3'", row["key"] == "Lab 3")
        check("SQLite row value matches", "Ticket #100" in row["value"])
        check("SQLite row created_at is populated", bool(row["created_at"]))

    # ------------------------------------------------------------------
    # Test 2 -- Retrieve
    # ------------------------------------------------------------------
    print()
    print("TEST 2 -- Retrieve memory")
    memories = retrieve_memories("Lab 3")
    print(f"  retrieve_memories('Lab 3') returned: {memories}")
    check("retrieve_memories returns list", isinstance(memories, list))
    check("retrieve_memories returns at least 1 item", len(memories) >= 1)
    if memories:
        check("First memory key matches", memories[0]["key"] == "Lab 3")
        check("First memory value matches", "Ticket #100" in memories[0]["value"])

    # Test case-insensitivity
    memories_lower = retrieve_memories("lab 3")
    check("Case-insensitive lookup ('lab 3') finds memory", len(memories_lower) >= 1)

    # ------------------------------------------------------------------
    # Test 3 -- Isolation
    # ------------------------------------------------------------------
    print()
    print("TEST 3 -- Isolation")
    memories_other = retrieve_memories("Lab 99")
    print(f"  retrieve_memories('Lab 99') returned: {memories_other}")
    check("retrieve_memories('Lab 99') returns empty list", len(memories_other) == 0)
    check("Lab 3 memory is NOT leaked for Lab 99 query",
          not any(m["key"] == "Lab 3" for m in memories_other))

    # ------------------------------------------------------------------
    # Test 4 -- Persistence across fresh connections
    # ------------------------------------------------------------------
    print()
    print("TEST 4 -- Persistence across fresh connection")
    # Fresh connection query
    fresh_conn = get_connection()
    try:
        fresh_rows = fresh_conn.execute(
            "SELECT * FROM memories WHERE LOWER(key) = 'lab 3'"
        ).fetchall()
        check("Memory row still present in fresh connection", len(fresh_rows) >= 1)
    finally:
        fresh_conn.close()

    # Call retrieve_memories again
    persisted_memories = retrieve_memories("Lab 3")
    check("retrieve_memories still returns saved memory", len(persisted_memories) >= 1)

    print()
    print(SEP)
    if all_ok:
        print("ALL MEMORY UNIT TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE MEMORY UNIT TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
