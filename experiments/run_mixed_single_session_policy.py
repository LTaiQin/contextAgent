import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path("/22liushoulong/agent/agent-context-isolation")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "LightAgent"))

from benchmark_adapters import BenchmarkResult, TaskUnit, make_policy, summarize_records  # noqa: E402
from benchmark_adapters.scoring import score_task  # noqa: E402
from math_eval import last_boxed  # noqa: E402


MATH_ALGEBRA_PATH = PROJECT_ROOT / "data" / "math" / "algebra" / "test-00000-of-00001.parquet"
AGENTIF_PATH = PROJECT_ROOT / "data" / "agentif" / "eval.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "experiments" / "runs" / "mixed_single_session_policy"
HISTORY_REFERENCE_PATTERN = (
    r"\b(previous|above|earlier|same as before|continue|that one|last one|the former|history|context)\b"
    r"|刚才|上一个|上一题|继续|按之前|照之前|那个|前面|上面|同样|沿用"
)

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


def clear_default_tools(agent: Any) -> None:
    agent.tool_registry.openai_function_schemas = []
    agent.tool_registry.function_mappings = {}
    agent.tool_registry.function_info = {}
    agent.loaded_tools = {}


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
    return agent


def load_math_samples(limit: int) -> list[dict[str, Any]]:
    df = pd.read_parquet(MATH_ALGEBRA_PATH)
    samples = []
    for row_index, row in df.head(limit).iterrows():
        item = row.to_dict()
        item["source_benchmark"] = "MATH"
        item["domain"] = "math"
        item["sample_id"] = f"algebra_{row_index}"
        samples.append(item)
    return samples


def agentif_sample_size(sample: dict[str, Any]) -> int:
    text = "\n".join(message.get("content", "") for message in sample.get("input", []))
    constraints = json.dumps(sample.get("constraints", []), ensure_ascii=False)
    return len(text) + len(constraints)


def load_agentif_samples(limit: int, distinct_constraints: bool = False) -> list[dict[str, Any]]:
    data = json.loads(AGENTIF_PATH.read_text(encoding="utf-8"))
    ranked = sorted((agentif_sample_size(sample), idx, sample) for idx, sample in enumerate(data))
    selected = []
    seen_desc = set()
    for _, idx, sample in ranked:
        text = "\n".join(message.get("content", "") for message in sample.get("input", []))
        if re_search_history_reference(text):
            continue
        constraints = sample.get("constraints", [])
        desc = " | ".join(str(item.get("desc", "")) for item in constraints)
        if distinct_constraints and desc in seen_desc:
            continue
        seen_desc.add(desc)
        item = dict(sample)
        item["source_benchmark"] = "AgentIF"
        item["domain"] = "instruction_following"
        item["sample_idx"] = idx
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def re_search_history_reference(text: str) -> bool:
    import re

    return bool(re.search(HISTORY_REFERENCE_PATTERN, text, flags=re.IGNORECASE))


def build_math_query(sample: dict[str, Any]) -> str:
    return (
        "Solve the following competition math problem. "
        "This is a new independent task unless the user explicitly says otherwise. "
        "Show concise reasoning, and put the final answer in \\boxed{}.\n\n"
        f"Category: algebra\n"
        f"Level: {sample.get('level')}\n"
        f"Sample ID: {sample.get('sample_id')}\n\n"
        f"Problem:\n{sample['problem']}"
    )


def split_agentif_messages(sample: dict[str, Any]) -> tuple[str, str]:
    system_parts = [message["content"] for message in sample["input"] if message.get("role") == "system"]
    user_parts = [message["content"] for message in sample["input"] if message.get("role") == "user"]
    system_text = "\n\n".join(system_parts)
    query = "\n\n".join(user_parts)
    constraints = sample.get("constraints", [])
    if constraints:
        query += "\n\nBenchmark constraints:\n" + json.dumps(constraints, ensure_ascii=False, indent=2)
    return system_text, query


