# Phase 1 Completion

Date: 2026-06-02.

## Status

Phase 1 implementation is complete enough to move into Phase 2.

Implemented:

- `src/context_isolation/assembler.py`
- `src/context_isolation/boundary.py`
- `src/context_isolation/evidence.py`
- `src/context_isolation/gates.py`
- `src/context_isolation/retrieval.py`
- `src/context_isolation/schema.py`
- `src/context_isolation/store.py`
- `src/context_isolation/tool_filter.py`
- `src/context_isolation/policy.py`
- `src/context_isolation/trace.py`
- `src/context_isolation/wrappers/lightagent.py`
- `experiments/run_context_policy_smoke.py`

## Policies

Implemented policy classes:

- `FullSessionPolicy`
- `RecentNPolicy`
- `RetrievalOnlyPolicy`
- `NeedGatedPolicy`
- `TaskScopedPolicy`
- `TaskScopedToolFilterPolicy`
- `OracleBoundaryPolicy`

The current `TaskScopedPolicy` is rule-based and conservative:

- Explicit references such as `previous`, `continue`, `刚才`, `上一题`, `按之前` select recent task context.
- Self-contained messages select no history.
- Same-domain unrelated tasks are treated as new tasks by default.
- Self-contained tasks suppress tools unless the message explicitly mentions tool-like needs.

## Smoke Test

Command:

```bash
python /22liushoulong/agent/agent-context-isolation/experiments/run_context_policy_smoke.py
```

Output summary:

```text
CURRENT: Solve x^2 + x - 6 = 0.
full_session: selected=['t1', 't2', 't3', 't4', 't5', 't6']
recent_n: selected=['t5', 't6']
retrieval_only: selected=['t5', 't6']
need_gated: selected=[]
task_scoped: selected=[]
task_scoped_tool_filter: selected=[]
oracle_boundary: selected=['t5', 't6']

CURRENT: Continue from the previous math problem and explain why those roots work.
full_session: selected=['t1', 't2', 't3', 't4', 't5', 't6']
recent_n: selected=['t5', 't6']
retrieval_only: selected=['t4']
need_gated: selected=['t5', 't6']
task_scoped: selected=['t5', 't6']
task_scoped_tool_filter: selected=['t5', 't6']
oracle_boundary: selected=['t5', 't6']
```

Result files:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/context_policy_smoke/results.json
/22liushoulong/agent/agent-context-isolation/experiments/runs/context_policy_smoke/traces.jsonl
```

## Interpretation

The minimum behavior required for the user's core idea is now visible:

- A new self-contained math problem does not inherit older math turns.
- A message explicitly referring to the previous task does retrieve recent task-local context.
- All planned Phase 1 policies are importable and runnable.
- `task_scoped` suppresses unrelated tools for self-contained tasks.

## Known Limits

This is not the final router.

Current limitations:

- No trained classifier.
- No embedding retrieval.
- Persistent store is JSONL-only.
- No official benchmark adapter integration yet.
- Rule-based reference detection is English/Chinese keyword based.

These are Phase 2 and Phase 4 work.
