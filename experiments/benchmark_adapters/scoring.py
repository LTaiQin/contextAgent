from __future__ import annotations

from typing import Any

from .core import BenchmarkScore, TaskUnit


def evaluate_agentif_code_constraints(response: str, constraints: list[dict[str, Any]]) -> tuple[int, int, list[dict[str, Any]]]:
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


def score_task(unit: TaskUnit, content: str, error: str | None) -> BenchmarkScore:
    from math_eval import extract_prediction, score_prediction

    if unit.source_benchmark == "MATH":
        prediction = extract_prediction(content)
        score = score_prediction(prediction, str(unit.gold))
        return BenchmarkScore(
            benchmark_score=bool(score["correct_normalized"] and not error),
            score_type="math_boxed_normalized",
            details={
                "prediction": prediction,
                "gold": unit.gold,
                "correct_raw": score["correct_raw"],
                "correct_normalized": score["correct_normalized"],
            },
        )
    if unit.source_benchmark == "AgentIF":
        passed, total, details = evaluate_agentif_code_constraints(content, unit.constraints)
        return BenchmarkScore(
            benchmark_score=bool(total and passed == total and not error),
            benchmark_scored=bool(total),
            score_type="agentif_code_constraints",
            details={
                "code_score_passed": passed,
                "code_score_total": total,
            },
            eval_details=details,
        )
    if unit.source_benchmark == "BFCL":
        from .bfcl_scoring import score_bfcl

        score = score_bfcl(content, unit.gold)
        return BenchmarkScore(
            benchmark_score=score.pop("benchmark_score"),
            benchmark_scored=score.pop("benchmark_scored"),
            score_type=score.pop("score_type"),
            details=score,
        )
    if unit.source_benchmark == "LongMemEval":
        from .longmemeval_adapter import score_longmemeval_string

        score = score_longmemeval_string(content, unit.gold)
        return BenchmarkScore(
            benchmark_score=score.pop("benchmark_score"),
            benchmark_scored=score.pop("benchmark_scored"),
            score_type=score.pop("score_type"),
            details=score,
        )
    return BenchmarkScore(
        benchmark_score=False,
        benchmark_scored=False,
        score_type="unsupported",
    )
