"""
agent.py — Stages 1 + 4: Plan Generation + Agent Execution Loop

Stage 1  : get_plan()   — calls Gemini, returns validated structured plan.
Stage 4  : run_agent()  — executes the plan, logs events, handles retries.

Architecture: PLAN -> ACT -> OBSERVE -> DECIDE -> ACT -> VERIFY -> FINAL OUTCOME
"""

import json
import os
import re
from datetime import date, datetime, timezone

from google import genai
from google.genai import types
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Required plan step names (in order)
# ---------------------------------------------------------------------------
REQUIRED_STEPS = [
    "check_equipment_history",
    "determine_priority",
    "create_ticket",
    "notify_staff",
    "verify",
]

# Steps that MUST have a "tool" field
STEPS_WITH_TOOL = {
    "check_equipment_history",
    "create_ticket",
    "notify_staff",
    "verify",
}

# Steps that MUST NOT have a "tool" field
STEPS_WITHOUT_TOOL = {"determine_priority"}

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a campus facility management AI agent.
Your ONLY task is to parse the user's request and return a structured JSON plan.

Return ONLY a single valid JSON object. 
Do NOT include markdown code fences (no ```json or ``` wrappers).
Do NOT include any explanation, preamble, or text outside the JSON.

The JSON must follow this EXACT structure:

{
  "extracted": {
    "room": "<room or location mentioned>",
    "issue": "<equipment or problem mentioned>",
    "deadline": "<deadline or urgency mentioned>"
  },
  "plan": [
    {
      "step": "check_equipment_history",
      "tool": "get_equipment_history"
    },
    {
      "step": "determine_priority"
    },
    {
      "step": "create_ticket",
      "tool": "create_maintenance_ticket"
    },
    {
      "step": "notify_staff",
      "tool": "notify_staff"
    },
    {
      "step": "verify",
      "tool": "verify_ticket"
    }
  ]
}

Rules:
- "determine_priority" must NOT have a "tool" field — it is handled by deterministic logic.
- All other steps MUST have a "tool" field with a string value.
- The "plan" array must contain exactly these 5 steps in this order.
- Fill "extracted" with values from the user's request.
- Do not deviate from this structure.
"""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if Gemini adds them."""
    text = text.strip()
    # Remove opening fence (```json or ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    # Remove closing fence
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _validate_plan(plan: dict) -> None:
    """
    Validate the parsed plan structure.
    Raises ValueError with a diagnostic message if anything is wrong.
    """
    # --- Top-level keys ---
    if "extracted" not in plan:
        raise ValueError("Missing top-level key: 'extracted'")
    if "plan" not in plan:
        raise ValueError("Missing top-level key: 'plan'")

    extracted = plan["extracted"]
    if not isinstance(extracted, dict):
        raise ValueError(f"'extracted' must be an object, got {type(extracted)}")
    for field in ("room", "issue", "deadline"):
        if field not in extracted:
            raise ValueError(f"'extracted' is missing required field: '{field}'")
        if not isinstance(extracted[field], str):
            raise ValueError(
                f"'extracted.{field}' must be a string, got {type(extracted[field])}"
            )

    steps = plan["plan"]
    if not isinstance(steps, list):
        raise ValueError(f"'plan' must be a list, got {type(steps)}")
    if len(steps) != len(REQUIRED_STEPS):
        raise ValueError(
            f"'plan' must have exactly {len(REQUIRED_STEPS)} steps, "
            f"got {len(steps)}"
        )

    for i, (step_obj, expected_name) in enumerate(zip(steps, REQUIRED_STEPS)):
        if not isinstance(step_obj, dict):
            raise ValueError(f"plan[{i}] must be an object, got {type(step_obj)}")
        if "step" not in step_obj:
            raise ValueError(f"plan[{i}] is missing 'step' key")
        actual_name = step_obj["step"]
        if actual_name != expected_name:
            raise ValueError(
                f"plan[{i}] 'step' must be '{expected_name}', got '{actual_name}'"
            )

        if expected_name in STEPS_WITH_TOOL:
            if "tool" not in step_obj:
                raise ValueError(
                    f"plan[{i}] ('{expected_name}') must have a 'tool' field"
                )
            if not isinstance(step_obj["tool"], str):
                raise ValueError(
                    f"plan[{i}] 'tool' must be a string, got {type(step_obj['tool'])}"
                )

        if expected_name in STEPS_WITHOUT_TOOL:
            if "tool" in step_obj:
                raise ValueError(
                    f"plan[{i}] ('{expected_name}') must NOT have a 'tool' field "
                    f"(got '{step_obj['tool']}')"
                )


