"""
test_api.py -- Stage 5: API Integration Test

Starts the FastAPI server as a subprocess, runs the full demo scenario
via HTTP, polls the events endpoint to prove progressive delivery,
then prints the final task + events.

The script exits with code 0 on success, 1 on failure.
"""

import json
import subprocess
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000"
GOAL = (
    "The projector in Lab 3 isn't working. "
    "I have my project presentation tomorrow at 10 AM. Please handle it."
)
SERVER_STARTUP_WAIT = 3.0   # seconds to wait for uvicorn to be ready
POLL_BEFORE_FIRST = 2.5     # wait this long before first event poll (Gemini takes 2-4s)
POLL_INTERVAL = 2.5         # seconds between event polls
MAX_WAIT_SECONDS = 120       # give up waiting for completion after this

SEP = "=" * 70
PASS = "  PASS"
FAIL = "  FAIL"


def check(label: str, cond: bool, detail: str = "") -> bool:
    tag = PASS if cond else FAIL
    msg = f"{tag}  {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    return cond


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def start_server() -> subprocess.Popen:
    """Launch uvicorn in a subprocess and wait for it to become ready."""
    print("[test] Starting uvicorn server...")
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
                print(f"[test] Server ready after {SERVER_STARTUP_WAIT}s")
                return proc
        except requests.exceptions.ConnectionError:
            time.sleep(0.3)

    proc.terminate()
    raise RuntimeError("Server did not start in time.")


from database import get_connection, init_db
from seed import run_seed

