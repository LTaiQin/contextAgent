import json
from pathlib import Path

from benchmark_adapters.bfcl_adapter import BFCLAdapter


OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/bfcl_adapter_smoke")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adapter = BFCLAdapter()
    records = []
    for category in ["simple", "multi_turn_base"]:
        units = adapter.build_session(category=category, limit=3)
        for index, unit in enumerate(units, start=1):
            record = {
                "category": category,
                "n": index,
                "task_uid": unit.task_uid,
                "source_benchmark": unit.source_benchmark,
                "task_type": unit.task_type,
                "tool_count": len(unit.tools),
                "first_tool": unit.tools[0] if unit.tools else None,
                "gold_preview": str(unit.gold)[:300],
                "query_preview": unit.query[:300],
                "metadata": unit.metadata,
            }
            records.append(record)
            print(
                f"BFCL smoke category={category} {index}/{len(units)} task={unit.task_uid} "
                f"tools={len(unit.tools)} first_tool={record['first_tool']['function']['name'] if unit.tools else None} "
                f"gold_present={bool(unit.gold)}"
            )
    (OUT_DIR / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
