"""
test_database.py — Stage 2 verification test

Tests:
1. Database initialises cleanly.
2. Seed inserts the correct rows.
3. Counts are exactly right (1 equipment, 2 incidents, 1 staff).
4. Both incidents are linked to the Lab 3 Projector.
5. Staff email matches TECH_EMAIL from the environment.
6. Running the seed a second time does NOT create duplicates.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from database import DB_PATH, get_connection, init_db
from seed import run_seed

load_dotenv()

PASS = "  PASS"
FAIL = "  FAIL"

separator = "=" * 70


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    line = f"{status}  {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return condition


def main() -> None:
    all_ok = True

    # ------------------------------------------------------------------
    # 0. Clean up any leftover db from a previous test run
    # ------------------------------------------------------------------
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed old database at {DB_PATH}")

    # ------------------------------------------------------------------
    # 1. Initialise database
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 1 — Database initialisation")
    init_db()
    all_ok &= check("campus_commander.db created", DB_PATH.exists())

    # Verify all expected tables exist
    with get_connection() as conn:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    for table in ("equipment", "incidents", "staff", "tickets", "agent_events"):
        all_ok &= check(f"table '{table}' exists", table in tables)

    # ------------------------------------------------------------------
    # 2. First seed run
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 2 — First seed run")
    run_seed()

    # ------------------------------------------------------------------
    # 3. Query and print all rows
    # ------------------------------------------------------------------
    with get_connection() as conn:
        equipment_rows = conn.execute("SELECT * FROM equipment").fetchall()
        incident_rows = conn.execute("SELECT * FROM incidents").fetchall()
        staff_rows = conn.execute("SELECT * FROM staff").fetchall()

    print(separator)
    print("STEP 3 — All equipment rows")
    for r in equipment_rows:
        print(f"  id={r['id']}  name={r['name']}  room={r['room']}  status={r['status']}")

    print()
    print("STEP 3 — All incident rows")
    for r in incident_rows:
        print(
            f"  id={r['id']}  equipment_id={r['equipment_id']}  "
            f"description={r['description']}  date={r['date']}  status={r['status']}"
        )

    print()
    print("STEP 3 — All staff rows")
    for r in staff_rows:
        print(f"  id={r['id']}  name={r['name']}  role={r['role']}  email={r['email']}")

    # ------------------------------------------------------------------
    # 4. Count assertions
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 4 — Count assertions")
    all_ok &= check("equipment count == 1", len(equipment_rows) == 1, f"got {len(equipment_rows)}")
    all_ok &= check("incident count == 2", len(incident_rows) == 2, f"got {len(incident_rows)}")
    all_ok &= check("staff count == 1", len(staff_rows) == 1, f"got {len(staff_rows)}")

    # ------------------------------------------------------------------
    # 5. Both incidents link to the Lab 3 Projector
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 5 — Incident linkage")
    projector_id = equipment_rows[0]["id"] if equipment_rows else None
    for r in incident_rows:
        all_ok &= check(
            f"incident id={r['id']} linked to projector",
            r["equipment_id"] == projector_id,
            f"equipment_id={r['equipment_id']} expected={projector_id}",
        )
    # Also check both expected descriptions exist
    descriptions = {r["description"] for r in incident_rows}
    all_ok &= check(
        "'projector display failure' incident exists",
        "projector display failure" in descriptions,
    )
    all_ok &= check(
        "'HDMI cable failure' incident exists",
        "HDMI cable failure" in descriptions,
    )

    # ------------------------------------------------------------------
    # 6. Staff email matches TECH_EMAIL
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 6 — Staff email")
    tech_email = os.getenv("TECH_EMAIL", "")
    actual_email = staff_rows[0]["email"] if staff_rows else ""
    all_ok &= check(
        "staff email == TECH_EMAIL",
        actual_email == tech_email,
        f"got '{actual_email}' expected '{tech_email}'",
    )

    # ------------------------------------------------------------------
    # 7. Second seed — must not create duplicates
    # ------------------------------------------------------------------
    print(separator)
    print("STEP 7 — Second seed run (idempotency check)")
    run_seed()

    with get_connection() as conn:
        eq_count = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
        inc_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        staff_count = conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0]

    print(f"  After second seed: equipment={eq_count}  incidents={inc_count}  staff={staff_count}")
    all_ok &= check("no duplicate equipment after 2nd seed", eq_count == 1, f"got {eq_count}")
    all_ok &= check("no duplicate incidents after 2nd seed", inc_count == 2, f"got {inc_count}")
    all_ok &= check("no duplicate staff after 2nd seed", staff_count == 1, f"got {staff_count}")

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------
    print(separator)
    if all_ok:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
