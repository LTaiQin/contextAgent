from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
RUNS_DIR = PROJECT_ROOT / "experiments" / "runs"
DEFAULT_OUT = PROJECT_ROOT / "experiment-notes" / "phase-5-small-results-summary-2026-06-02.md"


@dataclass
class RunSummary:
    benchmark: str
    run_name: str
    policy: str
    mode: str
    total: int
    passed: int | None
    scored: int | None
    input_tokens_est: int | None
    notes: str

    @property
    def score_text(self) -> str:
        if self.passed is None:
            return "-"
        denom = self.scored or self.total
        if denom <= 0:
            return f"{self.passed}/0"
        return f"{self.passed}/{denom} ({self.passed / denom:.1%})"

    @property
    def token_text(self) -> str:
        if self.input_tokens_est is None:
            return "-"
        return f"{self.input_tokens_est / 1_000_000:.4f}M"


KEY_RUNS = [
    "agentif_baseline_20_cctq_gpt54",
    "agentif_same_session_full_session_3_cctq_gpt54_compare",
    "agentif_same_session_recent_n_3_cctq_gpt54_compare",
    "agentif_same_session_task_scoped_3_cctq_gpt54_compare",
    "math_algebra_baseline_10_cctq_gpt54",
    "math_same_session_full_session_3_cctq_gpt54_compare",
    "math_same_session_recent_n_3_cctq_gpt54_compare",
    "math_same_session_task_scoped_3_cctq_gpt54_compare",
    "mixed_old_constraint_full_session_5_filtered_cctq_gpt54_compare",
    "mixed_old_constraint_recent_n_5_filtered_cctq_gpt54_compare",
    "mixed_old_constraint_task_scoped_5_filtered_cctq_gpt54_compare",
    "bfcl_scorer_smoke",
    "bfcl_tool_stress_full_session_dryrun_v3",
    "bfcl_tool_stress_recent_n_dryrun_v3",
    "bfcl_tool_stress_task_scoped_dryrun_v4",
    "longmemeval_retrieval_oracle_smoke",
    "longmemeval_retrieval_lexical_smoke",
    "longmemeval_qa_oracle_3_cctq_gpt54",
    "longmemeval_qa_oracle_ranked_3_cctq_gpt54",
    "longmemeval_qa_lexical_3_turn20_cctq_gpt54",
    "longmemeval_retrieval_lexical_turn_weighted_smoke20",
    "longmemeval_retrieval_lexical_turn_weighted_smoke100",
    "longmemeval_qa_lexical_turn_weighted_3_cctq_gpt54",
    "longmemeval_qa_lexical_turn_weighted_prompt_3_cctq_gpt54",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-all", action="store_true")
    args = parser.parse_args()

    run_names = sorted(path.name for path in args.runs_dir.iterdir() if (path / "results.json").exists())
    if not args.include_all:
        run_names = [name for name in KEY_RUNS if (args.runs_dir / name / "results.json").exists()]

    summaries = [summarize_run(args.runs_dir / name / "results.json") for name in run_names]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(summaries), encoding="utf-8")
    print(f"Wrote {args.out}")


def summarize_run(path: Path) -> RunSummary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    run_name = path.parent.name
    benchmark = infer_benchmark(run_name)

    if isinstance(payload, dict) and "summary" in payload:
        summary = payload.get("summary") or {}
        records = payload.get("records") or []
        policy = str(summary.get("policy") or first_value(records, "policy") or "-")
        mode = str(summary.get("mode") or summary.get("template") or first_value(records, "mode") or "-")
        total = int(summary.get("total") or len(records))
        passed = pick_int(summary, "pass", "benchmark_pass", "context_ok")
        scored = pick_int(summary, "benchmark_scored") or total
        tokens = pick_int(summary, "query_input_tokens_est_total", "input_tokens_est_total")
        notes = note_from_summary(summary)
        return RunSummary(benchmark, run_name, policy, mode, total, passed, scored, tokens, notes)

    records = payload if isinstance(payload, list) else list(payload.values()) if isinstance(payload, dict) else []
    policy = str(first_value(records, "policy") or "-")
    total = len(records)
    passed = count_passed(records)
    scored = count_scored(records) or total
    tokens = sum_int(records, "input_tokens_est", "query_input_tokens_est")
    notes = "-"
    return RunSummary(benchmark, run_name, policy, "-", total, passed, scored, tokens or None, notes)


