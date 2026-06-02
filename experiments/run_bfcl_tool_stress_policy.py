import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from benchmark_adapters import BenchmarkResult, make_policy, summarize_records  # noqa: E402
from benchmark_adapters.bfcl_adapter import BFCLAdapter  # noqa: E402
from benchmark_adapters.bfcl_scoring import expected_calls  # noqa: E402


OUT_DIR_DEFAULT = PROJECT_ROOT / "experiments" / "runs" / "bfcl_tool_stress_policy"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


def task_ids_from_messages(messages: list[dict[str, Any]]) -> list[str]:
    task_ids = []
    for message in messages:
        task_id = message.get("task_id")
        if task_id and task_id not in task_ids:
            task_ids.append(str(task_id))
    return task_ids


def estimate_tokens(messages: list[dict[str, Any]], current_message: str, system_text: str) -> int:
    chars = len(system_text) + len(current_message) + sum(len(str(item.get("content", ""))) for item in messages)
    return max(1, round(chars / 3.5))


def gold_tool_names(gold: Any) -> list[str]:
    names = []
    for call in expected_calls(gold):
        if call.name not in names:
            names.append(call.name)
    return names


def build_units(category: str, limit: int):
    adapter = BFCLAdapter()
    units = adapter.build_session(category=category, limit=limit)
    for unit in units:
        unit.metadata["gold_tool_names"] = gold_tool_names(unit.gold)
    return units


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="multi_turn_base")
    parser.add_argument("--policy", default="task_scoped_tool_filter")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    units = build_units(args.category, args.limit)
    policy = make_policy(args.policy)
    raw_history: list[dict[str, Any]] = []
    completed_task_ids: list[str] = []
    records: list[dict[str, Any]] = []

    print(
        f"{CYAN}BFCL tool stress category={args.category} policy={policy.name} limit={len(units)}{RESET}",
        flush=True,
    )

    for index, unit in enumerate(units, start=1):
        task_id = f"bfcl_{index:04d}"
        forbidden_task_ids = list(completed_task_ids)
        selected = policy.select(
            session_id=f"bfcl_{args.category}",
            user_id="benchmark_user",
            current_message=(
                "This is a new independent BFCL tool-calling task. "
                "File names or object names may include words like previous, but they do not refer to chat history.\n\n"
                f"{unit.query}"
            ),
            raw_history=raw_history,
            available_tools=unit.tools,
        )
        selected_task_ids = task_ids_from_messages(selected.messages)
        forbidden_included = [task_id for task_id in selected_task_ids if task_id in set(forbidden_task_ids)]
        input_tokens_est = estimate_tokens(selected.messages, unit.query, unit.system_text)
        unnecessary_context = bool(selected.messages)
        context_ok = not forbidden_included and not unnecessary_context
        selected_tool_names = selected.decision.selected_tools
        gold_tools = unit.metadata["gold_tool_names"]
        over_filter_tool = bool(gold_tools) and not set(gold_tools).issubset(set(selected_tool_names))
        wrong_tool_exposed = any(name not in set(gold_tools) for name in selected_tool_names)
        tool_context_ok = not over_filter_tool

        print(
            f"{BLUE}=== BFCL task {index}/{len(units)} {unit.task_uid} ==={RESET}",
            flush=True,
        )
        print(
            f"{MAGENTA}[context] selected_tasks={selected_task_ids} forbidden_included={forbidden_included} "
            f"selected_history={len(selected.messages)} input_tokens_est={input_tokens_est}{RESET}",
            flush=True,
        )
        print(
            f"{YELLOW}[tools] gold={gold_tools} selected={selected_tool_names} "
            f"over_filter={over_filter_tool} wrong_exposed={wrong_tool_exposed}{RESET}",
            flush=True,
        )

        status = "PASS" if context_ok and tool_context_ok else "FAIL"
        record = BenchmarkResult(
            n=index,
            template=f"bfcl_{args.category}_tool_stress",
            policy=policy.name,
            task_id=task_id,
            task_uid=unit.task_uid,
            source_benchmark=unit.source_benchmark,
            domain=unit.domain,
            task_type=unit.task_type,
            context_ok=context_ok and tool_context_ok,
            benchmark_status=status,
            benchmark_score={
                "benchmark_score": status == "PASS",
                "benchmark_scored": True,
                "score_type": "bfcl_context_tool_selection",
                "gold_tool_names": gold_tools,
                "selected_tool_names": selected_tool_names,
                "over_filter_tool": over_filter_tool,
                "wrong_tool_exposed": wrong_tool_exposed,
                "eval_details": [],
            },
            content="DRY_RUN_TOOL_STRESS",
            context_summary={
                "policy": policy.name,
                "need_type": selected.decision.need_type,
                "boundary": selected.decision.boundary,
                "confidence": selected.decision.confidence,
                "selected_turn_ids": selected.decision.selected_turn_ids,
                "selected_history_count": len(selected.messages),
                "input_tokens_est": input_tokens_est,
                "reason": selected.decision.reason,
            },
            gold_forbidden_context_task_ids=forbidden_task_ids,
            selected_task_ids=selected_task_ids,
            forbidden_context_task_ids_included=forbidden_included,
            unnecessary_context=unnecessary_context,
            metadata=unit.metadata,
        ).to_dict()
        records.append(record)

        raw_history.extend(
            [
                {
                    "turn_id": f"u_{index:04d}",
                    "role": "user",
                    "content": unit.query,
                    "task_id": task_id,
                    "metadata": {"task_uid": unit.task_uid, "gold_tool_names": gold_tools},
                },
                {
                    "turn_id": f"a_{index:04d}",
                    "role": "assistant",
                    "content": "DRY_RUN_TOOL_CALL_RESULT",
                    "task_id": task_id,
                    "metadata": {"task_uid": unit.task_uid, "gold_tool_names": gold_tools},
                },
            ]
        )
        completed_task_ids.append(task_id)

    summary = summarize_records(f"bfcl_{args.category}_tool_stress", policy.name, records)
    payload = {"summary": summary, "records": records}
    (args.out_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{CYAN}DONE summary={json.dumps(summary, ensure_ascii=False)} out={args.out_dir / 'results.json'}{RESET}")


if __name__ == "__main__":
    main()
