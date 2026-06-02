from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from benchmark_adapters.longmemeval_adapter import LongMemEvalAdapter  # noqa: E402


DEFAULT_RESULTS = (
    PROJECT_ROOT
    / "experiments"
    / "runs"
    / "longmemeval_retrieval_lexical_turn_weighted_smoke100"
    / "results.json"
)
DEFAULT_OUT = PROJECT_ROOT / "experiment-notes" / "longmemeval-retrieval-miss-analysis-2026-06-02.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--split", default="s_cleaned")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--top-turns", type=int, default=3)
    args = parser.parse_args()

    payload = json.loads(args.results.read_text(encoding="utf-8"))
    misses = [record for record in payload.get("records", []) if not record.get("answer_session_hit")]
    adapter = LongMemEvalAdapter()
    samples = adapter.load_samples(split=args.split)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_report(adapter, samples, misses, args.top_turns), encoding="utf-8")
    print(f"Wrote {args.out}")


def render_report(
    adapter: LongMemEvalAdapter,
    samples: list[dict[str, Any]],
    misses: list[dict[str, Any]],
    top_turns: int,
) -> str:
    lines = [
        "# LongMemEval 检索失败分析",
        "",
        "日期: 2026-06-02。",
        "",
        "来源: `longmemeval_retrieval_lexical_turn_weighted_smoke100`。",
        "",
        f"失败条数: {len(misses)}。",
        "",
        "## 总览",
        "",
        "| N | Question ID | Type | Gold | Selected Sessions | Answer Sessions | 初步类型 |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for miss in misses:
        sample = samples[int(miss["n"]) - 1]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(miss["n"]),
                    f"`{sample.get('question_id')}`",
                    str(sample.get("question_type")),
                    clean_cell(sample.get("answer")),
                    ", ".join(map(str, miss.get("selected_session_indexes", []))),
                    ", ".join(map(str, answer_indexes(sample))),
                    classify_miss(sample),
                ]
            )
            + " |"
        )

    lines.extend(["", "## 逐条分析", ""])
    for miss in misses:
        sample = samples[int(miss["n"]) - 1]
        lines.extend(render_one(adapter, sample, miss, top_turns))
    return "\n".join(lines) + "\n"


def render_one(
    adapter: LongMemEvalAdapter,
    sample: dict[str, Any],
    miss: dict[str, Any],
    top_turns: int,
) -> list[str]:
    lines = [
        f"### {miss['n']}. `{sample.get('question_id')}`",
        "",
        f"- 问题: {sample.get('question')}",
        f"- Gold: {sample.get('answer')}",
        f"- 类型: {sample.get('question_type')}",
        f"- 初步失败类型: {classify_miss(sample)}",
        "",
        "正确 session 证据:",
    ]
    for session_index in answer_indexes(sample):
        lines.extend(render_session_turns(adapter, sample, session_index, top_turns))
    lines.append("")
    lines.append("误选 session 证据:")
    for session_index in miss.get("selected_session_indexes", []):
        lines.extend(render_session_turns(adapter, sample, int(session_index), top_turns))
    lines.append("")
    return lines


def render_session_turns(
    adapter: LongMemEvalAdapter,
    sample: dict[str, Any],
    session_index: int,
    top_turns: int,
) -> list[str]:
    session_ids = sample.get("haystack_session_ids", [])
    session_id = session_ids[session_index] if session_index < len(session_ids) else f"session_{session_index}"
    lines = [f"- Session {session_index}: `{session_id}`"]
    for turn_index in adapter.rank_turns_weighted(sample, session_index)[:top_turns]:
        turn = sample["haystack_sessions"][session_index][turn_index]
        role = turn.get("role", "user")
        content = " ".join(str(turn.get("content", "")).split())
        lines.append(f"  - turn {turn_index} {role}: {content[:420]}")
    return lines


def answer_indexes(sample: dict[str, Any]) -> list[int]:
    answer_ids = {str(item) for item in sample.get("answer_session_ids", [])}
    session_ids = [str(item) for item in sample.get("haystack_session_ids", [])]
    return [index for index, session_id in enumerate(session_ids) if session_id in answer_ids]


def classify_miss(sample: dict[str, Any]) -> str:
    question = str(sample.get("question", "")).lower()
    answer = str(sample.get("answer", "")).lower()
    if "not mention" in answer or "did not mention" in answer:
        return "negative/unanswerable"
    if sample.get("question_type") == "multi-session":
        if any(term in question for term in ("how many", "how long", "different", "total")):
            return "multi-session aggregation"
        return "multi-session retrieval"
    return "paraphrase/low-overlap"


def clean_cell(value: Any) -> str:
    text = " ".join(str(value).split())
    text = text.replace("|", "\\|")
    return text[:120]


if __name__ == "__main__":
    main()
