import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "LightAgent"))

from context_isolation import (  # noqa: E402
    FullSessionPolicy,
    NeedGatedPolicy,
    RecentNPolicy,
    RetrievalOnlyPolicy,
    TaskScopedPolicy,
)


DATA_PATH = PROJECT_ROOT / "data" / "agentif" / "eval.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "experiments" / "runs" / "agentif_same_session_policy"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


def sample_size(sample: dict[str, Any]) -> int:
    text = "\n".join(message.get("content", "") for message in sample.get("input", []))
    constraints = json.dumps(sample.get("constraints", []), ensure_ascii=False)
    return len(text) + len(constraints)


def select_samples(data: list[dict[str, Any]], limit: int) -> list[tuple[int, dict[str, Any]]]:
    ranked = sorted((sample_size(sample), idx, sample) for idx, sample in enumerate(data))
    return [(idx, sample) for _, idx, sample in ranked[:limit]]


def split_messages(sample: dict[str, Any]) -> tuple[str, str]:
    system_parts = [message["content"] for message in sample["input"] if message.get("role") == "system"]
    user_parts = [message["content"] for message in sample["input"] if message.get("role") == "user"]
    system_text = "\n\n".join(system_parts)
    query = "\n\n".join(user_parts)
    constraints = sample.get("constraints", [])
    if constraints:
        query += "\n\nBenchmark constraints:\n" + json.dumps(constraints, ensure_ascii=False, indent=2)
    return system_text, query


def evaluate_code_constraints(response: str, constraints: list[dict[str, Any]]) -> tuple[int, int, list[dict[str, Any]]]:
    details = []
    total = 0
    passed = 0
    for constraint in constraints:
        evaluations = constraint.get("evaluation") or []
        for evaluation in evaluations:
            if evaluation.get("type") != "code" or not evaluation.get("exec"):
                continue
            total += 1
            namespace: dict[str, Any] = {}
            ok = False
            error = None
            try:
                exec(evaluation["exec"], namespace)
                checker = namespace.get("check_following")
                if callable(checker):
                    ok = bool(checker(response))
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            if ok:
                passed += 1
            details.append(
                {
                    "constraint_id": constraint.get("id"),
                    "desc": constraint.get("desc"),
                    "passed": ok,
                    "error": error,
                }
            )
    return passed, total, details


def clear_default_tools(agent: Any) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


def make_policy(name: str):
    if name == "full_session":
        return FullSessionPolicy()
    if name == "recent_n":
        return RecentNPolicy(n=4)
    if name == "retrieval_only":
        return RetrievalOnlyPolicy(top_k=4)
    if name == "need_gated":
        return NeedGatedPolicy(max_turns=6)
    if name == "task_scoped":
        return TaskScopedPolicy(max_task_turns=6)
    raise ValueError(f"Unsupported policy: {name}")


def make_agent(args: argparse.Namespace):
    from LightAgent import LightAgent

    agent = LightAgent(
        model=os.environ.get("CCTQ_MODEL", args.model),
        api_key=os.environ["CCTQ_API_KEY"],
        base_url=os.environ.get("CCTQ_BASE_URL", args.base_url),
        auto_discover_skills=False,
        tree_of_thought=False,
        self_learning=False,
    )
    clear_default_tools(agent)
    return agent


def estimate_tokens_from_messages(messages: list[dict[str, Any]], current_message: str, system_text: str) -> int:
    chars = len(system_text) + len(current_message) + sum(len(str(item.get("content", ""))) for item in messages)
    return max(1, round(chars / 3.5))


