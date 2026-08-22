"""
test_agent.py -- Stage 4: Full Agent Loop Test

Runs the locked demo scenario end-to-end and prints:
1. Complete agent_events in chronological order
2. Final outcome dictionary
3. Final ticket row from SQLite
"""

import json
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from database import get_connection, init_db
from seed import run_seed
from agent import run_agent

SEP = "=" * 70
TASK_ID = 42  # arbitrary test task ID


def main() -> None:
    # ------------------------------------------------------------------
    # 0. Fresh database state
    # ------------------------------------------------------------------
    print(SEP)
    print("SETUP -- initialising DB and seeding...")
    init_db()

    # Wipe ALL tables so every run starts from a guaranteed clean state
    with get_connection() as conn:
        conn.execute("DELETE FROM agent_events")
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM incidents")
        conn.execute("DELETE FROM equipment")
        conn.execute("DELETE FROM staff")
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
    print("Cleared all tables for clean run.")

    run_seed()

    print()

    # ------------------------------------------------------------------
    # 1. Run the agent
    # ------------------------------------------------------------------
    print(SEP)
    print("RUNNING AGENT...")
    print()

    goal = (
        "The projector in Lab 3 isn't working. "
        "I have my project presentation tomorrow at 10 AM. Please handle it."
    )

    outcome = run_agent(goal, task_id=TASK_ID)

    # ------------------------------------------------------------------
    # 2. Print agent_events in chronological order
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("AGENT EVENT LOG (chronological):")
    print()

    with get_connection() as conn:
        events = conn.execute(
            """
            SELECT id, event_type, tool, status, result, timestamp
            FROM agent_events
            WHERE task_id = ?
            ORDER BY id ASC
            """,
            (TASK_ID,),
        ).fetchall()

    for evt in events:
        print(f"  [{evt['id']:>2}] type={evt['event_type']:<14} "
              f"tool={str(evt['tool']):<28} "
              f"status={evt['status']}")
        # Pretty-print JSON result if parseable
        raw = evt["result"] or ""
        try:
            parsed = json.loads(raw)
            print(f"       result: {json.dumps(parsed)}")
        except (json.JSONDecodeError, TypeError):
            print(f"       result: {raw}")
        print(f"       ts:     {evt['timestamp']}")
        print()

    # ------------------------------------------------------------------
    # 3. Print final outcome
    # ------------------------------------------------------------------
    print(SEP)
    print("FINAL OUTCOME:")
    print()
    print(json.dumps(outcome, indent=2))
    print()

    # ------------------------------------------------------------------
    # 4. Print final ticket row
    # ------------------------------------------------------------------
    ticket_id = outcome.get("ticket_id")
    print(SEP)
    print(f"FINAL TICKET ROW (ticket_id={ticket_id}):")
    print()

    if ticket_id is not None:
        with get_connection() as conn:
            ticket = conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
        if ticket:
            for key in ticket.keys():
                print(f"  {key:<20} = {ticket[key]}")
        else:
            print(f"  WARNING: No ticket found for id={ticket_id}")
    else:
        print("  No ticket_id in outcome.")

    # ------------------------------------------------------------------
    # 5. Pass/Fail assertions
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("ASSERTIONS:")

    all_ok = True

    def check(label, cond, detail=""):
        nonlocal all_ok
        tag = "  PASS" if cond else "  FAIL"
        msg = f"{tag}  {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        if not cond:
            all_ok = False

    # Event sequence checks
    event_types = [(e["event_type"], e["tool"]) for e in events]
    tools_in_order = [e["tool"] for e in events if e["event_type"] == "tool_call"]

    check("at least 1 get_equipment_history event",
          any(t == "get_equipment_history" for _, t in event_types))
    check("determine_priority logged as decision (tool=None)",
          any(et == "decision" and t is None for et, t in event_types))
    check("create_maintenance_ticket event present",
          any(t == "create_maintenance_ticket" for _, t in event_types))
    check("notify_staff event present",
          any(t == "notify_staff" for _, t in event_types))
    check("verify_ticket event present",
          any(t == "verify_ticket" for _, t in event_types))

    # Outcome checks
    check("status == COMPLETED", outcome["status"] == "COMPLETED",
          f"got '{outcome['status']}'")
    check("priority == HIGH", outcome["priority"] == "HIGH",
          f"got '{outcome['priority']}'")
    check("technician_notified == True", outcome["technician_notified"] is True)
    check("ticket_id is set", isinstance(outcome.get("ticket_id"), int))

    # Verification checks
    v = outcome.get("verification", {})
    check("verification.ticket_exists == True", v.get("ticket_exists") is True)
    check("verification.priority_set  == True", v.get("priority_set") is True)
    check("verification.staff_notified == True", v.get("staff_notified") is True)

    # Honesty check -- outcome must NOT claim physical repair
    msg_lower = outcome.get("message", "").lower()
    check("message does NOT claim physical repair",
          "repaired" not in msg_lower and "fixed the projector" not in msg_lower)
    check("message mentions ticket", "ticket" in msg_lower)

    print()
    print(SEP)
    if all_ok:
        print("ALL ASSERTIONS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE ASSERTIONS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
