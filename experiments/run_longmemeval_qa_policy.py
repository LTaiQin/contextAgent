import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "LightAgent"))

from benchmark_adapters.longmemeval_adapter import LongMemEvalAdapter  # noqa: E402
from benchmark_adapters.scoring import score_task  # noqa: E402


DEFAULT_OUT_DIR = PROJECT_ROOT / "experiments" / "runs" / "longmemeval_qa_policy"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 3.5))


def answer_session_hit(sample: dict[str, Any], selected_indexes: list[int]) -> bool:
    session_ids = sample.get("haystack_session_ids", [])
    selected_ids = {str(session_ids[index]) for index in selected_indexes if index < len(session_ids)}
    answer_ids = {str(item) for item in sample.get("answer_session_ids", [])}
    return bool(selected_ids & answer_ids)


def clear_default_tools(agent: Any) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


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


def build_query(adapter: LongMemEvalAdapter, sample: dict[str, Any], args: argparse.Namespace) -> tuple[str, list[int]]:
    if args.mode == "full":
        return adapter.build_query(sample), list(range(len(sample.get("haystack_sessions", []))))
    selected = adapter.select_session_indexes(sample, mode=args.mode, max_sessions=args.max_sessions)
    query = adapter.build_compact_context(
        sample,
        mode=args.mode,
        max_sessions=args.max_sessions,
        max_turns_per_session=args.max_turns_per_session,
        turn_mode=args.turn_mode,
    )
    return query, selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="s_cleaned")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mode", choices=["oracle", "lexical", "full"], default="oracle")
    parser.add_argument("--max-sessions", type=int, default=3)
    parser.add_argument("--max-turns-per-session", type=int, default=4)
    parser.add_argument("--turn-mode", choices=["first_n", "last_n", "ranked", "full"], default="first_n")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default="https://www.cctq.ai/v1")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    adapter = LongMemEvalAdapter()
    samples = adapter.load_samples(split=args.split, limit=args.limit)
    agent = None if args.dry_run else make_agent(args)
    records = []

    print(
        f"{CYAN}LongMemEval QA run split={args.split} mode={args.mode} limit={len(samples)} "
        f"turn_mode={args.turn_mode} dry_run={args.dry_run}{RESET}",
        flush=True,
    )

    for index, sample in enumerate(samples, start=1):
        unit = adapter.build_task_unit(sample)
        full_query = adapter.build_query(sample)
        query, selected_indexes = build_query(adapter, sample, args)
        full_tokens = estimate_tokens(full_query)
        query_tokens = estimate_tokens(query)
        hit = answer_session_hit(sample, selected_indexes)

        print(
            f"{MAGENTA}=== sample {index}/{len(samples)} task={unit.task_uid} "
            f"type={unit.metadata.get('question_type')} mode={args.mode} "
            f"tokens={full_tokens}->{query_tokens} answer_hit={hit}{RESET}",
            flush=True,
        )

        if args.dry_run:
            content = str(unit.gold)
            error = None
            trace = []
        else:
            try:
                assert agent is not None
                agent.instructions = (
                    "Answer the benchmark question using only the supplied conversation evidence. "
                    "Return a concise answer phrase, not a long explanation."
                )
                agent.role = "LongMemEval QA evaluator."
                result = agent.run(
                    query,
                    history=[],
                    tools=[],
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

        score = score_task(unit, content, error).to_dict()
        status = "PASS" if score["benchmark_score"] and not error else "FAIL"
        color = GREEN if status == "PASS" else RED
        print(
            f"{color}[score] status={status} scored={score['benchmark_scored']} "
            f"type={score['score_type']} error={error}{RESET}",
            flush=True,
        )
        print(f"[answer] pred={content[:300].replace(chr(10), ' ')} gold={unit.gold}", flush=True)

        record = {
            "n": index,
            "task_uid": unit.task_uid,
            "question_id": unit.metadata.get("question_id"),
            "question_type": unit.metadata.get("question_type"),
            "mode": args.mode,
            "turn_mode": args.turn_mode,
            "selected_session_indexes": selected_indexes,
            "answer_session_hit": hit,
            "full_input_tokens_est": full_tokens,
            "query_input_tokens_est": query_tokens,
            "compression_ratio": round(query_tokens / full_tokens, 4),
            "content": content,
            "error": error,
            "status": status,
            "score": score,
            "gold": unit.gold,
            "agent_trace": trace,
        }
        records.append(record)
        (args.out_dir / f"sample_{index:03d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary = {
        "split": args.split,
        "mode": args.mode,
        "dry_run": args.dry_run,
        "total": len(records),
        "pass": sum(1 for item in records if item["status"] == "PASS"),
        "answer_session_hit": sum(1 for item in records if item["answer_session_hit"]),
        "full_input_tokens_est_total": sum(item["full_input_tokens_est"] for item in records),
        "query_input_tokens_est_total": sum(item["query_input_tokens_est"] for item in records),
        "avg_compression_ratio": round(
            sum(item["compression_ratio"] for item in records) / len(records), 4
        )
        if records
        else 0,
    }
    payload = {"summary": summary, "records": records}
    (args.out_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{CYAN}DONE summary={json.dumps(summary, ensure_ascii=False)} out={args.out_dir / 'results.json'}{RESET}")


if __name__ == "__main__":
    main()