def to_task_unit(source: str, local_index: int, sample: dict[str, Any]) -> TaskUnit:
    if source == "math":
        task_uid = f"math:algebra:{sample['sample_id']}"
        return TaskUnit(
            task_uid=task_uid,
            source_benchmark="MATH",
            domain="math",
            task_type="single_turn_qa",
            query=build_math_query(sample),
            gold=last_boxed(str(sample.get("solution", ""))) or sample.get("answer") or "",
            scorer="math_boxed_normalized",
            metadata={"level": sample.get("level"), "sample_id": sample.get("sample_id")},
        )
    if source == "agentif":
        system_text, query = split_agentif_messages(sample)
        return TaskUnit(
            task_uid=f"agentif:{sample.get('sample_idx', local_index)}",
            source_benchmark="AgentIF",
            domain="instruction_following",
            task_type="instruction_following",
            query=query,
            system_text=system_text,
            gold={},
            scorer="agentif_code_constraints",
            constraints=sample.get("constraints", []),
            metadata={
                "sample_idx": sample.get("sample_idx"),
                "sample_id": sample.get("id"),
                "constraints_count": len(sample.get("constraints", [])),
            },
        )
    raise ValueError(f"Unsupported source: {source}")


def build_session(template: str, limit: int) -> list[TaskUnit]:
    if template == "same_domain_unrelated":
        return [to_task_unit("math", index, sample) for index, sample in enumerate(load_math_samples(limit), start=1)]
    if template == "cross_domain_switch":
        math_samples = load_math_samples(max(2, (limit + 1) // 2))
        agentif_samples = load_agentif_samples(max(2, limit // 2))
        units = [
            to_task_unit("math", 1, math_samples[0]),
            to_task_unit("agentif", 1, agentif_samples[0]),
            to_task_unit("math", 2, math_samples[1]),
            to_task_unit("agentif", 2, agentif_samples[1]),
        ]
        return units[:limit]
    if template == "old_constraint_conflict":
        samples = load_agentif_samples(limit, distinct_constraints=True)
        return [to_task_unit("agentif", index, sample) for index, sample in enumerate(samples, start=1)]
    raise ValueError(f"Unsupported template: {template}")


def estimate_tokens(messages: list[dict[str, Any]], current_message: str, system_text: str) -> int:
    chars = len(system_text) + len(current_message) + sum(len(str(item.get("content", ""))) for item in messages)
    return max(1, round(chars / 3.5))


def task_ids_from_messages(messages: list[dict[str, Any]]) -> list[str]:
    task_ids = []
    for message in messages:
        task_id = message.get("task_id")
        if task_id and task_id not in task_ids:
            task_ids.append(str(task_id))
    return task_ids


def dry_run_content(unit: TaskUnit) -> str:
    if unit.source_benchmark == "MATH":
        return f"DRY_RUN_RESULT: \\boxed{{{unit.gold}}}"
    return "DRY_RUN_OUTPUT"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="cross_domain_switch")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--policy", default="task_scoped")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-model", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", default="https://www.cctq.ai/v1")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    units = build_session(args.template, args.limit)
    policy = make_policy(args.policy)
    agent = make_agent(args) if args.run_model else None
    raw_history: list[dict[str, Any]] = []
    completed_task_ids: list[str] = []
    records: list[dict[str, Any]] = []

    print(
        f"{CYAN}Mixed single-session run template={args.template} policy={policy.name} "
        f"limit={len(units)} run_model={args.run_model}{RESET}",
        flush=True,
    )

    for index, unit in enumerate(units, start=1):
        task_id = f"mixed_{index:04d}_{unit.source_benchmark.lower()}"
        forbidden_task_ids = list(completed_task_ids)
        selected = policy.select(
            session_id=f"mixed_{args.template}",
            user_id="benchmark_user",
            current_message=unit.query,
            raw_history=raw_history,
            available_tools=[],
        )
        selected_task_ids = task_ids_from_messages(selected.messages)
        forbidden_included = [task_id for task_id in selected_task_ids if task_id in set(forbidden_task_ids)]
        input_tokens_est = estimate_tokens(selected.messages, unit.query, unit.system_text)
        unnecessary_context = unit.task_type in {"single_turn_qa", "instruction_following"} and bool(
            selected.messages
        )
        context_ok = not forbidden_included and not unnecessary_context

        print(
            f"{BLUE}=== task {index}/{len(units)} {task_id} source={unit.source_benchmark} "
            f"template={args.template} ==={RESET}",
            flush=True,
        )
        print(
            f"{MAGENTA}[context] selected_tasks={selected_task_ids} forbidden={forbidden_task_ids} "
            f"forbidden_included={forbidden_included} selected_history={len(selected.messages)} "
            f"input_tokens_est={input_tokens_est}{RESET}",
            flush=True,
        )
        print(f"{YELLOW}[decision] need={selected.decision.need_type} boundary={selected.decision.boundary} reason={selected.decision.reason}{RESET}", flush=True)
        print(f"{GREEN if context_ok else RED}[context_score] ok={context_ok} unnecessary_context={unnecessary_context}{RESET}", flush=True)

        if args.run_model:
            try:
                assert agent is not None
                agent.instructions = "\n\n".join(
                    part
                    for part in [
                        unit.system_text or "Follow the current benchmark task exactly.",
                        selected.system_addendum,
                    ]
                    if part
                )
                agent.role = (
                    "Mixed single-session evaluator. Solve only the current task. "
                    "Use selected history only when it is actually needed."
                )
                result = agent.run(
                    unit.query,
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
                agent_trace = result.trace
            except Exception as exc:
                content = ""
                error = f"{type(exc).__name__}: {exc}"
                agent_trace = []
        else:
            content = dry_run_content(unit)
            error = None
            agent_trace = []

        benchmark_score = score_task(unit, content, error).to_dict()
        if not benchmark_score.get("benchmark_scored", True):
            status = "NO_CODE_SCORE"
        else:
            status = "PASS" if benchmark_score["benchmark_score"] else "FAIL"
        print(
            f"{GREEN if status == 'PASS' else (YELLOW if status == 'NO_CODE_SCORE' else RED)}[benchmark_score] status={status} "
            f"type={benchmark_score['score_type']} error={error}{RESET}",
            flush=True,
        )
        print(f"[answer_preview] {content[:500].replace(chr(10), ' ')}", flush=True)

        record = {
            "context_summary": {
                "policy": policy.name,
                "need_type": selected.decision.need_type,
                "boundary": selected.decision.boundary,
                "confidence": selected.decision.confidence,
                "selected_turn_ids": selected.decision.selected_turn_ids,
                "selected_history_count": len(selected.messages),
                "input_tokens_est": input_tokens_est,
                "reason": selected.decision.reason,
            },
        }
        record = BenchmarkResult(
            n=index,
            template=args.template,
            policy=policy.name,
            task_id=task_id,
            task_uid=unit.task_uid,
            source_benchmark=unit.source_benchmark,
            domain=unit.domain,
            task_type=unit.task_type,
            context_ok=context_ok,
            benchmark_status=status,
            context_summary=record["context_summary"],
            benchmark_score=benchmark_score,
            content=content,
            error=error,
            gold_forbidden_context_task_ids=forbidden_task_ids,
            selected_task_ids=selected_task_ids,
            forbidden_context_task_ids_included=forbidden_included,
            unnecessary_context=unnecessary_context,
            agent_trace=agent_trace,
            metadata=unit.metadata,
        ).to_dict()
        records.append(record)

        raw_history.extend(
            [
                {
                    "turn_id": f"u_{index:04d}",
                    "role": "user",
                    "content": unit.query,
                    "task_id": task_id,
                    "metadata": {"task_uid": unit.task_uid, "source_benchmark": unit.source_benchmark},
                },
                {
                    "turn_id": f"a_{index:04d}",
                    "role": "assistant",
                    "content": content,
                    "task_id": task_id,
                    "metadata": {"task_uid": unit.task_uid, "source_benchmark": unit.source_benchmark},
                },
            ]
        )
        completed_task_ids.append(task_id)

    summary = summarize_records(args.template, policy.name, records)
    payload = {"summary": summary, "records": records}
    (args.out_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{CYAN}DONE summary={json.dumps(summary, ensure_ascii=False)} out={args.out_dir / 'results.json'}{RESET}", flush=True)


if __name__ == "__main__":
    main()
