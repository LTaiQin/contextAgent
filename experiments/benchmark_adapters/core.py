from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaskUnit:
    task_uid: str
    source_benchmark: str
    domain: str
    task_type: str
    query: str
    system_text: str = ""
    gold: Any = None
    scorer: str = ""
    constraints: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkScore:
    benchmark_score: bool
    score_type: str
    benchmark_scored: bool = True
    details: dict[str, Any] = field(default_factory=dict)
    eval_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "benchmark_score": self.benchmark_score,
            "benchmark_scored": self.benchmark_scored,
            "score_type": self.score_type,
            "eval_details": self.eval_details,
        }
        payload.update(self.details)
        return payload


@dataclass
class BenchmarkResult:
    n: int
    template: str
    policy: str
    task_id: str
    task_uid: str
    source_benchmark: str
    domain: str
    task_type: str
    context_ok: bool
    benchmark_status: str
    context_summary: dict[str, Any]
    benchmark_score: dict[str, Any]
    content: str
    error: str | None = None
    gold_boundary: str = "new_task"
    gold_need_type: str = "no_context"
    gold_allowed_context_task_ids: list[str] = field(default_factory=list)
    gold_forbidden_context_task_ids: list[str] = field(default_factory=list)
    selected_task_ids: list[str] = field(default_factory=list)
    forbidden_context_task_ids_included: list[str] = field(default_factory=list)
    unnecessary_context: bool = False
    agent_trace: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_records(template: str, policy: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "template": template,
        "policy": policy,
        "total": len(records),
        "context_ok": sum(1 for item in records if item["context_ok"]),
        "benchmark_pass": sum(1 for item in records if item["benchmark_status"] == "PASS"),
        "benchmark_scored": sum(1 for item in records if item["benchmark_status"] in {"PASS", "FAIL"}),
        "benchmark_no_code_score": sum(1 for item in records if item["benchmark_status"] == "NO_CODE_SCORE"),
        "unnecessary_context": sum(1 for item in records if item["unnecessary_context"]),
        "forbidden_inclusion": sum(1 for item in records if item["forbidden_context_task_ids_included"]),
        "input_tokens_est_total": sum(item["context_summary"]["input_tokens_est"] for item in records),
    }
