from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from benchmark_adapters.longmemeval_adapter import LongMemEvalAdapter  # noqa: E402


DEFAULT_OUT_DIR = PROJECT_ROOT / "experiments" / "runs" / "longmemeval_adaptive_budget_sweep"


@dataclass(frozen=True)
class SweepConfig:
    name: str
    single_next_ratio: float
    single_gap: float
    single_budget: int
    multi_budget: int


@dataclass
class PreparedSample:
    sample: dict[str, Any]
    scored: list[tuple[float, int]]
    ranked: list[int]
    session_token_est: dict[int, int]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="s_cleaned")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--base-sessions", type=int, default=3)
    parser.add_argument("--max-turns-per-session", type=int, default=4)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    adapter = LongMemEvalAdapter()
    samples = adapter.load_samples(split=args.split, limit=args.limit)
    prepared = [prepare_sample(adapter, sample, args.max_turns_per_session) for sample in samples]
    configs = build_configs()
    results = [
        evaluate_config(prepared, config, args.base_sessions)
        for config in configs
    ]
    results.sort(key=lambda item: (-item["answer_session_hit"], item["compact_input_tokens_est_total"]))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"split": args.split, "limit": len(samples), "results": results}
    (args.out_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "summary.md").write_text(render_markdown(results), encoding="utf-8")

    print(render_markdown(results[:12]))
    print(f"Wrote {args.out_dir / 'results.json'}")


def build_configs() -> list[SweepConfig]:
    configs = [
        SweepConfig("fixed3", single_next_ratio=2.0, single_gap=-1.0, single_budget=3, multi_budget=3),
        SweepConfig("fixed8", single_next_ratio=0.0, single_gap=1.0, single_budget=8, multi_budget=8),
    ]
    for multi_budget in (6, 8):
        for single_budget in (3, 6):
            for next_ratio in (0.78, 0.84, 0.90):
                for gap in (0.03, 0.05):
                    name = f"adaptive_s{single_budget}_m{multi_budget}_r{next_ratio:.2f}_g{gap:.2f}"
                    configs.append(
                        SweepConfig(
                            name=name,
                            single_next_ratio=next_ratio,
                            single_gap=gap,
                            single_budget=single_budget,
                            multi_budget=multi_budget,
                        )
                    )
    return configs


def prepare_sample(
    adapter: LongMemEvalAdapter,
    sample: dict[str, Any],
    max_turns_per_session: int,
) -> PreparedSample:
    scored = adapter.score_sessions_by_turn_evidence(sample)
    ranked = [index for score, index in scored if score > 0]
    ranked = ranked[:8]
    session_token_est = {
        session_index: estimate_tokens(
            build_session_block(adapter, sample, session_index, max_turns_per_session)
        )
        for session_index in ranked
    }
    return PreparedSample(sample=sample, scored=scored, ranked=ranked, session_token_est=session_token_est)


def evaluate_config(
    prepared_samples: list[PreparedSample],
    config: SweepConfig,
    base_sessions: int,
) -> dict[str, Any]:
    records = []
    for prepared in prepared_samples:
        sample = prepared.sample
        selected = select_with_config(prepared, config, base_sessions)
        compact_tokens = estimate_query_tokens(sample, selected, prepared.session_token_est)
        record = {
            "question_id": sample.get("question_id"),
            "question_type": sample.get("question_type"),
            "selected_count": len(selected),
            "answer_session_hit": hit_answer_session(sample, selected),
            "compact_input_tokens_est": compact_tokens,
        }
        records.append(record)
    total_tokens = sum(item["compact_input_tokens_est"] for item in records)
    budget_distribution: dict[str, int] = {}
    for record in records:
        key = str(record["selected_count"])
        budget_distribution[key] = budget_distribution.get(key, 0) + 1
    return {
        "name": config.name,
        "single_next_ratio": config.single_next_ratio,
        "single_gap": config.single_gap,
        "single_budget": config.single_budget,
        "multi_budget": config.multi_budget,
        "total": len(records),
        "answer_session_hit": sum(1 for item in records if item["answer_session_hit"]),
        "compact_input_tokens_est_total": total_tokens,
        "compact_input_tokens_est_M": round(total_tokens / 1_000_000, 4),
        "budget_distribution": budget_distribution,
        "single_session_hit": sum(
            1
            for item in records
            if item["question_type"] == "single-session-user" and item["answer_session_hit"]
        ),
        "single_session_total": sum(1 for item in records if item["question_type"] == "single-session-user"),
        "multi_session_hit": sum(
            1 for item in records if item["question_type"] == "multi-session" and item["answer_session_hit"]
        ),
        "multi_session_total": sum(1 for item in records if item["question_type"] == "multi-session"),
    }


