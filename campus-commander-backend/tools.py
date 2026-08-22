"""
tools.py — Stage 3: Four Tool Functions

Implements:
  - get_equipment_history()
  - create_maintenance_ticket()
  - notify_staff()
  - verify_ticket()

No agent loop, no FastAPI, no orchestration here.
"""

import json
import os
from datetime import datetime, timezone


import resend
from dotenv import load_dotenv

from database import get_connection

load_dotenv()

# ---------------------------------------------------------------------------
# Email sender address — read from env with safe default for Resend onboarding
# ---------------------------------------------------------------------------
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")


# ===========================================================================
# 1. get_equipment_history
# ===========================================================================

def get_equipment_history(room: str, equipment_type: str) -> dict:
    """
    Query the equipment and incidents tables for the given room and
    equipment name/type.

    Returns:
        {
            "incident_count": <int>,
            "incidents": [
                {"date": "...", "description": "...", "resolution": "..."}
            ]
        }

    Raises:
        ValueError if no matching equipment is found.
    """
    with get_connection() as conn:
        equipment = conn.execute(
            """
            SELECT id, name, room, status, last_maintenance
            FROM equipment
            WHERE LOWER(room) = LOWER(?)
              AND LOWER(name) = LOWER(?)
            """,
            (room, equipment_type),
        ).fetchone()

        if equipment is None:
            raise ValueError(
                f"No equipment found: type='{equipment_type}' in room='{room}'"
            )

        incidents = conn.execute(
            """
            SELECT date, description, resolution
            FROM incidents
            WHERE equipment_id = ?
            ORDER BY date ASC
            """,
            (equipment["id"],),
        ).fetchall()

    incident_list = [
        {
            "date": row["date"],
            "description": row["description"],
            "resolution": row["resolution"],
        }
        for row in incidents
    ]

    return {
        "incident_count": len(incident_list),
        "incidents": incident_list,
    }


# ===========================================================================
# 2. create_maintenance_ticket
# ===========================================================================

def create_maintenance_ticket(
    room: str,
    issue: str,
    priority: str,
    reported_by_id: int | None = None,
) -> dict:
    """
    Create a maintenance ticket, or return the existing open ticket if one
    already exists for the same room + issue combination.

    Returns:
        On new ticket:
            {"ticket_id": <int>, "status": "CREATED", "duplicate": False, "priority": <str>, "reported_by_id": <int|None>}
        On duplicate:
            {"ticket_id": <int>, "status": "EXISTING", "duplicate": True, "priority": "HIGH", "reported_by_id": <int|None>}
    """
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, priority, reported_by_id
            FROM tickets
            WHERE LOWER(room)  = LOWER(?)
              AND status != 'resolved'
              AND (
                    LOWER(issue) = LOWER(?)
                 OR (LOWER(issue) LIKE '%projector%' AND LOWER(?) LIKE '%projector%')
              )
            LIMIT 1
            """,
            (room, issue, issue),
        ).fetchone()

        if existing:
            # Escalate priority to HIGH on duplicate; preserve existing reporter attribution
            conn.execute(
                "UPDATE tickets SET priority = 'HIGH' WHERE id = ?",
                (existing["id"],),
            )
            conn.commit()

            return {
                "ticket_id": existing["id"],
                "status": "EXISTING",
                "duplicate": True,
                "priority": "HIGH",
                "reported_by_id": existing["reported_by_id"],
            }

        # Create new ticket
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """
            INSERT INTO tickets (room, issue, priority, reported_by_id, status, created_at)
            VALUES (?, ?, ?, ?, 'OPEN', ?)
            """,
            (room, issue, priority.upper(), reported_by_id, now),
        )
        conn.commit()
        return {
            "ticket_id": cursor.lastrowid,
            "status": "CREATED",
            "duplicate": False,
            "priority": priority.upper(),
            "reported_by_id": reported_by_id,
        }



# ===========================================================================
# 3. notify_staff
# ===========================================================================

def notify_staff(staff_email: str, message: str, ticket_id: int) -> dict:
    """
    Send a real email to staff_email via Resend.

    Reads RESEND_API_KEY from environment.
    If SIMULATE_EMAIL_FAILURE=true, raises an exception before sending.

    Returns:
        {"success": True, "status": "sent", "ticket_id": <int>, "message_id": "..."}

    Raises:
        EnvironmentError  — if RESEND_API_KEY is not set.
        RuntimeError      — if SIMULATE_EMAIL_FAILURE=true.
        Exception         — if Resend API call fails.

    NOTE: Does NOT perform retry logic — that belongs to the agent loop (Prompt 4).
    """
    # Reload environment to pick up runtime test toggles like SIMULATE_EMAIL_FAILURE
    load_dotenv(override=True)

    # Simulate failure for testing purposes
    if os.getenv("SIMULATE_EMAIL_FAILURE", "").lower() == "true":
        raise RuntimeError(
            "SIMULATE_EMAIL_FAILURE=true — deliberately failing before send"
        )


    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "RESEND_API_KEY is not set. Add it to your .env file."
        )

    resend.api_key = api_key

    subject = f"[Campus Commander] Maintenance Ticket #{ticket_id}"
    html_body = f"""
    <h2>Campus Commander — Maintenance Alert</h2>
    <p><strong>Ticket ID:</strong> #{ticket_id}</p>
    <p><strong>Details:</strong> {message}</p>
    <hr>
    <p style="color: #888; font-size: 12px;">
        This message was sent automatically by Campus Commander.
    </p>
    """

    params: resend.Emails.SendParams = {
        "from": EMAIL_FROM,
        "to": [staff_email],
        "subject": subject,
        "html": html_body,
    }

    response = resend.Emails.send(params)

    # Resend returns an object with an 'id' field on success
    message_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)

    return {
        "success": True,
        "status": "sent",
        "ticket_id": ticket_id,
        "message_id": message_id,
    }


# ===========================================================================
# 4. verify_ticket
# ===========================================================================

def verify_ticket(ticket_id: int) -> dict:
    """
    Verify the state of a ticket by querying the database.

    - ticket_exists:   ticket row is present.
    - priority_set:    ticket exists AND priority is non-empty.
    - staff_notified:  an agent_events row exists where:
                         tool    = 'notify_staff'
                         status  = 'success'
                         result contains ticket_id or task_id matches ticket_id
                       Does NOT assume notify_staff was called -- reads the DB.

    Returns:
        {
            "ticket_exists":   <bool>,
            "priority_set":    <bool>,
            "staff_notified":  <bool>
        }
    """
    with get_connection() as conn:
        ticket = conn.execute(
            "SELECT id, priority FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        ticket_exists = ticket is not None
        priority_set = bool(ticket_exists and ticket["priority"])

        # Find any successful notify_staff event
        events = conn.execute(
            """
            SELECT task_id, result FROM agent_events
            WHERE tool   = 'notify_staff'
              AND status = 'success'
            """
        ).fetchall()

        staff_notified = False
        for evt in events:
            if evt["task_id"] == ticket_id:
                staff_notified = True
                break
            res = evt["result"] or ""
            try:
                data = json.loads(res)
                if isinstance(data, dict) and data.get("ticket_id") == ticket_id:
                    staff_notified = True
                    break
            except Exception:
                pass
            if f'"ticket_id": {ticket_id}' in res or f"'ticket_id': {ticket_id}" in res:
                staff_notified = True
                break

    return {
        "ticket_exists": ticket_exists,
        "priority_set": priority_set,
        "staff_notified": staff_notified,
    }

