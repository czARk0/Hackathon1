"""
test_tools.py — Stage 3: Tool Function Tests

Tests each tool function independently against the seeded database.
Calls the REAL Resend API — no mocking.

Run after test_database.py has already seeded the DB, OR let this script
seed it fresh by calling init_db() + run_seed() at the top.
"""

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from database import get_connection, init_db
from seed import run_seed
from tools import (
    create_maintenance_ticket,
    get_equipment_history,
    notify_staff,
    verify_ticket,
)

PASS = "  PASS"
FAIL = "  FAIL"
SEP = "=" * 70


def check(label: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    msg = f"{tag}  {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return condition


def main() -> None:
    all_ok = True

    # ------------------------------------------------------------------
    # Ensure DB is initialised and seeded before any tool test
    # ------------------------------------------------------------------
    init_db()

    # Clear transient tables so tests always start from a known state
    # (tickets and agent_events are ephemeral; equipment/incidents/staff are stable seed data)
    with get_connection() as conn:
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM agent_events")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('tickets','agent_events')")
        conn.commit()
    print("Cleared tickets and agent_events tables for clean test run.")

    run_seed()


    # ===================================================================
    # TEST 1 — get_equipment_history
    # ===================================================================
    print(SEP)
    print("TEST 1 — get_equipment_history('Lab 3', 'Projector')")
    print()

    result = get_equipment_history("Lab 3", "Projector")
    print(f"  incident_count = {result['incident_count']}")
    print("  incidents:")
    for inc in result["incidents"]:
        print(f"    date={inc['date']}  description={inc['description']}  resolution={inc['resolution']}")

    all_ok &= check("incident_count == 2", result["incident_count"] == 2,
                    f"got {result['incident_count']}")
    all_ok &= check("incidents list has 2 items", len(result["incidents"]) == 2)

    # ===================================================================
    # TEST 2 — create_maintenance_ticket (new ticket)
    # ===================================================================
    print()
    print(SEP)
    print("TEST 2 — create_maintenance_ticket (new ticket)")
    print()

    t2 = create_maintenance_ticket("Lab 3", "projector not working", "HIGH")
    print(f"  result: {t2}")

    all_ok &= check("ticket created (not duplicate)", t2["duplicate"] is False)
    all_ok &= check("status == 'CREATED'", t2["status"] == "CREATED")
    all_ok &= check("ticket_id is set", isinstance(t2["ticket_id"], int) and t2["ticket_id"] > 0,
                    f"got {t2['ticket_id']}")
    all_ok &= check("priority == 'HIGH'", t2["priority"] == "HIGH")

    first_ticket_id = t2["ticket_id"]

    # Confirm exactly 1 open ticket in DB for this room+issue
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE room='Lab 3' AND issue='projector not working' AND status!='resolved'",
        ).fetchone()[0]
    all_ok &= check("DB has exactly 1 open ticket for this issue", count == 1, f"got {count}")

    # ===================================================================
    # TEST 3 — create_maintenance_ticket again (duplicate detection)
    # ===================================================================
    print()
    print(SEP)
    print("TEST 3 -- create_maintenance_ticket again (same room+issue -> duplicate)")
    print()

    t3 = create_maintenance_ticket("Lab 3", "projector not working", "HIGH")
    print(f"  result: {t3}")

    all_ok &= check("duplicate == True", t3["duplicate"] is True)
    all_ok &= check("status == 'EXISTING'", t3["status"] == "EXISTING")
    all_ok &= check("same ticket_id returned",
                    t3["ticket_id"] == first_ticket_id,
                    f"got {t3['ticket_id']} expected {first_ticket_id}")
    all_ok &= check("priority escalated to HIGH", t3["priority"] == "HIGH")

    # Confirm still only 1 open ticket in DB
    with get_connection() as conn:
        count2 = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE room='Lab 3' AND issue='projector not working' AND status!='resolved'",
        ).fetchone()[0]
    all_ok &= check("DB still has exactly 1 open ticket (no duplicate created)", count2 == 1, f"got {count2}")

    # ===================================================================
    # TEST 4 — notify_staff (real Resend email)
    # ===================================================================
    print()
    print(SEP)
    print("TEST 4 — notify_staff (real email via Resend)")
    print()

    tech_email = os.getenv("TECH_EMAIL")
    if not tech_email:
        print("  SKIP  TECH_EMAIL not set — cannot test email")
        all_ok = False
    else:
        message = (
            f"Maintenance ticket #{first_ticket_id}: Projector in Lab 3 is not working. "
            f"Priority: HIGH. Please attend before 10 AM tomorrow."
        )
        try:
            email_result = notify_staff(tech_email, message, first_ticket_id)
            print(f"  result: {email_result}")
            all_ok &= check("email success == True", email_result["success"] is True)
            all_ok &= check("status == 'sent'", email_result["status"] == "sent")
            all_ok &= check("ticket_id matches", email_result["ticket_id"] == first_ticket_id)
            all_ok &= check("message_id returned", bool(email_result.get("message_id")),
                            f"got '{email_result.get('message_id')}'")
        except Exception as exc:
            print(f"  ERROR  notify_staff raised: {exc}")
            all_ok = False

    # ===================================================================
    # TEST 5 — verify_ticket
    # ===================================================================
    print()
    print(SEP)
    print("TEST 5 — verify_ticket")
    print()

    # Insert the agent_events record for the notify_staff success
    # (simulate what the agent loop will write in Prompt 4)
    now_ts = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_events (task_id, event_type, tool, status, result, timestamp)
            VALUES (?, 'tool_call', 'notify_staff', 'success', 'email sent', ?)
            """,
            (first_ticket_id, now_ts),
        )
        conn.commit()
    print(f"  Inserted agent_events row: task_id={first_ticket_id}, tool=notify_staff, status=success")

    # Now verify the real ticket
    v = verify_ticket(first_ticket_id)
    print(f"  verify_ticket({first_ticket_id}): {v}")
    all_ok &= check("ticket_exists == True", v["ticket_exists"] is True)
    all_ok &= check("priority_set  == True", v["priority_set"] is True)
    all_ok &= check("staff_notified == True", v["staff_notified"] is True)

    # Also verify a nonexistent ticket
    fake_id = 99999
    v_missing = verify_ticket(fake_id)
    print(f"  verify_ticket({fake_id}): {v_missing}")
    all_ok &= check("ticket_exists == False for nonexistent id",
                    v_missing["ticket_exists"] is False)

    # ===================================================================
    # Final result
    # ===================================================================
    print()
    print(SEP)
    if all_ok:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