def get_plan(user_goal: str) -> dict:
    """
    Send user_goal to Gemini and return a validated structured plan dict.

    Parameters
    ----------
    user_goal : str
        The raw natural-language request from the user.

    Returns
    -------
    dict
        A validated plan with 'extracted' and 'plan' keys.

    Raises
    ------
    EnvironmentError
        If GEMINI_API_KEY or GEMINI_MODEL are not set.
    ValueError
        If the response cannot be parsed as JSON or fails validation.
    """
    # --- Read configuration from environment ---
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    if not model_name:
        raise EnvironmentError(
            "GEMINI_MODEL is not set. "
            "Copy .env.example to .env and specify the model name."
        )

    # --- Configure Gemini client (new google-genai SDK) ---
    client = genai.Client(api_key=api_key)

    # --- Call the API with fallback models if quota exceeded ---
    candidate_models = [model_name]
    for fallback in ("gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.5-flash"):
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_exc = None
    raw_text = None
    for m in candidate_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=user_goal,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,  # deterministic JSON output
                ),
            )
            raw_text = response.text
            break
        except Exception as exc:
            last_exc = exc
            continue

    if raw_text is None:
        raise ValueError(f"All Gemini models failed. Last error: {last_exc}") from last_exc

    # --- Strip markdown fences (defensive) ---
    cleaned_text = _strip_markdown_fences(raw_text)

    # --- Parse JSON ---
    try:
        plan = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini returned non-JSON content.\n"
            f"JSON error: {exc}\n"
            f"Raw response (first 500 chars):\n{raw_text[:500]}"
        ) from exc

    # --- Validate structure ---
    _validate_plan(plan)

    return plan


# ---------------------------------------------------------------------------
# Stage 1B — Intent Classification
# ---------------------------------------------------------------------------
INTENT_SYSTEM_PROMPT = """You are the intent classification and assistance engine for Campus Commander, an autonomous AI system for campus facility operations.
Analyze the user's input and classify it into one of three categories:

1. "MAINTENANCE_REQUEST"
   The user is reporting an actionable physical equipment, facility, or classroom issue that requires facility maintenance or technician attention (e.g. broken projector, malfunctioning AC, leaking pipe, light bulb replacement, damaged furniture, etc.).
   Examples:
   - "The projector in Lab 3 isn't working. Presentation tomorrow 10am."
   - "AC is leaking water in Room 204."
   - "The whiteboard is coming loose from the wall."

2. "GENERAL_QUERY"
   The user is asking a general question, campus location/directions inquiry, schedule, facility hours, greeting, or information lookup without reporting an actionable equipment failure.
   Examples:
   - "Where is Lab 3?"
   - "Who is the AV technician?"
   - "What are library hours?"
   - "Hello, what can you do?"

3. "OUT_OF_SCOPE"
   The input is completely unrelated to campus facilities or operations, spam, or nonsense.

Return ONLY a valid JSON object:
{
  "intent": "MAINTENANCE_REQUEST" | "GENERAL_QUERY" | "OUT_OF_SCOPE",
  "confidence": 0.95,
  "reason": "<brief rationale>",
  "direct_response": "<If GENERAL_QUERY or OUT_OF_SCOPE, provide a direct, helpful, concise answer to the user (for example, for 'Where is Lab 3?', answer based on typical campus info such as 'Lab 3 is located in the Science & Technology Building, 2nd Floor, Room 203.'). If MAINTENANCE_REQUEST, leave as empty string ''>"
}
"""


