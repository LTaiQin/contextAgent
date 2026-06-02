import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/third_party/LightAgent")

from LightAgent import LightAgent


DATA_PATH = Path("/22liushoulong/agent/agent-context-isolation/data/agentif/eval.json")
DEFAULT_OUT_DIR = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/agentif_baseline_20_cctq_gpt54")


GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def sample_size(sample: dict) -> int:
    text = "\n".join(message.get("content", "") for message in sample.get("input", []))
    constraints = json.dumps(sample.get("constraints", []), ensure_ascii=False)
    return len(text) + len(constraints)


def select_samples(data: list[dict], limit: int) -> list[tuple[int, dict]]:
    ranked = sorted((sample_size(sample), idx, sample) for idx, sample in enumerate(data))
    return [(idx, sample) for _, idx, sample in ranked[:limit]]


def split_messages(sample: dict) -> tuple[str, str]:
    system_parts = [m["content"] for m in sample["input"] if m.get("role") == "system"]
    user_parts = [m["content"] for m in sample["input"] if m.get("role") == "user"]
    system_text = "\n\n".join(system_parts)
    query = "\n\n".join(user_parts)
    constraints = sample.get("constraints", [])
    if constraints:
        query += "\n\nBenchmark constraints:\n" + json.dumps(constraints, ensure_ascii=False, indent=2)
    return system_text, query


def evaluate_code_constraints(response: str, constraints: list[dict]) -> tuple[int, int, list[dict]]:
    details = []
    total = 0
    passed = 0
    for constraint in constraints:
        evaluations = constraint.get("evaluation") or []
        for evaluation in evaluations:
            if evaluation.get("type") != "code" or not evaluation.get("exec"):
                continue
            total += 1
            namespace = {}
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
            details.append({
                "constraint_id": constraint.get("id"),
                "desc": constraint.get("desc"),
                "passed": ok,
                "error": error,
            })
    return passed, total, details


def clear_default_tools(agent: LightAgent) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-tokens", type=int, default=700)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    selected = select_samples(data, args.limit)

    agent = LightAgent(
        model=os.environ.get("CCTQ_MODEL", "gpt-5.4"),
        api_key=os.environ["CCTQ_API_KEY"],
        base_url=os.environ.get("CCTQ_BASE_URL", "https://www.cctq.ai/v1"),
        auto_discover_skills=False,
        tree_of_thought=False,
        self_learning=False,
    )
    clear_default_tools(agent)

    results = []
    for n, (idx, sample) in enumerate(selected, start=1):
        system_text, query = split_messages(sample)
        agent.instructions = system_text or "Follow the benchmark instruction exactly."
        agent.role = "AgentIF baseline evaluator. Follow the current sample instruction and constraints exactly."

        print(f"{CYAN}=== AgentIF baseline {n}/{len(selected)} idx={idx} id={sample['id']} ==={RESET}", flush=True)
        print(
            f"chars={sample_size(sample)} query_chars={len(query)} constraints={len(sample.get('constraints', []))}",
            flush=True,
        )
        try:
            result = agent.run(
                query,
                history=[],
                result_format="object",
                trace=True,
                max_retry=2,
                use_skills=False,
                metadata={"max_tokens": args.max_tokens},
            )
            content = result.content
            error = result.error
        except Exception as exc:
            content = ""
            error = f"{type(exc).__name__}: {exc}"
            result = None

        passed, total, eval_details = evaluate_code_constraints(content, sample.get("constraints", []))
        status = "PASS" if total and passed == total and not error else ("NO_CODE_SCORE" if total == 0 and not error else "FAIL")
        color = GREEN if status == "PASS" else (YELLOW if status == "NO_CODE_SCORE" else RED)
        print(f"{color}status={status} code_score={passed}/{total} error={error}{RESET}", flush=True)
        print("answer_preview:", content[:500].replace("\n", "\\n"), flush=True)

        record = {
            "n": n,
            "idx": idx,
            "id": sample["id"],
            "chars": sample_size(sample),
            "query_chars": len(query),
            "constraints_count": len(sample.get("constraints", [])),
            "content": content,
            "error": error,
            "code_score_passed": passed,
            "code_score_total": total,
            "status": status,
            "eval_details": eval_details,
            "trace": result.trace if result else [],
        }
        results.append(record)
        (args.out_dir / f"sample_{n:03d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary_passed = sum(1 for item in results if item["status"] == "PASS")
        summary_failed = sum(1 for item in results if item["status"] == "FAIL")
        print(f"running_summary: pass={summary_passed} fail={summary_failed} done={len(results)}", flush=True)

    (args.out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    print(f"{CYAN}DONE out={args.out_dir / 'results.json'} pass={pass_count} fail={fail_count} total={len(results)}{RESET}", flush=True)


if __name__ == "__main__":
    main()
