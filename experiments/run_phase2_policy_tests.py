import json
import sys
from pathlib import Path

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/src")

from context_isolation import TaskScopedPolicy


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/phase2_policy_tests")


def build_history() -> list[dict]:
    return [
        {"turn_id": "m1_u", "role": "user", "content": "Solve 2x + 3 = 11.", "task_id": "math_1"},
        {"turn_id": "m1_a", "role": "assistant", "content": "The answer is x = 4.", "task_id": "math_1"},
        {
            "turn_id": "travel_u",
            "role": "user",
            "content": "Book a calendar reminder for my Tokyo flight tomorrow.",
            "task_id": "travel_1",
        },
        {
            "turn_id": "travel_a",
            "role": "assistant",
            "content": "The calendar reminder has been created.",
            "task_id": "travel_1",
        },
        {"turn_id": "m2_u", "role": "user", "content": "Solve x^2 - 5x + 6 = 0.", "task_id": "math_2"},
        {"turn_id": "m2_a", "role": "assistant", "content": "The roots are 2 and 3.", "task_id": "math_2"},
    ]


def assert_case(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    policy = TaskScopedPolicy(max_task_turns=6)
    history = build_history()
    tools = [{"type": "function", "function": {"name": "calendar_update", "description": "Update calendar."}}]
    cases = [
        {
            "name": "same_domain_unrelated_math",
            "message": "Solve x^2 + x - 6 = 0.",
            "expected_need": "no_context",
            "expected_boundary": "new_task",
            "expected_turns": [],
            "expected_tools": [],
        },
        {
            "name": "explicit_previous_math",
            "message": "Continue from the previous math problem and explain why those roots work.",
            "expected_need": "task_local",
            "expected_boundary": "continue_task",
            "expected_turns": ["m2_u", "m2_a"],
            "expected_tools": [],
        },
        {
            "name": "ambiguous_pronoun",
            "message": "Make that shorter.",
            "expected_need": "clarification",
            "expected_boundary": "continue_task",
            "expected_turns": [],
            "expected_tools": [],
        },
        {
            "name": "tool_state_reference",
            "message": "Change the calendar reminder I booked earlier.",
            "expected_need": "tool_state",
            "expected_boundary": "continue_task",
            "expected_turns": ["travel_u", "travel_a"],
            "expected_tools": tools,
        },
        {
            "name": "global_profile_like_self_contained",
            "message": "Translate hello into Chinese.",
            "expected_need": "no_context",
            "expected_boundary": "new_task",
            "expected_turns": [],
            "expected_tools": [],
        },
    ]

    records = []
    for case in cases:
        selected = policy.select(
            session_id="phase2_tests",
            user_id="u1",
            current_message=case["message"],
            raw_history=history,
            available_tools=tools,
        )
        record = {
            "name": case["name"],
            "message": case["message"],
            "need_type": selected.decision.need_type,
            "boundary": selected.decision.boundary,
            "selected_turn_ids": selected.decision.selected_turn_ids,
            "selected_tools": selected.decision.selected_tools,
            "reason": selected.decision.reason,
        }
        records.append(record)
        assert_case(f"{case['name']} need", selected.decision.need_type, case["expected_need"])
        assert_case(f"{case['name']} boundary", selected.decision.boundary, case["expected_boundary"])
        assert_case(f"{case['name']} turns", selected.decision.selected_turn_ids, case["expected_turns"])
        expected_tool_names = [
            item["function"]["name"] for item in case["expected_tools"] if isinstance(item, dict) and "function" in item
        ]
        assert_case(f"{case['name']} tools", selected.decision.selected_tools, expected_tool_names)
        print(
            f"PASS {case['name']}: need={selected.decision.need_type} "
            f"boundary={selected.decision.boundary} turns={selected.decision.selected_turn_ids} "
            f"tools={selected.decision.selected_tools}"
        )

    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