def infer_benchmark(run_name: str) -> str:
    if run_name.startswith("agentif"):
        return "AgentIF"
    if run_name.startswith("math"):
        return "MATH"
    if run_name.startswith("mixed"):
        return "Mixed Session"
    if run_name.startswith("bfcl"):
        return "BFCL"
    if run_name.startswith("longmemeval"):
        return "LongMemEval"
    return "Other"


def first_value(records: list[dict[str, Any]], key: str) -> Any:
    for record in records:
        if isinstance(record, dict) and record.get(key) not in (None, ""):
            return record[key]
    return None


def pick_int(mapping: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return None


def count_passed(records: list[dict[str, Any]]) -> int | None:
    if not records:
        return None
    passed = 0
    observed = False
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("status") in {"PASS", "pass", "correct"}:
            passed += 1
            observed = True
        elif record.get("correct_normalized") is True or record.get("correct_raw") is True:
            passed += 1
            observed = True
        elif record.get("code_score_passed") is not None and record.get("code_score_total") is not None:
            passed += int(record.get("code_score_passed") or 0) == int(record.get("code_score_total") or 0)
            observed = True
        elif isinstance(record.get("score"), dict) and record["score"].get("benchmark_score") is not None:
            passed += bool(record["score"].get("benchmark_score"))
            observed = True
    return passed if observed else None


def count_scored(records: list[dict[str, Any]]) -> int | None:
    if not records:
        return None
    scored = 0
    observed = False
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("code_score_total") is not None:
            scored += int(record.get("code_score_total") or 0) > 0
            observed = True
        elif isinstance(record.get("score"), dict) and record["score"].get("benchmark_scored") is not None:
            scored += bool(record["score"].get("benchmark_scored"))
            observed = True
        elif any(key in record for key in ("status", "correct_normalized", "correct_raw")):
            scored += 1
            observed = True
    return scored if observed else None


def sum_int(records: list[dict[str, Any]], *keys: str) -> int:
    total = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in keys:
            value = record.get(key)
            if isinstance(value, (int, float)):
                total += int(value)
                break
            context = record.get("context_summary")
            if isinstance(context, dict) and isinstance(context.get(key), (int, float)):
                total += int(context[key])
                break
    return total


def note_from_summary(summary: dict[str, Any]) -> str:
    details = []
    if "answer_session_hit" in summary:
        details.append(f"answer session hit {summary['answer_session_hit']}/{summary.get('total', '?')}")
    if "avg_compression_ratio" in summary:
        details.append(f"compression {summary['avg_compression_ratio']}")
    if "unnecessary_context" in summary:
        details.append(f"unnecessary context {summary['unnecessary_context']}")
    if "forbidden_inclusion" in summary:
        details.append(f"forbidden inclusion {summary['forbidden_inclusion']}")
    return "; ".join(details) if details else "-"


def render_markdown(summaries: list[RunSummary]) -> str:
    lines = [
        "# Phase 5 小样本实验汇总",
        "",
        "生成日期: 2026-06-02。",
        "",
        "这份表只汇总当前已经落盘的小样本/烟测结果，用于判断实验链路是否跑通，以及下一步应优先补哪类实验。它还不能代表论文级最终结论。",
        "",
        "| Benchmark | Run | Policy | Mode/Template | N | Score | Input Tokens Est | Notes |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in summaries:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.benchmark,
                    f"`{item.run_name}`",
                    f"`{item.policy}`",
                    f"`{item.mode}`",
                    str(item.total),
                    item.score_text,
                    item.token_text,
                    item.notes,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 当前判断",
            "",
            "1. AgentIF、MATH、Mixed Session 主要验证同一 session 中的上下文隔离接口、need gate 和 task boundary 是否能稳定工作。",
            "2. BFCL 已接入官方 scorer 的直接 checker，说明工具调用类 benchmark 的评分链路可以复用公开标准。",
            "3. LongMemEval 的关键发现是: 只选中正确 session 还不够，session 内部 turn ranking 明显影响答案和 token 成本。",
            "4. 当前最需要补的是非 oracle 的 LongMemEval 检索策略，以及更系统的同一 session 混合任务大样本协议。",
            "",
            "## 下一步",
            "",
            "1. 改进 LongMemEval lexical 检索: 从整段 session overlap 改为 turn-level max/mean + role/date/answer-like boost。",
            "2. 对改进检索先跑 dry-run，再用 3 到 5 条真实模型调用验证是否超过旧 lexical。",
            "3. 把混合 session 验证从手工模板扩展为可配置的 benchmark mixer，以 task 为单位打乱但保留可控冲突规则。",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
