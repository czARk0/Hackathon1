"""
test_failure.py -- Stage 6: Failure Handling + Exactly One Retry Test

Executes:
  TEST A: SIMULATE_EMAIL_FAILURE=true
          - Validates intentional failure on notify_staff
          - Validates exactly 1 retry occurred (2 notify attempts total, no 3rd attempt)
          - Validates ticket status updated to 'awaiting manual follow-up'
          - Validates technician_notified == False and honest failure message

  TEST B: SIMULATE_EMAIL_FAILURE=false
          - Runs exact same scenario again
          - Validates existing ticket is reused (no duplicate open ticket created)
          - Validates email succeeds
          - Validates verify_ticket confirms staff_notified == True
          - Validates final status == COMPLETED
"""

import json
import os
import subprocess
import sys
import time

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config & Setup
# ---------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000"
GOAL = (
    "The projector in Lab 3 isn't working. "
    "I have my project presentation tomorrow at 10 AM. Please handle it."
)
SERVER_STARTUP_WAIT = 3.0
MAX_WAIT_SECONDS = 60

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


def set_simulate_email_failure(value: str) -> None:
    """Update both os.environ and the .env file on disk."""
    os.environ["SIMULATE_EMAIL_FAILURE"] = value
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(env_path, "w", encoding="utf-8") as f:
            found = False
            for line in lines:
                if line.startswith("SIMULATE_EMAIL_FAILURE="):
                    f.write(f"SIMULATE_EMAIL_FAILURE={value}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"SIMULATE_EMAIL_FAILURE={value}\n")


def ensure_server() -> subprocess.Popen | None:
    """Check if server is already running, or start a new subprocess."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=1)
        if r.status_code == 200:
            print("[test] Connected to already-running FastAPI server.")
            return None
    except requests.exceptions.ConnectionError:
        pass

    print("[test] Starting uvicorn server in background subprocess...")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "warning",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + SERVER_STARTUP_WAIT + 10
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=1)
            if r.status_code == 200:
                print(f"[test] Server ready after {SERVER_STARTUP_WAIT}s.")
                return proc
        except requests.exceptions.ConnectionError:
            time.sleep(0.3)
    proc.terminate()
    raise RuntimeError("Server failed to start in time.")


def poll_task_completion(task_id: int) -> dict:
    """Poll GET /agent/task/{task_id} until terminal state."""
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/agent/task/{task_id}", timeout=5)
        task_data = r.json()
        status = task_data.get("status")
        if status in ("COMPLETED", "FAILED", "NOTIFICATION_FAILED", "NEEDS_HUMAN_INTERVENTION"):
            return task_data
        time.sleep(1.0)
    raise TimeoutError(f"Task {task_id} did not complete within {MAX_WAIT_SECONDS}s.")


def get_task_events(task_id: int) -> list[dict]:
    """Fetch events from GET /agent/task/{task_id}/events."""
    r = requests.get(f"{BASE_URL}/agent/task/{task_id}/events", timeout=5)
    return r.json().get("events", [])


# ---------------------------------------------------------------------------
# Main Test Routine
# ---------------------------------------------------------------------------

def main() -> None:
    global all_ok
    from database import get_connection, init_db
    from seed import run_seed

    # 1. Clean DB init and seed
    print(SEP)
    print("SETUP -- Resetting database and seeding fresh demo data...")
    init_db()
    with get_connection() as conn:
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
    print("Database reset complete.")
    print(SEP)

    proc = ensure_server()

    try:
        # ===================================================================
        # TEST A -- Intentional Email Failure & Exactly One Retry
        # ===================================================================
        print()
        print(SEP)
        print("TEST A -- Failure Path (SIMULATE_EMAIL_FAILURE=true)")
        print(SEP)

        set_simulate_email_failure("true")

        print("[TEST A] Submitting goal via POST /agent/run...")
        resp_a = requests.post(f"{BASE_URL}/agent/run", json={"goal": GOAL, "reporter_id": 1}, timeout=10)
        check("POST /agent/run returned 202", resp_a.status_code == 202)
        task_id_a = resp_a.json().get("task_id")
        check("task_id returned", isinstance(task_id_a, int), f"task_id={task_id_a}")

        print(f"[TEST A] Polling task #{task_id_a} for completion...")
        task_a = poll_task_completion(task_id_a)
        outcome_a = task_a.get("outcome") or {}

        print()
        print("[TEST A] Final Task Response:")
        print(json.dumps(task_a, indent=2))
        print()

        # Outcome validations
        check("Task status indicates notification failure",
              task_a.get("status") in ("NOTIFICATION_FAILED", "FAILED"),
              f"got '{task_a.get('status')}'")
        check("outcome.technician_notified == False",
              outcome_a.get("technician_notified") is False)
        ticket_id_a = outcome_a.get("ticket_id")
        check("Ticket ID returned", isinstance(ticket_id_a, int), f"ticket_id={ticket_id_a}")

        msg_a = outcome_a.get("message", "").lower()
        check("Outcome message mentions retry/failed",
              "failed" in msg_a or "notification failed" in msg_a)
        check("Outcome message mentions manual follow-up",
              "manual follow-up" in msg_a)
        check("Outcome does NOT falsely claim technician notified",
              "technician notified" not in msg_a)
        check("Outcome does NOT claim projector repaired",
              "repaired" not in msg_a and "fixed" not in msg_a)

        # Inspect events in DB
        events_a = get_task_events(task_id_a)
        print("[TEST A] Event Log:")
        notify_events_a = []
        for evt in events_a:
            print(f"  [{evt['id']:>2}] type={evt['event_type']:<12} "
                  f"tool={str(evt['tool']):<28} status={evt['status']}")
            if evt["tool"] == "notify_staff":
                notify_events_a.append(evt)

        print()
        check("Exactly 2 notification attempts in events (attempt 1 + exactly 1 retry)",
              len(notify_events_a) == 2,
              f"got {len(notify_events_a)} attempts")
        check("Attempt 1 status == failed",
              len(notify_events_a) >= 1 and notify_events_a[0]["status"] == "failed")
        check("Attempt 2 (retry) status == failed",
              len(notify_events_a) >= 2 and notify_events_a[1]["status"] == "failed")
        check("No 3rd notify attempt occurred",
              len(notify_events_a) <= 2)

        # Inspect SQLite tickets table
        with get_connection() as conn:
            ticket_row_a = conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id_a,)
            ).fetchone()

        print()
        print(f"[TEST A] SQLite Ticket #{ticket_id_a} Row:")
        if ticket_row_a:
            for k in ticket_row_a.keys():
                print(f"  {k:<20} = {ticket_row_a[k]}")
            check("Ticket status in SQLite == 'awaiting manual follow-up'",
                  ticket_row_a["status"] == "awaiting manual follow-up",
                  f"got '{ticket_row_a['status']}'")
            check("Ticket priority in SQLite == 'HIGH'",
                  ticket_row_a["priority"] == "HIGH",
                  f"got '{ticket_row_a['priority']}'")
        else:
            check("Ticket exists in SQLite", False, "Ticket row not found")

        # ===================================================================
        # TEST B -- Successful Second Run & Duplicate Ticket Safety
        # ===================================================================
        print()
        print(SEP)
        print("TEST B -- Success Path & Duplicate Safety (SIMULATE_EMAIL_FAILURE=false)")
        print(SEP)

        set_simulate_email_failure("false")

        print("[TEST B] Submitting same goal via POST /agent/run...")
        resp_b = requests.post(f"{BASE_URL}/agent/run", json={"goal": GOAL, "reporter_id": 1}, timeout=10)
        check("POST /agent/run returned 202", resp_b.status_code == 202)
        task_id_b = resp_b.json().get("task_id")
        check("task_id returned", isinstance(task_id_b, int), f"task_id={task_id_b}")

        print(f"[TEST B] Polling task #{task_id_b} for completion...")
        task_b = poll_task_completion(task_id_b)
        outcome_b = task_b.get("outcome") or {}

        print()
        print("[TEST B] Final Task Response:")
        print(json.dumps(task_b, indent=2))
        print()

        # Outcome validations
        check("Task status == COMPLETED",
              task_b.get("status") == "COMPLETED",
              f"got '{task_b.get('status')}'")
        check("outcome.priority == HIGH",
              outcome_b.get("priority") == "HIGH",
              f"got '{outcome_b.get('priority')}'")
        check("outcome.technician_notified == True",
              outcome_b.get("technician_notified") is True)
        ticket_id_b = outcome_b.get("ticket_id")
        check("Ticket ID matches existing ticket (reused, no duplicate created)",
              ticket_id_b == ticket_id_a,
              f"ticket_id_b={ticket_id_b} ticket_id_a={ticket_id_a}")

        verif_b = outcome_b.get("verification") or {}
        check("verification.ticket_exists == True", verif_b.get("ticket_exists") is True)
        check("verification.priority_set  == True", verif_b.get("priority_set") is True)
        check("verification.staff_notified == True", verif_b.get("staff_notified") is True)

        # Inspect events in DB for task B
        events_b = get_task_events(task_id_b)
        print()
        print("[TEST B] Event Log:")
        notify_events_b = []
        for evt in events_b:
            print(f"  [{evt['id']:>2}] type={evt['event_type']:<12} "
                  f"tool={str(evt['tool']):<28} status={evt['status']}")
            if evt["tool"] == "notify_staff":
                notify_events_b.append(evt)

        check("Notification succeeded on attempt 1",
              len(notify_events_b) >= 1 and notify_events_b[0]["status"] == "success")

        # Verify duplicate safety in SQLite: total tickets for Lab 3 projector
        with get_connection() as conn:
            all_tickets = conn.execute(
                "SELECT id, room, issue, priority, status FROM tickets WHERE LOWER(room) = 'lab 3'"
            ).fetchall()

        print()
        print("[TEST B] All Lab 3 Tickets in SQLite:")
        for t in all_tickets:
            print(f"  Ticket #{t['id']}: room={t['room']} issue={t['issue']} priority={t['priority']} status={t['status']}")

        check("Exactly 1 ticket exists for Lab 3 (no duplicate open ticket created)",
              len(all_tickets) == 1,
              f"got {len(all_tickets)} ticket(s)")

    finally:
        # Restore SIMULATE_EMAIL_FAILURE to empty in .env
        set_simulate_email_failure("")
        if proc:
            proc.terminate()
            proc.wait()
            print("[test] Subprocess server stopped.")

    print()
    print(SEP)
    if all_ok:
        print("ALL STAGE 6 FAILURE & RETRY TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE STAGE 6 TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
