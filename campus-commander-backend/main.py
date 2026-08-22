"""
main.py -- Stage 5: FastAPI REST API

Endpoints:
    POST /agent/run                     -- submit a goal, start agent in background
    GET  /agent/task/{task_id}          -- poll task status + outcome
    GET  /agent/task/{task_id}/events   -- stream-poll agent events (grows during execution)

Architecture:
    - FastAPI BackgroundTasks runs run_agent() asynchronously.
    - Task state is persisted in the SQLite `tasks` table.
    - Agent events are persisted in `agent_events` as they happen.
    - No WebSockets, SSE, Celery, Redis, or Kafka.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

load_dotenv()

from database import get_connection, init_db
from seed import run_seed

# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Campus Commander API",
    description="Autonomous AI agent for campus facility management.",
    version="1.0.0",
)

# Thread pool for running the blocking agent loop without tying up the event loop
_agent_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-worker")

# CORS -- allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Initialise the database and seed demo data on first start."""
    init_db()
    try:
        run_seed()
    except Exception as exc:
        # Seed may fail if TECH_EMAIL is missing -- non-fatal for the API itself
        print(f"[startup] seed warning: {exc}")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    goal: str
    reporter_id: int  # required

    @field_validator("goal")
    @classmethod
    def goal_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("goal must not be empty")
        return v.strip()


class RunResponse(BaseModel):
    task_id: int
    status: str


class ReporterItem(BaseModel):
    id: int
    name: str
    role: str
    email: str


class TaskResponse(BaseModel):
    task_id: int
    status: str
    outcome: Any


class EventItem(BaseModel):
    id: int
    event_type: str
    tool: str | None
    status: str
    result: str | None
    timestamp: str


class EventsResponse(BaseModel):
    task_id: int
    events: list[EventItem]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_task(goal: str) -> int:
    """Insert a RUNNING task row and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (status, goal, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("RUNNING", goal, _now_iso(), _now_iso()),
        )
        conn.commit()
        return cursor.lastrowid


def _update_task(task_id: int, status: str, outcome: dict) -> None:
    """Update the task row with final status and JSON-serialised outcome."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, outcome=?, updated_at=? WHERE id=?",
            (status, json.dumps(outcome), _now_iso(), task_id),
        )
        conn.commit()


def _run_agent_sync(goal: str, task_id: int, reporter_id: int | None = None) -> None:
    """
    Synchronous wrapper — runs in a thread pool so it doesn't block
    uvicorn's event loop while the agent executes.
    """
    from agent import run_agent  # imported here to keep startup fast
    try:
        outcome = run_agent(goal, task_id, reporter_id=reporter_id)
        final_status = outcome.get("status", "COMPLETED")
        _update_task(task_id, final_status, outcome)
    except Exception as exc:
        error_outcome = {
            "status": "FAILED",
            "ticket_id": None,
            "priority": None,
            "technician_notified": False,
            "message": f"Unhandled exception in agent loop: {exc}",
        }
        _update_task(task_id, "FAILED", error_outcome)


async def _run_agent_background(goal: str, task_id: int, reporter_id: int | None = None) -> None:
    """
    Async wrapper used by FastAPI BackgroundTasks.
    Offloads the synchronous agent to a thread so the event loop
    remains free to serve concurrent polling requests.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_agent_executor, _run_agent_sync, goal, task_id, reporter_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/reporters", response_model=list[ReporterItem])
def get_reporters() -> list[ReporterItem]:
    """Return all seeded campus reporters."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, role, email FROM reporters ORDER BY id ASC"
        ).fetchall()

    return [
        ReporterItem(
            id=r["id"],
            name=r["name"],
            role=r["role"],
            email=r["email"],
        )
        for r in rows
    ]


@app.post("/agent/run", response_model=RunResponse, status_code=202)
def run_agent_endpoint(
    request: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """
    Submit a natural-language goal to Campus Commander with reporter attribution.

    Validates that reporter_id exists.
    Returns immediately with a task_id.
    The agent runs asynchronously via BackgroundTasks.
    Poll GET /agent/task/{task_id} for status.
    """
    # Validate reporter_id exists in SQLite
    with get_connection() as conn:
        reporter = conn.execute(
            "SELECT id FROM reporters WHERE id = ?", (request.reporter_id,)
        ).fetchone()

    if reporter is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reporter with id {request.reporter_id} not found."
        )

    task_id = _create_task(request.goal)
    background_tasks.add_task(
        _run_agent_background, request.goal, task_id, request.reporter_id
    )
    return RunResponse(task_id=task_id, status="running")



@app.get("/agent/task/{task_id}", response_model=TaskResponse)
def get_task(task_id: int) -> TaskResponse:
    """
    Poll the status and outcome of a submitted task.

    Returns:
        - status='running'  while the agent is still executing
        - status='COMPLETED' / 'FAILED' / 'NEEDS_HUMAN_INTERVENTION' when done
        - outcome is null while running, populated on completion
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, status, outcome FROM tasks WHERE id=?", (task_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")

    outcome_val = None
    if row["outcome"]:
        try:
            outcome_val = json.loads(row["outcome"])
        except (json.JSONDecodeError, TypeError):
            outcome_val = row["outcome"]

    return TaskResponse(
        task_id=row["id"],
        status=row["status"],
        outcome=outcome_val,
    )


@app.get("/agent/task/{task_id}/events", response_model=EventsResponse)
def get_task_events(task_id: int) -> EventsResponse:
    """
    Return all agent_events for a task in chronological order.

    This endpoint is safe to call while the agent is still running --
    events are committed to SQLite immediately as they occur, so the
    list grows progressively with each poll.
    """
    # Verify task exists first
    with get_connection() as conn:
        task_row = conn.execute(
            "SELECT id FROM tasks WHERE id=?", (task_id,)
        ).fetchone()

        if task_row is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")

        event_rows = conn.execute(
            """
            SELECT id, event_type, tool, status, result, timestamp
            FROM agent_events
            WHERE task_id=?
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

    events = [
        EventItem(
            id=r["id"],
            event_type=r["event_type"],
            tool=r["tool"],
            status=r["status"],
            result=r["result"],
            timestamp=r["timestamp"],
        )
        for r in event_rows
    ]

    return EventsResponse(task_id=task_id, events=events)


@app.get("/health")
def health_check() -> dict:
    """Simple liveness check."""
    return {"status": "ok", "service": "Campus Commander API"}
