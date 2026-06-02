import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from benchmark_adapters.longmemeval_adapter import LongMemEvalAdapter  # noqa: E402
from benchmark_adapters.scoring import score_task  # noqa: E402


OUT_DIR_DEFAULT = PROJECT_ROOT / "experiments" / "runs" / "longmemeval_retrieval_smoke"

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 3.5))


def hit_answer_session(sample: dict[str, Any], selected_indexes: list[int]) -> bool:
    session_ids = sample.get("haystack_session_ids", [])
    selected_ids = {str(session_ids[index]) for index in selected_indexes if index < len(session_ids)}
    answer_ids = {str(item) for item in sample.get("answer_session_ids", [])}
    return bool(selected_ids & answer_ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="s_cleaned")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mode", choices=["oracle", "lexical", "lexical_turn"], default="oracle")
    parser.add_argument("--max-sessions", type=int, default=3)
    parser.add_argument("--max-turns-per-session", type=int, default=4)
    parser.add_argument("--turn-mode", choices=["first_n", "last_n", "ranked", "weighted", "full"], default="first_n")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    adapter = LongMemEvalAdapter()
    samples = adapter.load_samples(split=args.split, limit=args.limit)
    records = []

    print(
        f"{CYAN}LongMemEval retrieval smoke split={args.split} mode={args.mode} limit={len(samples)} "
        f"max_sessions={args.max_sessions} max_turns={args.max_turns_per_session}{RESET}",
        flush=True,
    )

    for index, sample in enumerate(samples, start=1):
        unit = adapter.build_task_unit(sample)
        full_query = adapter.build_query(sample)
        compact_query = adapter.build_compact_context(
            sample,
            mode=args.mode,
            max_sessions=args.max_sessions,
            max_turns_per_session=args.max_turns_per_session,
            turn_mode=args.turn_mode,
        )
        selected_indexes = adapter.select_session_indexes(sample, mode=args.mode, max_sessions=args.max_sessions)
        score = score_task(unit, str(unit.gold), None).to_dict()
        full_tokens = estimate_tokens(full_query)
        compact_tokens = estimate_tokens(compact_query)
        compression_ratio = round(compact_tokens / full_tokens, 4)
        answer_hit = hit_answer_session(sample, selected_indexes)
        record = {
            "n": index,
            "task_uid": unit.task_uid,
            "question_type": unit.metadata.get("question_type"),
            "haystack_session_count": unit.metadata.get("haystack_session_count"),
            "selected_session_indexes": selected_indexes,
            "answer_session_hit": answer_hit,
            "full_query_chars": len(full_query),
            "compact_query_chars": len(compact_query),
            "full_input_tokens_est": full_tokens,
            "compact_input_tokens_est": compact_tokens,
            "compression_ratio": compression_ratio,
            "gold": unit.gold,
            "score": score,
        }
        records.append(record)
        color = GREEN if answer_hit else YELLOW
        print(
            f"{color}sample {index}/{len(samples)} task={unit.task_uid} type={record['question_type']} "
            f"sessions={record['haystack_session_count']} selected={selected_indexes} "
            f"answer_hit={answer_hit} tokens={full_tokens}->{compact_tokens} "
            f"ratio={compression_ratio}{RESET}",
            flush=True,
        )

    summary = {
        "split": args.split,
        "mode": args.mode,
        "turn_mode": args.turn_mode,
        "total": len(records),
        "answer_session_hit": sum(1 for item in records if item["answer_session_hit"]),
        "full_input_tokens_est_total": sum(item["full_input_tokens_est"] for item in records),
        "compact_input_tokens_est_total": sum(item["compact_input_tokens_est"] for item in records),
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
