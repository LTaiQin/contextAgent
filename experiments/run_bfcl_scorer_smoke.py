import json
from pathlib import Path

from benchmark_adapters.bfcl_adapter import BFCLAdapter
from benchmark_adapters.bfcl_scoring import expected_calls, score_bfcl_official


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/bfcl_scorer_smoke")


def content_from_gold(gold):
    calls = expected_calls(gold)
    if not calls:
        return []
    if isinstance(gold, list) and gold and isinstance(gold[0], list):
        rendered = []
        for turn in gold:
            turn_calls = []
            for call in expected_calls(turn):
                args_text = ", ".join(f"{key}={example_value(value)!r}" for key, value in call.args.items())
                turn_calls.append(f"{call.name}({args_text})")
            rendered.append([turn_calls])
        return rendered
    return [{call.name: {key: example_value(value) for key, value in call.args.items()}} for call in calls]


def content_from_multi_turn_gold(sample: dict) -> list[list[list[str]]]:
    turns = sample["ground_truth"]
    return [[turn] for turn in turns]


def example_value(value):
    if isinstance(value, list) and value:
        for item in value:
            if item != "":
                return item
        return value[0]
    return value


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adapter = BFCLAdapter()
    records = []
    for category in ["simple", "multi_turn_base"]:
        units = adapter.build_session(category=category, limit=3)
        for index, unit in enumerate(units, start=1):
            if category == "multi_turn_base":
                sample = {
                    "id": unit.metadata["bfcl_id"],
                    "function": unit.tools,
                    "ground_truth": unit.gold,
                    "initial_config": unit.metadata.get("initial_config"),
                    "involved_classes": unit.metadata.get("involved_classes"),
                }
                content = content_from_multi_turn_gold(sample)
            else:
                content = content_from_gold(unit.gold)
            score = score_bfcl_official(
                {
                    "id": unit.metadata["bfcl_id"],
                    "function": unit.tools[0]["function"] if unit.tools else {},
                    "ground_truth": unit.gold,
                    "initial_config": unit.metadata.get("initial_config"),
                    "involved_classes": unit.metadata.get("involved_classes"),
                },
                content,
            )
            record = {
                "category": category,
                "n": index,
                "task_uid": unit.task_uid,
                "content": content,
                "score": score,
            }
            records.append(record)
            official = score.get("official_result", {})
            print(
                f"BFCL scorer category={category} {index}/{len(units)} "
                f"task={unit.task_uid} score={score['benchmark_score']} "
                f"official_valid={official.get('valid')}"
            )
            if not score["benchmark_score"]:
                print(json.dumps(official, ensure_ascii=False, indent=2, default=str))
                raise AssertionError(f"Expected generated gold content to pass for {unit.task_uid}")
    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
