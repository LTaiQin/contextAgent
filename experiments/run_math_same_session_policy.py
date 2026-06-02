import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from huggingface_hub import hf_hub_download

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "LightAgent"))

from context_isolation import (  # noqa: E402
    FullSessionPolicy,
    NeedGatedPolicy,
    RecentNPolicy,
    RetrievalOnlyPolicy,
    TaskScopedPolicy,
)
from math_eval import extract_prediction, last_boxed, score_prediction  # noqa: E402


OUT_DIR_DEFAULT = PROJECT_ROOT / "experiments" / "runs" / "math_same_session_policy"
DATA_DIR = PROJECT_ROOT / "data" / "math"
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
MAGENTA = "\033[35m"
BLUE = "\033[34m"
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


def load_samples(limit: int, categories: list[str]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    per_category = max(1, (limit + len(categories) - 1) // len(categories))
    for category in categories:
        path = download_category(category)
        df = pd.read_parquet(path)
        for row_index, row in df.head(per_category).iterrows():
            item = row.to_dict()
            item["category"] = category
            item["sample_id"] = f"{category}_{row_index}"
            samples.append(item)
            if len(samples) >= limit:
                return samples
    return samples[:limit]


def build_query(sample: dict[str, Any]) -> str:
    return (
        "Solve the following competition math problem. "
        "This is a new independent task unless the user explicitly says otherwise. "
        "Show concise reasoning, and put the final answer in \\boxed{}.\n\n"
        f"Category: {sample.get('category')}\n"
        f"Level: {sample.get('level')}\n"
        f"Sample ID: {sample.get('sample_id')}\n\n"
        f"Problem:\n{sample['problem']}"
    )


def clear_default_tools(agent: Any) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


def make_policy(name: str):
    if name == "full_session":
        return FullSessionPolicy()
    if name == "recent_n":
        return RecentNPolicy(n=4)
    if name == "retrieval_only":
        return RetrievalOnlyPolicy(top_k=4)
    if name == "need_gated":
        return NeedGatedPolicy(max_turns=6)
    if name == "task_scoped":
        return TaskScopedPolicy(max_task_turns=6)
    raise ValueError(f"Unsupported policy: {name}")


def make_agent(args: argparse.Namespace):
    from LightAgent import LightAgent

    agent = LightAgent(
        model=os.environ.get("CCTQ_MODEL", args.model),
        api_key=os.environ["CCTQ_API_KEY"],
        base_url=os.environ.get("CCTQ_BASE_URL", args.base_url),
        auto_discover_skills=False,
        tree_of_thought=False,
        self_learning=False,
    )
    clear_default_tools(agent)
    agent.instructions = (
        "You are a careful competition math solver. "
        "Use only the selected chat history that is provided by the context policy."
    )
    agent.role = "Solve the current problem independently unless selected history is truly needed."
    return agent


def estimate_tokens_from_messages(messages: list[dict[str, Any]], current_message: str) -> int:
    chars = len(current_message) + sum(len(str(item.get("content", ""))) for item in messages)
    return max(1, round(chars / 3.5))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--policy", default="task_scoped")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--categories", default=",".join(CATEGORIES))
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default="https://www.cctq.ai/v1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    categories = [item.strip() for item in args.categories.split(",") if item.strip()]
    samples = load_samples(args.limit, categories)
    policy = make_policy(args.policy)
    agent = None if args.dry_run else make_agent(args)
    raw_history: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    print(
        f"{CYAN}MATH same-session policy run policy={policy.name} limit={len(samples)} dry_run={args.dry_run}{RESET}",
        flush=True,
    )

    for n, sample in enumerate(samples, start=1):
        task_id = f"math_{n:04d}_{sample.get('category')}"
        query = build_query(sample)
        gold = last_boxed(str(sample.get("solution", ""))) or sample.get("answer") or ""
        selected = policy.select(
            session_id="math_same_session",
            user_id="benchmark_user",
            current_message=query,
            raw_history=raw_history,
            available_tools=[],
        )
        selected_token_est = estimate_tokens_from_messages(selected.messages, query)

        print(
            f"{BLUE}=== task {n}/{len(samples)} id={task_id} category={sample.get('category')} level={sample.get('level')} ==={RESET}",
            flush=True,
        )
        print(
            f"{MAGENTA}[context] policy={policy.name} boundary={selected.decision.boundary} "
            f"need={selected.decision.need_type} selected_turns={selected.decision.selected_turn_ids} "
            f"history_all={len(raw_history)} history_selected={len(selected.messages)} "
            f"input_tokens_est={selected_token_est}{RESET}",
            flush=True,
        )
        print(f"{YELLOW}[reason] {selected.decision.reason}{RESET}", flush=True)

        if args.dry_run:
            content = f"DRY_RUN: gold is \\boxed{{{gold}}}"
            error = None
            trace = []
        else:
            try:
                result = agent.run(
                    query,
                    history=selected.messages,
                    tools=selected.tools,
                    result_format="object",
                    trace=True,
                    max_retry=2,
                    use_skills=False,
                    metadata={"max_tokens": args.max_tokens},
                )
                content = result.content
                error = result.error
                trace = result.trace
            except Exception as exc:
                content = ""
                error = f"{type(exc).__name__}: {exc}"
                trace = []

        pred = extract_prediction(content)
        score = score_prediction(pred, gold)
        correct_raw = score["correct_raw"]
        correct_normalized = score["correct_normalized"]
        context_summary = {
            "policy": policy.name,
            "need_type": selected.decision.need_type,
            "boundary": selected.decision.boundary,
            "task_id": selected.decision.task_id,
            "confidence": selected.decision.confidence,
            "selected_turn_ids": selected.decision.selected_turn_ids,
            "selected_memory_ids": selected.decision.selected_memory_ids,
            "selected_tools": selected.decision.selected_tools,
            "suppressed_tools": selected.decision.suppressed_tools,
            "raw_history_count": len(raw_history),
            "selected_history_count": len(selected.messages),
            "input_tokens_est": selected_token_est,
            "reason": selected.decision.reason,
        }
        status = "PASS" if correct_normalized and not error else "FAIL"
        color = GREEN if correct_normalized else RED
        print(f"{color}[score] status={status} pred={pred!r} gold={gold!r} error={error}{RESET}", flush=True)
        print(f"[answer_preview] {content[:500].replace(chr(10), ' ')}", flush=True)

        user_turn = {
            "turn_id": f"u_{n:04d}",
            "role": "user",
            "content": query,
            "task_id": task_id,
            "metadata": {
                "benchmark": "MATH",
                "sample_id": sample.get("sample_id"),
                "category": sample.get("category"),
            },
        }
        assistant_turn = {
            "turn_id": f"a_{n:04d}",
            "role": "assistant",
            "content": content,
            "task_id": task_id,
            "metadata": {
                "benchmark": "MATH",
                "sample_id": sample.get("sample_id"),
                "correct_raw": correct_raw,
                "correct_normalized": correct_normalized,
            },
        }
        raw_history.extend([user_turn, assistant_turn])

        record = {
            "n": n,
            "task_id": task_id,
            "policy": policy.name,
            "category": sample.get("category"),
            "level": sample.get("level"),
            "problem": sample.get("problem"),
            "solution": sample.get("solution"),
            "gold": gold,
            "prediction": pred,
            "content": content,
            "error": error,
            "correct_raw": correct_raw,
            "correct_normalized": correct_normalized,
            "context_summary": context_summary,
            "context_decision": selected.trace,
            "selected_messages": selected.messages,
            "agent_trace": trace,
        }
        results.append(record)
        (args.out_dir / f"sample_{n:03d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        correct_count = sum(1 for item in results if item["correct_normalized"])
        print(
            f"{CYAN}[running] correct={correct_count} wrong={len(results) - correct_count} done={len(results)}{RESET}",
            flush=True,
        )

    (args.out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    correct_count = sum(1 for item in results if item["correct_normalized"])
    print(
        f"{CYAN}DONE out={args.out_dir / 'results.json'} correct={correct_count} total={len(results)}{RESET}",
        flush=True,
    )


if __name__ == "__main__":
    main()
