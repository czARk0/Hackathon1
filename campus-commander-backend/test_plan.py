"""
test_plan.py — Stage 1 tests for get_plan()

Calls the real Gemini API (no mocking).
Verifies all three phrasings of the Lab 3 projector scenario.
"""

import json
import sys

from agent import get_plan

# ---------------------------------------------------------------------------
# Test inputs
# ---------------------------------------------------------------------------
TESTS = [
    (
        1,
        "The projector in Lab 3 isn't working. "
        "I have my project presentation tomorrow at 10 AM. Please handle it.",
    ),
    (
        2,
        "Lab 3's projector is broken and I present tomorrow morning at 10.",
    ),
    (
        3,
        "Can you sort out the Lab 3 projector issue? "
        "Presentation is tomorrow 10am.",
    ),
]

REQUIRED_STEPS = [
    "check_equipment_history",
    "determine_priority",
    "create_ticket",
    "notify_staff",
    "verify",
]

STEPS_WITH_TOOL = {
    "check_equipment_history",
    "create_ticket",
    "notify_staff",
    "verify",
}

STEPS_WITHOUT_TOOL = {"determine_priority"}

# ---------------------------------------------------------------------------
# Validation helper (mirrors agent.py for independent checking)
# ---------------------------------------------------------------------------

def check_plan(plan: dict) -> list[str]:
    """Return a list of failure messages (empty = all passed)."""
    failures = []

    # extracted fields
    extracted = plan.get("extracted", {})
    for field in ("room", "issue", "deadline"):
        if not extracted.get(field):
            failures.append(f"  FAIL  extracted.{field} is missing or empty")

    # plan steps
    steps = plan.get("plan", [])
    if len(steps) != len(REQUIRED_STEPS):
        failures.append(
            f"  FAIL  expected {len(REQUIRED_STEPS)} steps, got {len(steps)}"
        )
        return failures  # can't check step details if count is wrong

    for i, (step_obj, expected_name) in enumerate(zip(steps, REQUIRED_STEPS)):
        actual_name = step_obj.get("step", "<missing>")
        if actual_name != expected_name:
            failures.append(
                f"  FAIL  step {i}: expected '{expected_name}', got '{actual_name}'"
            )
            continue

        if expected_name in STEPS_WITH_TOOL:
            tool = step_obj.get("tool")
            if not tool or not isinstance(tool, str):
                failures.append(
                    f"  FAIL  step '{expected_name}' missing 'tool' field"
                )

        if expected_name in STEPS_WITHOUT_TOOL:
            if "tool" in step_obj:
                failures.append(
                    f"  FAIL  step '{expected_name}' must NOT have 'tool' "
                    f"(got '{step_obj['tool']}')"
                )

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    all_passed = True
    separator = "=" * 70

    for test_num, user_input in TESTS:
        print(separator)
        print(f"TEST {test_num}")
        print(f"INPUT: {user_input}")
        print()

        try:
            plan = get_plan(user_input)
        except Exception as exc:
            print(f"  ERROR calling get_plan(): {exc}")
            all_passed = False
            continue

        print("PARSED JSON:")
        print(json.dumps(plan, indent=2))
        print()

        failures = check_plan(plan)
        if failures:
            print("VALIDATION: FAILED")
            for msg in failures:
                print(msg)
            all_passed = False
        else:
            print("VALIDATION: PASSED")
            # Print a friendly summary of what was extracted
            ext = plan["extracted"]
            print(f"  room     = {ext['room']}")
            print(f"  issue    = {ext['issue']}")
            print(f"  deadline = {ext['deadline']}")
            steps = plan["plan"]
            print(f"  steps    = {[s['step'] for s in steps]}")
            determine = next(s for s in steps if s["step"] == "determine_priority")
            has_tool = "tool" in determine
            print(f"  determine_priority has tool = {has_tool}  (must be False)")

        print()

    print(separator)
    if all_passed:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("ONE OR MORE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