def classify_intent(user_goal: str) -> dict:
    """
    Classify user goal intent into MAINTENANCE_REQUEST, GENERAL_QUERY, or OUT_OF_SCOPE.
    Returns a dict with keys: 'intent', 'confidence', 'reason', 'direct_response'.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    if not model_name:
        raise EnvironmentError(
            "GEMINI_MODEL is not set. "
            "Copy .env.example to .env and specify the model name."
        )

    client = genai.Client(api_key=api_key)

    candidate_models = [model_name]
    for fallback in ("gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.5-flash"):
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_exc = None
    raw_text = None
    for m in candidate_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=user_goal,
                config=types.GenerateContentConfig(
                    system_instruction=INTENT_SYSTEM_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text
            break
        except Exception as exc:
            last_exc = exc
            continue

    if raw_text is None:
        return {
            "intent": "MAINTENANCE_REQUEST",
            "confidence": 0.5,
            "reason": f"Fallback due to API error: {last_exc}",
            "direct_response": "",
        }

    cleaned_text = _strip_markdown_fences(raw_text)
    try:
        data = json.loads(cleaned_text)
        if not isinstance(data, dict) or "intent" not in data:
            raise ValueError("Invalid intent response structure")
        return data
    except Exception as exc:
        return {
            "intent": "MAINTENANCE_REQUEST",
            "confidence": 0.5,
            "reason": f"Failed to parse intent JSON: {exc}",
            "direct_response": "",
        }



# ===========================================================================
# Stage 4 — Agent Execution Loop
# ===========================================================================

# Safety limits
MAX_STEPS = 10
MAX_TOOL_CALLS = 8


def _now_iso() -> str:
    """Current UTC timestamp as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _log_event(
    conn,  # kept for API compatibility but no longer used — each call opens its own connection
    task_id: int,
    event_type: str,
    tool: str | None,
    status: str,
    result: str,
) -> None:
    """
    Insert a single agent_events row immediately using a fresh connection.

    Opening a new connection per event and closing it immediately ensures
    the write is committed and visible to concurrent readers (e.g. the
    polling API) without waiting for the entire agent loop to finish.
    Events are never batched.
    """
    from database import get_connection as _get_conn
    with _get_conn() as event_conn:
        event_conn.execute(
            """
            INSERT INTO agent_events
                (task_id, event_type, tool, status, result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, event_type, tool, status, result, _now_iso()),
        )
        event_conn.commit()



def _is_urgent_deadline(deadline_str: str) -> bool:
    """
    Return True when the deadline text implies same-day or next-day urgency.

    Recognised patterns (case-insensitive):
      - "today", "now", "immediately"
      - "tomorrow" or "tmrw"
      - a time-only string like "10 AM" (implies today/soon)

    Anything else (e.g. "next week", "in 3 days") returns False.
    """
    text = deadline_str.lower()
    urgent_keywords = ("today", "tonight", "now", "immediately", "tomorrow", "tmrw", "tmr")
    for kw in urgent_keywords:
        if kw in text:
            return True
    # A bare time with no day qualifier ("10 AM", "10am", "10:00")
    # is treated as same-day urgency
    import re as _re
    if _re.search(r"\b\d{1,2}\s*(am|pm|:\d{2})\b", text) and not any(
        day in text
        for day in ("week", "month", "day", "monday", "tuesday", "wednesday",
                    "thursday", "friday", "saturday", "sunday")
    ):
        return True
    return False


def _determine_priority(incident_count: int, deadline_str: str) -> tuple[str, str]:
    """
    Deterministic Python priority logic — Gemini is NOT consulted.

    Rule:
        incident_count >= 2  AND  deadline is same-day or next-day  =>  HIGH
        Otherwise                                                     =>  MEDIUM

    Returns (priority, reason_string)
    """
    urgent = _is_urgent_deadline(deadline_str)
    if incident_count >= 2 and urgent:
        reason = (
            f"{incident_count} previous incidents + "
            f"next-day presentation deadline -> HIGH priority"
        )
        return "HIGH", reason
    else:
        parts = []
        if incident_count < 2:
            parts.append(f"only {incident_count} prior incident(s)")
        if not urgent:
            parts.append(f"deadline '{deadline_str}' is not same/next-day")
        reason = "; ".join(parts) + " -> MEDIUM priority"
        return "MEDIUM", reason


def _get_av_technician_email() -> str:
    """
    Look up the AV Technician email from the staff table.
    Opens its own short-lived connection. Raises ValueError if not found.
    """
    from database import get_connection as _get_conn
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT email FROM staff WHERE role = 'AV Technician' LIMIT 1"
        ).fetchone()
    if not row:
        raise ValueError(
            "No AV Technician found in the staff table. Run seed.py first."
        )
    return row["email"]


def run_agent(goal: str, task_id: int, reporter_id: int | None = None) -> dict:
    """
    Execute the full Campus Commander agent loop for a given goal.

    Architecture:
        INTENT -> (if MAINTENANCE) -> PLAN -> get_equipment_history -> determine_priority
               -> create_maintenance_ticket -> notify_staff -> verify_ticket -> FINAL OUTCOME
               -> (if NON-MAINTENANCE) -> Direct response outcome (skip 5-step workflow)

    Parameters
    ----------
    goal : str
        The raw natural-language user request.
    task_id : int
        Unique identifier for this agent run (used as FK in agent_events).
    reporter_id : int, optional
        ID of the campus reporter submitting the request.

    Returns
    -------
    dict
        Final outcome with status, ticket_id, priority, technician_notified, message, etc.
    """
    # Import here to avoid circular imports at module load time
    from tools import (
        create_maintenance_ticket,
        get_equipment_history,
        notify_staff,
        verify_ticket,
    )

    step_count = 0
    tool_call_count = 0

    # Look up reporter info immediately so it is available to ALL branches (maintenance & non-maintenance)
    reporter_info: dict | None = None
    if reporter_id is not None:
        from database import get_connection as _get_conn
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT id, name, role FROM reporters WHERE id = ?",
                (reporter_id,),
            ).fetchone()
            if row:
                reporter_info = {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                }

    # -----------------------------------------------------------------------
    # PHASE 0 — Intent Classification & Branching
    # -----------------------------------------------------------------------
    print("[Agent] Classifying user intent...")
    intent_result = classify_intent(goal)
    intent = intent_result.get("intent", "MAINTENANCE_REQUEST")

    _log_event(
        None,
        task_id,
        "intent_classification",
        "classify_intent",
        "success",
        json.dumps(intent_result),
    )

    # BRANCH: If not a maintenance request, skip the 5-step workflow entirely
    if intent != "MAINTENANCE_REQUEST":
        direct_msg = intent_result.get("direct_response") or (
            "This request does not appear to be an actionable facility maintenance issue. "
            "No ticket was created and no staff was notified."
        )
        print(f"[Agent] Non-maintenance intent detected ('{intent}'). Skipping 5-step workflow.")

        return {
            "status": "COMPLETED",
            "intent": intent,
            "ticket_id": None,
            "priority": "N/A",
            "technician_notified": False,
            "reporter": reporter_info,
            "message": direct_msg,
            "steps_executed": 0,
            "tool_calls_made": 0,
            "verification": {
                "ticket_exists": False,
                "priority_set": False,
                "staff_notified": False,
            },
        }

    # Accumulated state — populated as the loop executes
    history_result: dict | None = None
    priority: str = "MEDIUM"
    ticket_id: int | None = None
    technician_notified: bool = False
    verify_result: dict | None = None

    # -----------------------------------------------------------------------
    # PHASE 1 — Planning (5-Step Ticket Workflow)
    # -----------------------------------------------------------------------
    print("[Agent] Maintenance intent confirmed. Calling get_plan()...")
    plan_data = get_plan(goal)
    extracted = plan_data["extracted"]
    steps = plan_data["plan"]

    room = extracted["room"]
    issue = extracted["issue"]
    deadline = extracted["deadline"]

    print(f"[Agent] Plan received. room='{room}' issue='{issue}' deadline='{deadline}'")
    print(f"[Agent] Executing {len(steps)} steps...")

    # -----------------------------------------------------------------------
    # PHASE 2 — Memory Retrieval (Contextual memory lookup)
    # -----------------------------------------------------------------------
    from memory import retrieve_memories, save_memory
    retrieved_memories = retrieve_memories(room)
    mem_summary = {
        "count": len(retrieved_memories),
        "room": room,
        "memories": [
            {"id": m["id"], "type": m["memory_type"], "value": m["value"]}
            for m in retrieved_memories
        ],
    }
    _log_event(
        None,
        task_id,
        "memory_retrieval",
        "retrieve_memories",
        "success",
        json.dumps(mem_summary),
    )
    print(f"[Agent] Retrieved {len(retrieved_memories)} memory/memories for '{room}'")

    # No long-lived connection held here.
    # Each sub-operation opens its own short-lived connection so that
    # commits are immediately visible to concurrent API readers.

    try:
        for step_obj in steps:
            step_name = step_obj["step"]
            tool_name = step_obj.get("tool")  # None for determine_priority

            # ---------------------------------------------------------------
            # Safety limits
            # ---------------------------------------------------------------
            step_count += 1
            if step_count > MAX_STEPS:
                _log_event(None, task_id, "safety", None, "failed",
                           f"MAX_STEPS ({MAX_STEPS}) exceeded -- stopping")
                return {
                    "status": "NEEDS_HUMAN_INTERVENTION",
                    "ticket_id": ticket_id,
                    "priority": priority,
                    "technician_notified": technician_notified,
                    "message": f"Safety limit: exceeded {MAX_STEPS} total steps.",
                }

            print(f"[Agent] Step {step_count}: {step_name}")

            # ===============================================================
            # STEP: check_equipment_history
            # ===============================================================
            if step_name == "check_equipment_history":
                if tool_call_count >= MAX_TOOL_CALLS:
                    _log_event(None, task_id, "safety", tool_name, "failed",
                               f"MAX_TOOL_CALLS ({MAX_TOOL_CALLS}) exceeded")
                    return {
                        "status": "NEEDS_HUMAN_INTERVENTION",
                        "ticket_id": ticket_id,
                        "priority": priority,
                        "technician_notified": technician_notified,
                        "message": f"Safety limit: exceeded {MAX_TOOL_CALLS} tool calls.",
                    }
                tool_call_count += 1

                try:
                    history_result = get_equipment_history(room, "Projector")
                    result_str = json.dumps(history_result)
                    _log_event(None, task_id, "tool_call", tool_name,
                               "success", result_str)
                    print(f"[Agent]   -> incident_count={history_result['incident_count']}")
                except Exception as exc:
                    _log_event(None, task_id, "tool_call", tool_name,
                               "failed", str(exc))
                    history_result = {"incident_count": 0, "incidents": []}
                    print(f"[Agent]   -> get_equipment_history failed: {exc}; defaulting to 0 incidents")

            # ===============================================================
            # STEP: determine_priority  (Python decision -- NO tool)
            # ===============================================================
            elif step_name == "determine_priority":
                incident_count = (history_result or {}).get("incident_count", 0)
                priority, reason = _determine_priority(incident_count, deadline)
                _log_event(None, task_id, "decision", None,
                           "success", reason)
                print(f"[Agent]   -> priority={priority}  reason: {reason}")

            # ===============================================================
            # STEP: create_ticket
            # ===============================================================
            elif step_name == "create_ticket":
                if tool_call_count >= MAX_TOOL_CALLS:
                    _log_event(None, task_id, "safety", tool_name, "failed",
                               f"MAX_TOOL_CALLS ({MAX_TOOL_CALLS}) exceeded")
                    return {
                        "status": "NEEDS_HUMAN_INTERVENTION",
                        "ticket_id": ticket_id,
                        "priority": priority,
                        "technician_notified": technician_notified,
                        "message": f"Safety limit: exceeded {MAX_TOOL_CALLS} tool calls.",
                    }
                tool_call_count += 1

                try:
                    ticket_result = create_maintenance_ticket(
                        room, issue, priority, reported_by_id=reporter_id
                    )
                    ticket_id = ticket_result["ticket_id"]

                    if ticket_result["duplicate"]:
                        priority = "HIGH"
                        dup_reason = (
                            f"Duplicate ticket #{ticket_id} already open for '{issue}' "
                            f"in {room} -- reusing existing ticket and escalating priority to HIGH"
                        )
                        _log_event(None, task_id, "decision", None,
                                   "success", dup_reason)
                        print(f"[Agent]   -> duplicate ticket #{ticket_id}, escalated to HIGH")

                    _log_event(None, task_id, "tool_call", tool_name,
                               "success", json.dumps(ticket_result))
                    print(f"[Agent]   -> ticket_id={ticket_id} status={ticket_result['status']}")

                except Exception as exc:
                    _log_event(None, task_id, "tool_call", tool_name,
                               "failed", str(exc))
                    return {
                        "status": "FAILED",
                        "ticket_id": None,
                        "priority": priority,
                        "technician_notified": False,
                        "message": f"Failed to create maintenance ticket: {exc}",
                    }

            # ===============================================================
            # STEP: notify_staff  (with exactly-one retry)
            # ===============================================================
            elif step_name == "notify_staff":
                if tool_call_count >= MAX_TOOL_CALLS:
                    _log_event(None, task_id, "safety", tool_name, "failed",
                               f"MAX_TOOL_CALLS ({MAX_TOOL_CALLS}) exceeded")
                    return {
                        "status": "NEEDS_HUMAN_INTERVENTION",
                        "ticket_id": ticket_id,
                        "priority": priority,
                        "technician_notified": technician_notified,
                        "message": f"Safety limit: exceeded {MAX_TOOL_CALLS} tool calls.",
                    }
                tool_call_count += 1

                staff_email = _get_av_technician_email()
                notify_message = (
                    f"Maintenance required -- Ticket #{ticket_id}\n"
                    f"Room: {room}\n"
                    f"Issue: {issue}\n"
                    f"Priority: {priority}\n"
                    f"Deadline: {deadline}\n"
                    f"Please attend before the scheduled presentation."
                )

                def _attempt_notify(attempt_label: str) -> dict:
                    """Try notify_staff once; return result dict on success."""
                    return notify_staff(staff_email, notify_message, ticket_id)

                # --- First attempt ---
                try:
                    notify_result = _attempt_notify("attempt 1")
                    technician_notified = True
                    # Restore ticket to OPEN if it was previously awaiting manual follow-up
                    from database import get_connection as _get_conn
                    with _get_conn() as _c:
                        _c.execute(
                            "UPDATE tickets SET status='OPEN' WHERE id=? AND status='awaiting manual follow-up'",
                            (ticket_id,)
                        )
                        _c.commit()
                    _log_event(None, task_id, "tool_call", tool_name,
                               "success", json.dumps(notify_result))
                    print(f"[Agent]   -> email sent message_id={notify_result.get('message_id')}")

                except Exception as first_exc:
                    _log_event(None, task_id, "tool_call", tool_name,
                               "failed", f"attempt 1 failed: {first_exc}")
                    print(f"[Agent]   -> notify attempt 1 FAILED: {first_exc}; retrying...")

                    # --- Exactly one retry ---
                    if tool_call_count >= MAX_TOOL_CALLS:
                        _log_event(None, task_id, "safety", tool_name, "failed",
                                   "Cannot retry -- MAX_TOOL_CALLS reached")
                        from database import get_connection as _get_conn
                        with _get_conn() as _c:
                            _c.execute(
                                "UPDATE tickets SET status='awaiting manual follow-up' WHERE id=?",
                                (ticket_id,)
                            )
                            _c.commit()
                        return {
                            "status": "NOTIFICATION_FAILED",
                            "ticket_id": ticket_id,
                            "priority": priority,
                            "technician_notified": False,
                            "message": (
                                f"Ticket #{ticket_id} created but email notification failed "
                                f"and retry was blocked by safety limit. "
                                f"Ticket set to 'awaiting manual follow-up'."
                            ),
                        }

                    tool_call_count += 1
                    try:
                        notify_result = _attempt_notify("attempt 2 (retry)")
                        technician_notified = True
                        from database import get_connection as _get_conn
                        with _get_conn() as _c:
                            _c.execute(
                                "UPDATE tickets SET status='OPEN' WHERE id=? AND status='awaiting manual follow-up'",
                                (ticket_id,)
                            )
                            _c.commit()
                        _log_event(None, task_id, "tool_call", tool_name,
                                   "success",
                                   json.dumps({**notify_result, "note": "succeeded on retry"}))
                        print(f"[Agent]   -> retry succeeded message_id={notify_result.get('message_id')}")


                    except Exception as retry_exc:
                        _log_event(None, task_id, "tool_call", tool_name,
                                   "failed", f"retry also failed: {retry_exc}")
                        print(f"[Agent]   -> retry also FAILED: {retry_exc}")
                        from database import get_connection as _get_conn
                        with _get_conn() as _c:
                            _c.execute(
                                "UPDATE tickets SET status='awaiting manual follow-up' WHERE id=?",
                                (ticket_id,)
                            )
                            _c.commit()
                        return {
                            "status": "NOTIFICATION_FAILED",
                            "ticket_id": ticket_id,
                            "priority": priority,
                            "technician_notified": False,
                            "message": (
                                f"Ticket #{ticket_id} created but email notification failed "
                                f"after 2 attempts. Ticket set to 'awaiting manual follow-up'. "
                                f"Last error: {retry_exc}"
                            ),
                        }

            # ===============================================================
            # STEP: verify
            # ===============================================================
            elif step_name == "verify":
                if tool_call_count >= MAX_TOOL_CALLS:
                    _log_event(None, task_id, "safety", tool_name, "failed",
                               f"MAX_TOOL_CALLS ({MAX_TOOL_CALLS}) exceeded")
                    return {
                        "status": "NEEDS_HUMAN_INTERVENTION",
                        "ticket_id": ticket_id,
                        "priority": priority,
                        "technician_notified": technician_notified,
                        "message": f"Safety limit: exceeded {MAX_TOOL_CALLS} tool calls.",
                    }
                tool_call_count += 1

                try:
                    verify_result = verify_ticket(ticket_id)
                    _log_event(None, task_id, "tool_call", tool_name,
                               "success", json.dumps(verify_result))
                    print(f"[Agent]   -> verify_result={verify_result}")
                except Exception as exc:
                    _log_event(None, task_id, "tool_call", tool_name,
                               "failed", str(exc))
                    verify_result = {
                        "ticket_exists": False,
                        "priority_set": False,
                        "staff_notified": False,
                    }
                    print(f"[Agent]   -> verify_ticket failed: {exc}")

            else:
                _log_event(None, task_id, "unknown_step", tool_name,
                           "failed", f"Unrecognised step: {step_name}")
                print(f"[Agent]   -> WARNING: unknown step '{step_name}' -- skipped")

    except Exception as loop_exc:
        # Catch-all so the background task always updates the tasks table
        raise loop_exc

    # -----------------------------------------------------------------------
    # PHASE FINAL — Build honest outcome
    # -----------------------------------------------------------------------
    v = verify_result or {}
    all_verified = (
        v.get("ticket_exists", False)
        and v.get("priority_set", False)
        and v.get("staff_notified", False)
    )

    incident_count = (history_result or {}).get("incident_count", 0)

    if all_verified:
        status = "COMPLETED"
        reporter_suffix = (
            f" Reported by {reporter_info['name']} ({reporter_info['role']})."
            if reporter_info else ""
        )
        message = (
            f"Campus Commander completed all steps for the {room} {issue}.{reporter_suffix} "
            f"Historical check found {incident_count} prior incident(s). "
            f"Priority determined as {priority} "
            f"({'urgent deadline detected' if _is_urgent_deadline(deadline) else 'standard timeline'}). "
            f"Maintenance ticket #{ticket_id} created/reused. "
            f"AV Technician notified by email. "
            f"Ticket verified in database. "
            f"NOTE: Physical repair is still pending -- Campus Commander manages "
            f"ticketing and notification only."
        )

        # -------------------------------------------------------------------
        # Memory Save (Persist task outcome memory)
        # -------------------------------------------------------------------
        mem_value = (
            f"Issue: {issue}. Priority: {priority}. Ticket #{ticket_id}. "
            f"Technician notified successfully. Task completed."
        )
        save_memory(
            task_id=task_id,
            memory_type="task_outcome",
            key=room,
            value=mem_value,
        )
        _log_event(
            None,
            task_id,
            "memory_save",
            "save_memory",
            "success",
            json.dumps({
                "memory_type": "task_outcome",
                "key": room,
                "ticket_id": ticket_id,
                "saved": True,
            }),
        )
        print(f"[Agent] Saved task outcome memory for '{room}'")

    else:
        unverified = [k for k, v_val in v.items() if not v_val]
        status = "PARTIAL"
        message = (
            f"Agent loop finished but verification was incomplete. "
            f"Unverified checks: {unverified}. "
            f"Ticket #{ticket_id} may still be actionable."
        )

    return {
        "status": status,
        "ticket_id": ticket_id,
        "priority": priority,
        "technician_notified": technician_notified,
        "reporter": reporter_info,
        "message": message,
        "steps_executed": step_count,
        "tool_calls_made": tool_call_count,
        "verification": v,
    }
