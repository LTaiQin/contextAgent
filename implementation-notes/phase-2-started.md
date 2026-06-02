# Phase 2 Started

Date: 2026-06-02.

## Status

Phase 2 has started with a rule-based implementation.

Implemented modules:

- `src/context_isolation/gates.py`
- `src/context_isolation/boundary.py`
- `src/context_isolation/retrieval.py`
- `src/context_isolation/evidence.py`
- `src/context_isolation/tool_filter.py`

## Current Behavior

`RuleBasedNeedGate` handles:

- Explicit history references: `previous`, `continue`, `刚才`, `上一题`, `按之前`, `沿用`.
- Tool-state references: `cancel`, `update`, `reservation`, `订单`, `改签`.
- Self-contained messages: math expressions, translation requests, independent QA, long complete prompts.
- Ambiguous references: `it`, `that`, `这个`, `那个`.

`RuleBasedBoundaryDetector` handles:

- Self-contained messages as `new_task`.
- Explicit references as `continue_task` against the latest active task.
- Missing history with reference as `ambiguous`.

`ScopedRetriever` handles:

- `no_context`: returns no history.
- `task_local` / `tool_state`: returns task-local turns when a task id is known.
- fallback: returns recent turns.

`RuleBasedToolFilter` handles:

- Suppresses tools for self-contained tasks.
- Keeps tools for tool-state or explicitly tool-like tasks.

## Verification

Command:

```bash
python /22liushoulong/agent/agent-context-isolation/experiments/run_context_policy_smoke.py
```

Observed behavior:

- Self-contained new math task selects no history under `task_scoped`.
- Explicit follow-up selects recent task-local turns.
- Weather/search-like request keeps the weather tool under `task_scoped`.
- `full_session`, `recent_n`, `retrieval_only`, `need_gated`, `task_scoped`, `task_scoped_tool_filter`, and `oracle_boundary` are all runnable.

## Remaining Phase 2 Work

- Add stronger self-sufficiency tests.
- Add boundary tests for same-domain unrelated tasks.
- Add clarification behavior for ambiguous references.
- Add evaluation metrics for gate accuracy.
- Later: replace or augment rules with a classifier / LLM judge fallback.

