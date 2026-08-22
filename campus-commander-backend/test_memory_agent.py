"""
test_memory_agent.py -- Stage 7: Agent Memory Integration Test

Tests:
  1. First Run:
     - Agent retrieves existing Lab 3 memories (0 initial)
     - Logs 'memory_retrieval' event
     - Executes full workflow (HIGH priority, ticket, email, verification)
     - Saves 'task_outcome' memory upon completion
     - Logs 'memory_save' event
     - Honest outcome (no claim of physical repair)

  2. Second Run:
     - Agent retrieves memory created during First Run
     - Logs 'memory_retrieval' event showing retrieved context (count >= 1)
     - Full workflow completes normally
     - Saves second memory
     - Validates SQLite memories table contains multiple historical memories for Lab 3
"""

import json
import sys
from database import get_connection, init_db
from seed import run_seed
from agent import run_agent
from memory import retrieve_memories

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
    print("STAGE 7: AGENT MEMORY INTEGRATION TEST")
    print(SEP)

    # Clean DB setup
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM memories")
        conn.execute("DELETE FROM agent_events")
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM incidents")
        conn.execute("DELETE FROM equipment")
        conn.execute("DELETE FROM staff")
        try:
            conn.execute("DELETE FROM tasks")
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass
    run_seed()
    print("Clean database initialized and seeded.")
    print()

    # ===================================================================
    # EXECUTION 1 -- First Run
    # ===================================================================
    print(SEP)
    print("EXECUTION 1 -- Initial Run (Cold memory state)")
    print(SEP)

    goal_1 = (
        "The projector in Lab 3 isn't working. "
        "I have my project presentation tomorrow at 10 AM. Please handle it."
    )
    outcome_1 = run_agent(goal_1, task_id=1)

    print()
    print("[Run 1] Final Outcome:")
    print(json.dumps(outcome_1, indent=2))
    print()

    check("Run 1 status == COMPLETED", outcome_1.get("status") == "COMPLETED")
    check("Run 1 priority == HIGH", outcome_1.get("priority") == "HIGH")
    check("Run 1 technician_notified == True", outcome_1.get("technician_notified") is True)

    msg_1 = outcome_1.get("message", "").lower()
    check("Run 1 message does NOT claim physical repair",
          "repaired" not in msg_1 and "fixed the projector" not in msg_1)

    # Inspect Run 1 events
    with get_connection() as conn:
        events_1 = conn.execute(
            "SELECT * FROM agent_events WHERE task_id = 1 ORDER BY id ASC"
        ).fetchall()

    print("[Run 1] Chronological Events:")
    for e in events_1:
        print(f"  [{e['id']:>2}] type={e['event_type']:<18} tool={str(e['tool']):<24} status={e['status']}")

    event_types_1 = [e["event_type"] for e in events_1]
    check("Run 1 has 'memory_retrieval' event", "memory_retrieval" in event_types_1)
    check("Run 1 has 'memory_save' event", "memory_save" in event_types_1)

    # Inspect SQLite memories table after Run 1
    mems_1 = retrieve_memories("Lab 3")
    print(f"\n[Run 1] SQLite memories for 'Lab 3': {len(mems_1)} found")
    for m in mems_1:
        print(f"  ID #{m['id']} (task {m['task_id']}): {m['value']}")

    check("At least 1 memory saved in SQLite for 'Lab 3'", len(mems_1) >= 1)
    if mems_1:
        check("Saved memory contains ticket info", "Ticket" in mems_1[0]["value"])
        check("Saved memory contains priority", "Priority: HIGH" in mems_1[0]["value"])

    # ===================================================================
    # EXECUTION 2 -- Second Run (Retrieves memory from Run 1)
    # ===================================================================
    print()
    print(SEP)
    print("EXECUTION 2 -- Second Run (Warm memory state - retrieving prior context)")
    print(SEP)

    goal_2 = (
        "The projector in Lab 3 is malfunctioning again. "
        "Need assistance for our presentation tomorrow morning."
    )
    outcome_2 = run_agent(goal_2, task_id=2)

    print()
    print("[Run 2] Final Outcome:")
    print(json.dumps(outcome_2, indent=2))
    print()

    check("Run 2 status == COMPLETED", outcome_2.get("status") == "COMPLETED")
    check("Run 2 priority == HIGH", outcome_2.get("priority") == "HIGH")
    check("Run 2 technician_notified == True", outcome_2.get("technician_notified") is True)

    # Inspect Run 2 events
    with get_connection() as conn:
        events_2 = conn.execute(
            "SELECT * FROM agent_events WHERE task_id = 2 ORDER BY id ASC"
        ).fetchall()

    print("[Run 2] Chronological Events:")
    retrieval_event_2 = None
    for e in events_2:
        print(f"  [{e['id']:>2}] type={e['event_type']:<18} tool={str(e['tool']):<24} status={e['status']}")
        if e["event_type"] == "memory_retrieval":
            retrieval_event_2 = e

    check("Run 2 has 'memory_retrieval' event", retrieval_event_2 is not None)
    if retrieval_event_2:
        res_data = json.loads(retrieval_event_2["result"])
        print(f"  [Run 2] Memory retrieval result payload: {res_data}")
        check("Run 2 memory retrieval count >= 1", res_data.get("count", 0) >= 1, f"count={res_data.get('count')}")
        check("Run 2 memory retrieval contains prior Run 1 context",
              any("Ticket" in m["value"] for m in res_data.get("memories", [])))

    event_types_2 = [e["event_type"] for e in events_2]
    check("Run 2 has 'memory_save' event", "memory_save" in event_types_2)

    # Inspect SQLite memories table after Run 2
    mems_2 = retrieve_memories("Lab 3")
    print(f"\n[Run 2] SQLite memories for 'Lab 3': {len(mems_2)} found")
    for m in mems_2:
        print(f"  ID #{m['id']} (task {m['task_id']}): {m['value']}")

    check("SQLite contains 2 memories for 'Lab 3'", len(mems_2) == 2, f"got {len(mems_2)}")

    print()
    print(SEP)
    if all_ok:
        print("ALL MEMORY AGENT INTEGRATION TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE MEMORY AGENT INTEGRATION TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
