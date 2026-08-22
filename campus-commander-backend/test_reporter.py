"""
test_reporter.py -- Stage 6B: Reporter Attribution Test

Tests:
  TEST 1: GET /reporters -> returns at least 3 seeded reporters
  TEST 2: POST /agent/run with valid reporter_id:
          - HTTP 202
          - task_id returned
          - agent completes successfully
          - ticket.reported_by_id == 1 in SQLite
          - final outcome contains reporter information
          - final outcome message mentions reporter
  TEST 3: POST /agent/run without reporter_id -> FastAPI rejects with HTTP 422
  TEST 4: POST /agent/run with nonexistent reporter_id (e.g. 99999) -> rejected with HTTP 404
  TEST 5: POST /agent/run with valid reporter_id on same scenario -> duplicate safety preserved
"""

import json
import subprocess
import sys
import time

import requests

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


def ensure_server() -> subprocess.Popen | None:
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
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/agent/task/{task_id}", timeout=5)
        task_data = r.json()
        status = task_data.get("status")
        if status in ("COMPLETED", "FAILED", "NOTIFICATION_FAILED", "NEEDS_HUMAN_INTERVENTION"):
            return task_data
        time.sleep(1.0)
    raise TimeoutError(f"Task {task_id} did not complete within {MAX_WAIT_SECONDS}s.")


