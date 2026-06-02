import json
from pathlib import Path

from benchmark_adapters.longmemeval_adapter import LongMemEvalAdapter
from benchmark_adapters.scoring import score_task


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/longmemeval_adapter_smoke")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adapter = LongMemEvalAdapter()
    units = adapter.build_session(split="s_cleaned", limit=3)
    records = []
    for index, unit in enumerate(units, start=1):
        content = str(unit.gold)
        score = score_task(unit, content, None).to_dict()
        record = {
            "n": index,
            "task_uid": unit.task_uid,
            "question_type": unit.metadata.get("question_type"),
            "haystack_session_count": unit.metadata.get("haystack_session_count"),
            "gold": unit.gold,
            "query_chars": len(unit.query),
            "score": score,
        }
        records.append(record)
        print(
            f"LongMemEval smoke {index}/{len(units)} task={unit.task_uid} "
            f"type={record['question_type']} sessions={record['haystack_session_count']} "
            f"score={score['benchmark_score']} query_chars={record['query_chars']}"
        )
        if not score["benchmark_score"]:
            raise AssertionError(f"Expected gold content to pass for {unit.task_uid}")
    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
