import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/third_party/LightAgent")

from LightAgent import LightAgent


DATA_PATH = Path("/22liushoulong/agent/agent-context-isolation/data/agentif/eval.json")
OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/agentif_cctq_gpt54_smoke")
SAMPLE_INDICES = [619, 512, 484]


def build_prompt(sample: dict) -> tuple[str, list[dict]]:
    messages = sample["input"]
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_parts = [m["content"] for m in messages if m.get("role") == "user"]
    constraints = sample.get("constraints", [])
    query = "\n\n".join(user_parts)
    if constraints:
        query += "\n\nConstraints from benchmark:\n" + json.dumps(constraints, ensure_ascii=False, indent=2)
    history = []
    if system_parts:
        history.append({"role": "user", "content": "Benchmark system instruction:\n" + "\n\n".join(system_parts)})
        history.append({"role": "assistant", "content": "Understood."})
    return query, history


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    agent = LightAgent(
        model=os.environ.get("CCTQ_MODEL", "gpt-5.4"),
        api_key=os.environ["CCTQ_API_KEY"],
        base_url=os.environ.get("CCTQ_BASE_URL", "https://www.cctq.ai/v1"),
        auto_discover_skills=False,
        tree_of_thought=False,
        self_learning=False,
    )
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}

    results = []
    for n, idx in enumerate(SAMPLE_INDICES, start=1):
        sample = data[idx]
        query, history = build_prompt(sample)
        print(f"\n=== AgentIF smoke {n}/{len(SAMPLE_INDICES)} idx={idx} id={sample['id']} ===", flush=True)
        print(f"query_chars={len(query)} history_turns={len(history)} constraints={len(sample.get('constraints', []))}", flush=True)
        result = agent.run(
            query,
            history=history,
            result_format="object",
            trace=True,
            max_retry=2,
            use_skills=False,
        )
        record = {
            "idx": idx,
            "id": sample["id"],
            "query_chars": len(query),
            "history_turns": len(history),
            "constraints": sample.get("constraints", []),
            "content": result.content,
            "error": result.error,
            "trace": result.trace,
        }
        results.append(record)
        (OUT_DIR / f"sample_{n}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print("error:", result.error, flush=True)
        print("answer_preview:", result.content[:500].replace("\n", "\\n"), flush=True)

    (OUT_DIR / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'results.json'}", flush=True)


if __name__ == "__main__":
    main()