def main() -> None:
    global all_ok
    from database import get_connection, init_db
    from seed import run_seed

    print(SEP)
    print("STAGE 6B: REPORTER ATTRIBUTION TESTS")
    print(SEP)

    # Initialize & seed DB cleanly
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM memories")
        conn.execute("DELETE FROM agent_events")
        conn.execute("DELETE FROM tickets")
        conn.execute("DELETE FROM incidents")
        conn.execute("DELETE FROM equipment")
        conn.execute("DELETE FROM staff")
        conn.execute("DELETE FROM reporters")
        try:
            conn.execute("DELETE FROM tasks")
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass
    run_seed()
    print("Database reset and seeded with demo reporters.")
    print()

    proc = ensure_server()

    try:
        # ===================================================================
        # TEST 1 -- GET /reporters
        # ===================================================================
        print(SEP)
        print("TEST 1 -- GET /reporters")
        print(SEP)
        resp1 = requests.get(f"{BASE_URL}/reporters", timeout=5)
        check("GET /reporters returned 200", resp1.status_code == 200)
        reporters = resp1.json()
        print(f"  Reporters returned ({len(reporters)}):")
        for rep in reporters:
            print(f"    ID #{rep['id']}: {rep['name']} ({rep['role']}) - {rep['email']}")
        check("At least 3 seeded reporters exist", len(reporters) >= 3, f"got {len(reporters)}")

        # ===================================================================
        # TEST 2 -- POST /agent/run with valid reporter_id
        # ===================================================================
        print()
        print(SEP)
        print("TEST 2 -- POST /agent/run with valid reporter_id: 1 (Arjun Reddy)")
        print(SEP)
        resp2 = requests.post(
            f"{BASE_URL}/agent/run",
            json={"goal": GOAL, "reporter_id": 1},
            timeout=10,
        )
        check("POST /agent/run returns 202", resp2.status_code == 202)
        task_id_2 = resp2.json().get("task_id")
        check("task_id returned", isinstance(task_id_2, int), f"task_id={task_id_2}")

        print(f"  Polling task #{task_id_2} for completion...")
        task_2 = poll_task_completion(task_id_2)
        outcome_2 = task_2.get("outcome") or {}
        print("  Final Outcome:")
        print(json.dumps(task_2, indent=2))
        print()

        check("Task status == COMPLETED", task_2.get("status") == "COMPLETED")
        check("priority == HIGH", outcome_2.get("priority") == "HIGH")
        check("technician_notified == True", outcome_2.get("technician_notified") is True)
        ticket_id_2 = outcome_2.get("ticket_id")
        check("ticket_id returned", isinstance(ticket_id_2, int))

        # Check reporter object in outcome
        reporter_obj = outcome_2.get("reporter")
        check("Reporter object present in outcome", isinstance(reporter_obj, dict))
        if reporter_obj:
            check("reporter.id == 1", reporter_obj.get("id") == 1)
            check("reporter.name matches", "Arjun Reddy" in reporter_obj.get("name", ""))
            check("reporter.role == Student", reporter_obj.get("role") == "Student")

        # Check outcome message mentions reporter
        msg_2 = outcome_2.get("message", "")
        check("Outcome message mentions reporter name", "Arjun Reddy" in msg_2)

        # Inspect SQLite tickets table
        with get_connection() as conn:
            ticket_row_2 = conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id_2,)
            ).fetchone()

        check("Ticket row exists in SQLite", ticket_row_2 is not None)
        if ticket_row_2:
            check("ticket.reported_by_id == 1 in SQLite",
                  ticket_row_2["reported_by_id"] == 1,
                  f"got {ticket_row_2['reported_by_id']}")

        # ===================================================================
        # TEST 3 -- POST /agent/run without reporter_id (Validation failure)
        # ===================================================================
        print()
        print(SEP)
        print("TEST 3 -- POST /agent/run without reporter_id (Missing field)")
        print(SEP)
        resp3 = requests.post(
            f"{BASE_URL}/agent/run",
            json={"goal": GOAL},  # missing reporter_id
            timeout=10,
        )
        print(f"  HTTP Status: {resp3.status_code}")
        print(f"  Response: {resp3.json()}")
        check("FastAPI rejects missing reporter_id with HTTP 422", resp3.status_code == 422)

        # ===================================================================
        # TEST 4 -- POST /agent/run with nonexistent reporter_id
        # ===================================================================
        print()
        print(SEP)
        print("TEST 4 -- POST /agent/run with nonexistent reporter_id: 99999")
        print(SEP)
        resp4 = requests.post(
            f"{BASE_URL}/agent/run",
            json={"goal": GOAL, "reporter_id": 99999},
            timeout=10,
        )
        print(f"  HTTP Status: {resp4.status_code}")
        print(f"  Response: {resp4.json()}")
        check("API rejects nonexistent reporter_id with HTTP 404", resp4.status_code == 404)

        # ===================================================================
        # TEST 5 -- POST /agent/run again with different reporter (Duplicate Safety)
        # ===================================================================
        print()
        print(SEP)
        print("TEST 5 -- Duplicate Safety with another reporter: 2 (Priya Sharma)")
        print(SEP)
        resp5 = requests.post(
            f"{BASE_URL}/agent/run",
            json={"goal": GOAL, "reporter_id": 2},
            timeout=10,
        )
        check("POST returns 202", resp5.status_code == 202)
        task_id_5 = resp5.json().get("task_id")

        print(f"  Polling task #{task_id_5} for completion...")
        task_5 = poll_task_completion(task_id_5)
        outcome_5 = task_5.get("outcome") or {}

        check("Task status == COMPLETED", task_5.get("status") == "COMPLETED")
        ticket_id_5 = outcome_5.get("ticket_id")
        check("Reused existing Ticket #1 (no duplicate ticket created)",
              ticket_id_5 == ticket_id_2,
              f"ticket_id_5={ticket_id_5} ticket_id_2={ticket_id_2}")

        with get_connection() as conn:
            all_tickets = conn.execute(
                "SELECT id, room, issue, priority, reported_by_id, status FROM tickets WHERE LOWER(room) = 'lab 3'"
            ).fetchall()

        print("  All Lab 3 Tickets in SQLite:")
        for t in all_tickets:
            print(f"    Ticket #{t['id']}: room={t['room']} issue={t['issue']} reported_by_id={t['reported_by_id']} status={t['status']}")

        check("Exactly 1 ticket exists for Lab 3 (duplicate protection intact)",
              len(all_tickets) == 1,
              f"got {len(all_tickets)} ticket(s)")

    finally:
        if proc:
            proc.terminate()
            proc.wait()
            print("[test] Subprocess server stopped.")

    print()
    print(SEP)
    if all_ok:
        print("ALL REPORTER ATTRIBUTION TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE REPORTER ATTRIBUTION TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
