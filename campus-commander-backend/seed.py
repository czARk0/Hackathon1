"""
seed.py — Stage 2: Seed Data

Inserts the fixed demo scenario rows into the database.
Safe to run repeatedly — will not create duplicate records.

Reads TECH_EMAIL from the environment (via .env).
Fails clearly if TECH_EMAIL is not set.
"""

import os
from datetime import date, timedelta

from dotenv import load_dotenv

from database import get_connection, init_db

load_dotenv()


def _seed_equipment(conn) -> int:
    """
    Ensure the Lab 3 projector row exists.
    Returns the equipment id (existing or newly inserted).
    """
    row = conn.execute(
        "SELECT id FROM equipment WHERE name = ? AND room = ?",
        ("Projector", "Lab 3"),
    ).fetchone()

    if row:
        return row["id"]

    cursor = conn.execute(
        "INSERT INTO equipment (name, room, status, last_maintenance) VALUES (?, ?, ?, ?)",
        ("Projector", "Lab 3", "faulty", None),
    )
    return cursor.lastrowid


def _seed_incidents(conn, equipment_id: int) -> None:
    """
    Ensure the two canonical Lab 3 projector incidents exist.
    Uses (equipment_id, description) as the uniqueness key.
    """
    today = date.today()
    incident_data = [
        {
            "description": "projector display failure",
            "date": str(today - timedelta(weeks=6)),
            "status": "resolved",
            "resolution": "Replaced faulty lamp unit",
        },
        {
            "description": "HDMI cable failure",
            "date": str(today - timedelta(weeks=3)),
            "status": "resolved",
            "resolution": "Replaced HDMI cable",
        },
    ]

    for incident in incident_data:
        existing = conn.execute(
            "SELECT id FROM incidents WHERE equipment_id = ? AND description = ?",
            (equipment_id, incident["description"]),
        ).fetchone()

        if existing:
            continue  # already seeded — skip

        conn.execute(
            """
            INSERT INTO incidents (equipment_id, description, date, status, resolution)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                equipment_id,
                incident["description"],
                incident["date"],
                incident["status"],
                incident["resolution"],
            ),
        )


def _seed_staff(conn, tech_email: str) -> None:
    """
    Ensure the AV Technician staff record exists.
    Uses (role, email) as the uniqueness key.
    """
    existing = conn.execute(
        "SELECT id FROM staff WHERE role = ? AND email = ?",
        ("AV Technician", tech_email),
    ).fetchone()

    if existing:
        return  # already seeded — skip

    conn.execute(
        "INSERT INTO staff (name, role, email) VALUES (?, ?, ?)",
        ("AV Technician", "AV Technician", tech_email),
    )


def _seed_reporters(conn) -> None:
    """
    Ensure fixed demo reporter records exist.
    Uses email as the uniqueness key. Idempotent.
    """
    reporters = [
        {"name": "Arjun Reddy", "role": "Student", "email": "student1@example.com"},
        {"name": "Priya Sharma", "role": "Student", "email": "student2@example.com"},
        {"name": "Rahul Kumar", "role": "Faculty", "email": "faculty1@example.com"},
        {"name": "Sneha Patel", "role": "Staff", "email": "staff1@example.com"},
    ]

    for rep in reporters:
        existing = conn.execute(
            "SELECT id FROM reporters WHERE email = ?",
            (rep["email"],),
        ).fetchone()

        if existing:
            continue

        conn.execute(
            "INSERT INTO reporters (name, role, email) VALUES (?, ?, ?)",
            (rep["name"], rep["role"], rep["email"]),
        )


def run_seed() -> None:
    """
    Run all seed inserts inside a single transaction.
    Idempotent — safe to call multiple times.
    """
    tech_email = os.getenv("TECH_EMAIL")
    if not tech_email:
        raise EnvironmentError(
            "TECH_EMAIL is not set. "
            "Add it to your .env file before running the seed."
        )

    init_db()  # ensure tables exist before seeding

    with get_connection() as conn:
        equipment_id = _seed_equipment(conn)
        _seed_incidents(conn, equipment_id)
        _seed_staff(conn, tech_email)
        _seed_reporters(conn)
        conn.commit()

    print(f"Seed complete. Lab 3 Projector id={equipment_id}, tech_email={tech_email}")


if __name__ == "__main__":
    run_seed()