def dry_run_content(sample: dict[str, Any]) -> str:
    output = sample.get("output")
    if isinstance(output, str) and output.strip():
        return output
    return "DRY_RUN_OUTPUT"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--policy", default="task_scoped")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default="https://www.cctq.ai/v1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    samples = select_samples(data, args.limit)
    policy = make_policy(args.policy)
    agent = None if args.dry_run else make_agent(args)
    raw_history: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    print(
        f"{CYAN}AgentIF same-session policy run policy={policy.name} limit={len(samples)} dry_run={args.dry_run}{RESET}",
        flush=True,
    )

    for n, (idx, sample) in enumerate(samples, start=1):
        task_id = f"agentif_{n:04d}"
        system_text, query = split_messages(sample)
        selected = policy.select(
            session_id="agentif_same_session",
            user_id="benchmark_user",
            current_message=query,
            raw_history=raw_history,
            available_tools=[],
        )
        selected_token_est = estimate_tokens_from_messages(selected.messages, query, system_text)
        context_summary = {
            "policy": policy.name,
            "need_type": selected.decision.need_type,
            "boundary": selected.decision.boundary,
            "task_id": selected.decision.task_id,
            "confidence": selected.decision.confidence,
            "selected_turn_ids": selected.decision.selected_turn_ids,
            "selected_memory_ids": selected.decision.selected_memory_ids,
            "selected_tools": selected.decision.selected_tools,
            "suppressed_tools": selected.decision.suppressed_tools,
            "raw_history_count": len(raw_history),
            "selected_history_count": len(selected.messages),
            "input_tokens_est": selected_token_est,
            "reason": selected.decision.reason,
        }

        print(f"{BLUE}=== task {n}/{len(samples)} idx={idx} id={sample['id']} ==={RESET}", flush=True)
        print(
            f"{MAGENTA}[context] policy={policy.name} boundary={selected.decision.boundary} "
            f"need={selected.decision.need_type} selected_turns={selected.decision.selected_turn_ids} "
            f"history_all={len(raw_history)} history_selected={len(selected.messages)} "
            f"input_tokens_est={selected_token_est}{RESET}",
            flush=True,
        )
        print(f"{YELLOW}[reason] {selected.decision.reason}{RESET}", flush=True)

        if args.dry_run:
            content = dry_run_content(sample)
            error = None
            trace = []
        else:
            try:
                assert agent is not None
                agent.instructions = "\n\n".join(
                    part
                    for part in [
                        system_text or "Follow the benchmark instruction exactly.",
                        selected.system_addendum,
                    ]
                    if part
                )
                agent.role = (
                    "AgentIF same-session evaluator. Follow only the current sample instruction "
                    "and the selected context supplied by the context policy."
                )
                result = agent.run(
                    query,
                    history=selected.messages,
                    tools=selected.tools,
                    result_format="object",
                    trace=True,
                    max_retry=2,
                    use_skills=False,
                    metadata={"max_tokens": args.max_tokens},
                )
                content = result.content
                error = result.error
                trace = result.trace
            except Exception as exc:
                content = ""
                error = f"{type(exc).__name__}: {exc}"
                trace = []

        passed, total, eval_details = evaluate_code_constraints(content, sample.get("constraints", []))
        status = "PASS" if total and passed == total and not error else ("NO_CODE_SCORE" if total == 0 and not error else "FAIL")
        color = GREEN if status == "PASS" else (YELLOW if status == "NO_CODE_SCORE" else RED)
        print(f"{color}[score] status={status} code_score={passed}/{total} error={error}{RESET}", flush=True)
        print(f"[answer_preview] {content[:500].replace(chr(10), ' ')}", flush=True)

        user_turn = {
            "turn_id": f"u_{n:04d}",
            "role": "user",
            "content": query,
            "task_id": task_id,
            "metadata": {
                "benchmark": "AgentIF",
                "sample_idx": idx,
                "sample_id": sample.get("id"),
            },
        }
        assistant_turn = {
            "turn_id": f"a_{n:04d}",
            "role": "assistant",
            "content": content,
            "task_id": task_id,
            "metadata": {
                "benchmark": "AgentIF",
                "sample_idx": idx,
                "sample_id": sample.get("id"),
                "status": status,
            },
        }
        raw_history.extend([user_turn, assistant_turn])

        record = {
            "n": n,
            "idx": idx,
            "id": sample["id"],
            "task_id": task_id,
            "policy": policy.name,
            "chars": sample_size(sample),
            "query_chars": len(query),
            "constraints_count": len(sample.get("constraints", [])),
            "content": content,
            "error": error,
            "code_score_passed": passed,
            "code_score_total": total,
            "status": status,
            "eval_details": eval_details,
            "context_summary": context_summary,
            "context_decision": selected.trace,
            "selected_messages": selected.messages,
            "agent_trace": trace,
        }
        results.append(record)
        (args.out_dir / f"sample_{n:03d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary_passed = sum(1 for item in results if item["status"] == "PASS")
        summary_failed = sum(1 for item in results if item["status"] == "FAIL")
        print(f"{CYAN}[running] pass={summary_passed} fail={summary_failed} done={len(results)}{RESET}", flush=True)

    (args.out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    print(f"{CYAN}DONE out={args.out_dir / 'results.json'} pass={pass_count} fail={fail_count} total={len(results)}{RESET}", flush=True)


if __name__ == "__main__":
    main()
