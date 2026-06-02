import json
import sys
from pathlib import Path

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/src")

from context_isolation import (
    FullSessionPolicy,
    NeedGatedPolicy,
    OracleBoundaryPolicy,
    RecentNPolicy,
    RetrievalOnlyPolicy,
    TaskScopedPolicy,
    TaskScopedToolFilterPolicy,
)
from context_isolation.trace import JsonlTraceWriter


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/context_policy_smoke")


def build_history():
    return [
        {"turn_id": "t1", "role": "user", "content": "Solve 2x + 3 = 11.", "task_id": "math_1"},
        {"turn_id": "t2", "role": "assistant", "content": "x = 4.", "task_id": "math_1"},
        {"turn_id": "t3", "role": "user", "content": "Give dinner suggestions for a rainy day.", "task_id": "daily_1"},
        {"turn_id": "t4", "role": "assistant", "content": "Soup and rice are good options.", "task_id": "daily_1"},
        {"turn_id": "t5", "role": "user", "content": "Solve x^2 - 5x + 6 = 0.", "task_id": "math_2"},
        {"turn_id": "t6", "role": "assistant", "content": "x = 2 or x = 3.", "task_id": "math_2"},
    ]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    writer = JsonlTraceWriter(OUT_DIR / "traces.jsonl")
    history = build_history()
    current_messages = [
        "Solve x^2 + x - 6 = 0.",
        "Continue from the previous math problem and explain why those roots work.",
        "Search for the latest weather in Shanghai.",
    ]
    tools = [{"type": "function", "function": {"name": "search_weather", "description": "Search weather."}}]
    policies = [
        FullSessionPolicy(),
        RecentNPolicy(n=2),
        RetrievalOnlyPolicy(top_k=2),
        NeedGatedPolicy(),
        TaskScopedPolicy(),
        TaskScopedToolFilterPolicy(),
        OracleBoundaryPolicy(),
    ]

    records = []
    for current_message in current_messages:
        print(f"\nCURRENT: {current_message}")
        for policy in policies:
            selected = policy.select(
                session_id="mixed_demo",
                user_id="u1",
                current_message=current_message,
                raw_history=history,
                available_tools=tools,
            )
            record = {
                "policy": policy.name,
                "current_message": current_message,
                "selected_turn_ids": selected.decision.selected_turn_ids,
                "need_type": selected.decision.need_type,
                "boundary": selected.decision.boundary,
                "selected_tools": selected.decision.selected_tools,
                "suppressed_tools": selected.decision.suppressed_tools,
                "reason": selected.decision.reason,
                "trace": selected.trace,
            }
            records.append(record)
            writer.write(record)
            print(
                f"{policy.name}: selected={selected.decision.selected_turn_ids} "
                f"need={selected.decision.need_type} boundary={selected.decision.boundary} "
                f"tools={selected.decision.selected_tools}"
            )

    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