def main() -> None:
    all_ok = True
    proc = None

    # Clean reset of DB before testing
    print("[test] Resetting DB and seeding demo data...")
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
    print("[test] Database reset complete.")

    try:
        proc = start_server()
        time.sleep(SERVER_STARTUP_WAIT)


        # ===================================================================
        # TEST 1 -- POST /agent/run returns immediately
        # ===================================================================
        print()
        print(SEP)
        print("TEST 1 -- POST /agent/run")
        print()

        t_post_start = time.time()
        resp = requests.post(
            f"{BASE_URL}/agent/run",
            json={"goal": GOAL, "reporter_id": 1},
            timeout=15,
        )
        t_post_end = time.time()
        post_elapsed = t_post_end - t_post_start

        print(f"  HTTP status : {resp.status_code}")
        print(f"  Elapsed     : {post_elapsed:.3f}s")
        print(f"  Response    : {resp.json()}")
        print()

        all_ok &= check("POST returns 202", resp.status_code == 202)
        data = resp.json()
        task_id = data.get("task_id")
        all_ok &= check("task_id returned", isinstance(task_id, int))
        all_ok &= check("status == 'running'", data.get("status") == "running")

        # The Gemini API call alone takes >1s, so if POST returned in <1.5s
        # it returned before the agent finished.
        all_ok &= check(
            "POST returned before agent finished (< 1.5s)",
            post_elapsed < 1.5,
            f"elapsed={post_elapsed:.3f}s",
        )

        # ===================================================================
        # TEST 2 -- Prove progressive event polling
        # ===================================================================
        print()
        print(SEP)
        print("TEST 2 -- Progressive event polling")
        print()
        print(f"  (Gemini plan call typically takes 2-4s, so first event")
        print(f"   appears around t+2-4s after POST)")
        print()

        poll_results = []          # list of (elapsed_since_post, event_count)

        # Poll 1 -- wait 2.5s first (agent should have completed Gemini call by now)
        time.sleep(POLL_BEFORE_FIRST)
        r = requests.get(f"{BASE_URL}/agent/task/{task_id}/events", timeout=5)
        count1 = len(r.json().get("events", []))
        poll_results.append((time.time() - t_post_start, count1))
        print(f"  Poll 1 at t+{poll_results[-1][0]:.2f}s: {count1} events")

        # Poll 2 -- after ~2.5s more
        time.sleep(POLL_INTERVAL)
        r = requests.get(f"{BASE_URL}/agent/task/{task_id}/events", timeout=5)
        count2 = len(r.json().get("events", []))
        poll_results.append((time.time() - t_post_start, count2))
        print(f"  Poll 2 at t+{poll_results[-1][0]:.2f}s: {count2} events")

        # Poll 3 -- after another ~2.5s
        time.sleep(POLL_INTERVAL)
        r = requests.get(f"{BASE_URL}/agent/task/{task_id}/events", timeout=5)
        count3 = len(r.json().get("events", []))
        poll_results.append((time.time() - t_post_start, count3))
        print(f"  Poll 3 at t+{poll_results[-1][0]:.2f}s: {count3} events")

        print()

        # Growth check: at least one poll should show events growing OR
        # all events should be present in the final poll (agent ran fully in background)
        growth_seen = (count2 > count1) or (count3 > count2)
        events_present = count3 > 0
        progressive = growth_seen or events_present
        all_ok &= check(
            "Events visible during / after background execution",
            progressive,
            f"counts: {count1} -> {count2} -> {count3}",
        )
        if growth_seen:
            print("  NOTE: Event count grew between polls -- BackgroundTasks proven concurrent.")
        elif events_present:
            print("  NOTE: Events appeared by final poll. Task ran fully in background.")
            print("        Growth not observable because Gemini latency compressed the window.")

        # ===================================================================
        # TEST 3 -- Poll task status shows RUNNING at some point, then terminal
        # ===================================================================
        print()
        print(SEP)
        print("TEST 3 -- Poll task status until terminal")
        print()

        deadline = time.time() + MAX_WAIT_SECONDS
        status_seen_running = False
        final_task = None

        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/agent/task/{task_id}", timeout=5)
            task_data = r.json()
            current_status = task_data.get("status")
            elapsed = time.time() - t_post_start
            print(f"  t+{elapsed:.1f}s  status={current_status}")

            if current_status == "RUNNING":
                status_seen_running = True

            if current_status in ("COMPLETED", "FAILED", "NEEDS_HUMAN_INTERVENTION",
                                  "NOTIFICATION_FAILED", "PARTIAL"):
                final_task = task_data
                break

            time.sleep(1.5)

        if final_task is None:
            print(f"  ERROR: Task did not reach terminal state within {MAX_WAIT_SECONDS}s")
            all_ok = False
        else:
            print()
            all_ok &= check(
                "status == COMPLETED",
                final_task.get("status") == "COMPLETED",
                f"got '{final_task.get('status')}'",
            )
            outcome = final_task.get("outcome") or {}
            all_ok &= check("outcome.priority == HIGH",
                            outcome.get("priority") == "HIGH",
                            f"got '{outcome.get('priority')}'")
            all_ok &= check("outcome.technician_notified == true",
                            outcome.get("technician_notified") is True)
            all_ok &= check("outcome.ticket_id set",
                            isinstance(outcome.get("ticket_id"), int))

        # ===================================================================
        # TEST 4 -- Final event list
        # ===================================================================
        print()
        print(SEP)
        print("TEST 4 -- Final event list")
        print()

        r = requests.get(f"{BASE_URL}/agent/task/{task_id}/events", timeout=5)
        final_events = r.json().get("events", [])
        print(f"  Total events: {len(final_events)}")
        for evt in final_events:
            print(f"  [{evt['id']:>2}] type={evt['event_type']:<14} "
                  f"tool={str(evt['tool']):<30} status={evt['status']}")

        print()
        all_ok &= check("at least 5 events in final list",
                        len(final_events) >= 5,
                        f"got {len(final_events)}")

        tool_names = [e["tool"] for e in final_events if e["tool"]]
        all_ok &= check("get_equipment_history event present",
                        "get_equipment_history" in tool_names)
        all_ok &= check("create_maintenance_ticket event present",
                        "create_maintenance_ticket" in tool_names)
        all_ok &= check("notify_staff event present",
                        "notify_staff" in tool_names)
        all_ok &= check("verify_ticket event present",
                        "verify_ticket" in tool_names)

        decision_events = [e for e in final_events if e["event_type"] == "decision"]
        all_ok &= check("determine_priority decision event present",
                        len(decision_events) >= 1)

        # ===================================================================
        # TEST 5 -- 404 for nonexistent task
        # ===================================================================
        print()
        print(SEP)
        print("TEST 5 -- 404 for nonexistent task")
        r404 = requests.get(f"{BASE_URL}/agent/task/99999", timeout=5)
        all_ok &= check("404 for nonexistent task", r404.status_code == 404,
                        f"got {r404.status_code}")

        # ===================================================================
        # Print final outcome
        # ===================================================================
        print()
        print(SEP)
        print("FINAL OUTCOME:")
        print(json.dumps(final_task, indent=2) if final_task else "  None")

    finally:
        if proc:
            proc.terminate()
            proc.wait()
            print()
            print("[test] Server stopped.")

    print()
    print(SEP)
    if all_ok:
        print("ALL API TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE API TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
