import json
from database import get_connection, init_db
from seed import run_seed
from agent import run_agent

def run_test_case(title: str, goal: str, task_id: int, reporter_id: int = 1):
    print("=" * 80)
    print(f"TEST: {title}")
    print(f"GOAL: \"{goal}\"")
    print(f"TASK ID: {task_id}, REPORTER ID: {reporter_id}")
    print("-" * 80)
    
    outcome = run_agent(goal, task_id=task_id, reporter_id=reporter_id)
    
    print("\n--- RETURNED OUTCOME ---")
    print(json.dumps(outcome, indent=2))
    
    with get_connection() as conn:
        events = conn.execute(
            "SELECT id, event_type, tool, status, result FROM agent_events WHERE task_id = ? ORDER BY id ASC",
            (task_id,)
        ).fetchall()
        
    print("\n--- AGENT EVENTS LOGGED ---")
    for e in events:
        print(f"[{e['id']}] event_type='{e['event_type']}', tool='{e['tool']}', status='{e['status']}'")
        print(f"     result: {e['result']}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    init_db()
    try:
        run_seed()
    except Exception as exc:
        print(f"Seed info: {exc}")
        
    # Test 1: Maintenance issue
    run_test_case(
        "Test 1: Maintenance Request",
        "The projector in Lab 3 isn't working. Presentation tomorrow 10am.",
        task_id=101,
        reporter_id=1,
    )
    
    # Test 2: General query (Non-maintenance)
    run_test_case(
        "Test 2: General Query / Location Inquiry",
        "Where is Lab 3?",
        task_id=102,
        reporter_id=1,
    )
