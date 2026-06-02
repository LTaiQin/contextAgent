import json
from pathlib import Path

from benchmark_adapters.bfcl_adapter import BFCLAdapter
from benchmark_adapters.bfcl_scoring import expected_calls, score_bfcl


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/bfcl_scorer_smoke")


def content_from_gold(gold) -> str:
    calls = expected_calls(gold)
    return "\n".join(
        f"{call.name}({', '.join(f'{key}={example_value(value)!r}' for key, value in call.args.items())})"
        for call in calls
    )


def example_value(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adapter = BFCLAdapter()
    records = []
    for category in ["simple", "multi_turn_base"]:
        units = adapter.build_session(category=category, limit=3)
        for index, unit in enumerate(units, start=1):
            content = content_from_gold(unit.gold)
            score = score_bfcl(content, unit.gold)
            record = {
                "category": category,
                "n": index,
                "task_uid": unit.task_uid,
                "content": content,
                "score": score,
            }
            records.append(record)
            print(
                f"BFCL scorer category={category} {index}/{len(units)} "
                f"task={unit.task_uid} score={score['benchmark_score']} "
                f"matched={score['matched_call_count']}/{score['expected_call_count']}"
            )
            if not score["benchmark_score"]:
                raise AssertionError(f"Expected generated gold content to pass for {unit.task_uid}")
    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