def select_with_config(
    prepared: PreparedSample,
    config: SweepConfig,
    base_sessions: int,
) -> list[int]:
    sample = prepared.sample
    scored = prepared.scored
    ranked = prepared.ranked
    if not ranked:
        return []
    question_type = str(sample.get("question_type", ""))
    if config.name == "fixed3":
        return ranked[:base_sessions]
    if config.name == "fixed8":
        return ranked[:8]
    if question_type == "multi-session":
        return ranked[: config.multi_budget]
    budget = single_session_budget(scored, config, base_sessions)
    return ranked[:budget]


def single_session_budget(scored: list[tuple[float, int]], config: SweepConfig, base_sessions: int) -> int:
    positive_scores = [score for score, _index in scored if score > 0]
    if len(positive_scores) <= base_sessions:
        return len(positive_scores)
    top_score = positive_scores[0]
    kth_score = positive_scores[base_sessions - 1]
    next_score = positive_scores[base_sessions]
    if top_score <= 0:
        return base_sessions
    next_ratio = next_score / top_score
    boundary_gap = (kth_score - next_score) / top_score
    if next_ratio >= config.single_next_ratio or boundary_gap <= config.single_gap:
        return max(base_sessions, config.single_budget)
    return base_sessions


def estimate_query_tokens(
    sample: dict[str, Any],
    selected_indexes: list[int],
    session_token_est: dict[int, int],
) -> int:
    overhead = estimate_tokens("LongMemEval sweep\nConversation evidence:\n\nQuestion:\n" + str(sample.get("question", "")))
    return overhead + sum(session_token_est.get(index, 0) for index in selected_indexes)


def build_session_block(
    adapter: LongMemEvalAdapter,
    sample: dict[str, Any],
    session_index: int,
    max_turns_per_session: int,
) -> str:
    sessions = sample.get("haystack_sessions", [])
    session_ids = sample.get("haystack_session_ids", [])
    session_id = session_ids[session_index] if session_index < len(session_ids) else f"session_{session_index}"
    parts = [f"\n[Session {session_index + 1}: {session_id}]"]
    for turn_index in adapter.rank_turns_weighted(sample, session_index)[:max_turns_per_session]:
        turn = sessions[session_index][turn_index]
        parts.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
    return "\n".join(parts)


def hit_answer_session(sample: dict[str, Any], selected_indexes: list[int]) -> bool:
    session_ids = sample.get("haystack_session_ids", [])
    selected_ids = {str(session_ids[index]) for index in selected_indexes if index < len(session_ids)}
    answer_ids = {str(item) for item in sample.get("answer_session_ids", [])}
    return bool(selected_ids & answer_ids)


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 3.5))


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "# LongMemEval Adaptive Budget Sweep",
        "",
        "| Config | Hit | Tokens | Single | Multi | Budget Dist |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['name']}`",
                    f"{item['answer_session_hit']}/{item['total']}",
                    f"{item['compact_input_tokens_est_M']}M",
                    f"{item['single_session_hit']}/{item['single_session_total']}",
                    f"{item['multi_session_hit']}/{item['multi_session_total']}",
                    json.dumps(item["budget_distribution"], ensure_ascii=False, sort_keys=True),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
