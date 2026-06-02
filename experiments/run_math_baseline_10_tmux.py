import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/experiments")
sys.path.insert(0, "/22liushoulong/agent/agent-context-isolation/third_party/LightAgent")

from LightAgent import LightAgent
from math_eval import extract_prediction, last_boxed, score_prediction


OUT_DIR_DEFAULT = Path("/22liushoulong/agent/agent-context-isolation/experiments/runs/math_baseline_10_cctq_gpt54")
DATA_DIR = Path("/22liushoulong/agent/agent-context-isolation/data/math")
CATEGORIES = [
    "algebra",
    "counting_and_probability",
    "geometry",
    "intermediate_algebra",
    "number_theory",
    "prealgebra",
    "precalculus",
]

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def download_category(category: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{category}/test-00000-of-00001.parquet"
    local_path = DATA_DIR / filename
    if local_path.exists():
        return local_path
    return Path(
        hf_hub_download(
            repo_id="EleutherAI/hendrycks_math",
            repo_type="dataset",
            filename=filename,
            local_dir=DATA_DIR,
        )
    )


def load_samples(limit: int, categories: list[str]) -> list[dict]:
    samples = []
    per_category = max(1, (limit + len(categories) - 1) // len(categories))
    for category in categories:
        path = download_category(category)
        df = pd.read_parquet(path)
        for _, row in df.head(per_category).iterrows():
            item = row.to_dict()
            item["category"] = category
            samples.append(item)
            if len(samples) >= limit:
                return samples
    return samples[:limit]


def build_query(sample: dict) -> str:
    return (
        "Solve the following competition math problem. "
        "Show concise reasoning, and put the final answer in \\boxed{}.\n\n"
        f"Category: {sample.get('category')}\n"
        f"Level: {sample.get('level')}\n\n"
        f"Problem:\n{sample['problem']}"
    )


def clear_default_tools(agent: LightAgent) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--categories", default=",".join(CATEGORIES))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    categories = [item.strip() for item in args.categories.split(",") if item.strip()]
    samples = load_samples(args.limit, categories)

    agent = LightAgent(
        model=os.environ.get("CCTQ_MODEL", "gpt-5.4"),
        api_key=os.environ["CCTQ_API_KEY"],
        base_url=os.environ.get("CCTQ_BASE_URL", "https://www.cctq.ai/v1"),
        auto_discover_skills=False,
        tree_of_thought=False,
        self_learning=False,
    )
    clear_default_tools(agent)
    agent.instructions = "You are a careful competition math solver."
    agent.role = "Solve each problem independently. Do not use previous problems."

    results = []
    for n, sample in enumerate(samples, start=1):
        query = build_query(sample)
        gold = last_boxed(sample.get("solution", "")) or sample.get("answer") or ""
        print(
            f"{CYAN}=== MATH baseline {n}/{len(samples)} category={sample.get('category')} level={sample.get('level')} ==={RESET}",
            flush=True,
        )
        print(f"problem_chars={len(sample['problem'])} query_chars={len(query)}", flush=True)
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

        pred = extract_prediction(content)
        score = score_prediction(pred, gold)
        status = "PASS" if score["correct_normalized"] and not error else "FAIL"
        color = GREEN if score["correct_normalized"] else RED
        print(f"{color}status={status} pred={pred!r} gold={gold!r} error={error}{RESET}", flush=True)
        print("answer_preview:", content[:500].replace("\n", "\\n"), flush=True)

        record = {
            "n": n,
            "category": sample.get("category"),
            "level": sample.get("level"),
            "problem": sample.get("problem"),
            "solution": sample.get("solution"),
            "gold": gold,
            "prediction": pred,
            "content": content,
            "error": error,
            "correct_raw": score["correct_raw"],
            "correct_normalized": score["correct_normalized"],
            "correct_exact": score["correct_normalized"],
            "trace": result.trace if result else [],
        }
        results.append(record)
        (args.out_dir / f"sample_{n:03d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        done = len(results)
        correct_count = sum(1 for item in results if item["correct_exact"])
        print(f"running_summary: correct={correct_count} wrong={done - correct_count} done={done}", flush=True)

    (args.out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    correct_count = sum(1 for item in results if item["correct_exact"])
    print(f"{CYAN}DONE out={args.out_dir / 'results.json'} correct={correct_count} total={len(results)}{RESET}", flush=True)


if __name__ == "__main__":
    main()
