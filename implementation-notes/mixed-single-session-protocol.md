# Mixed Single-Session Evaluation Protocol

Date: 2026-06-02.

## Goal

This protocol records the idea of evaluating context isolation in one long chat session that mixes many task types. The target is not math, daily QA, tools, or memory separately. The target is whether an agent can keep task boundaries clean when ordinary users put unrelated work into the same chat thread.

## Core Claim

A realistic chat-bound agent should be evaluated with multiple heterogeneous tasks in the same session. The evaluation unit remains each task, but all tasks share the same session history.

This directly tests:

- Whether the current message is a new task or a continuation.
- Whether old context is needed at all.
- Whether same-domain but unrelated tasks are incorrectly merged.
- Whether old constraints, variables, memory, or tool state contaminate the current task.
- Whether explicit references to previous tasks still retrieve the right evidence.

## Data Sources

The mixed session should reuse public benchmark tasks. It should not invent new benchmark questions as the main evidence.

Initial sources:

- MATH / GSM8K: self-contained and related math tasks.
- AgentIF: instruction and constraint following tasks.
- BFCL: tool/function routing tasks.
- LongMemEval / LoCoMo: long-memory and fact-update tasks.
- ToolSandbox or tau2: stateful tool tasks, after P0 is stable.

## Task Unit

Each benchmark item becomes a `TaskUnit`.

Required fields:

```json
{
  "task_uid": "math:algebra:test:0001",
  "source_benchmark": "MATH",
  "domain": "math",
  "task_type": "single_turn_qa",
  "messages": [],
  "gold": {},
  "scorer": "math_boxed_exact",
  "requires_history": false,
  "allowed_context_task_ids": [],
  "forbidden_context_task_ids": [],
  "tools": [],
  "metadata": {}
}
```

## Session Templates

The order must be controlled, not purely random.

### cross_domain_switch

Pattern:

```text
math -> instruction_following -> memory_qa -> tool_calling -> math
```

Purpose:

Test broad domain shifts and stale constraints.

### same_domain_unrelated

Pattern:

```text
math_a -> math_b -> math_c
```

Constraint:

Each task is self-contained and must not use prior task variables or results.

Purpose:

Test the rule that same domain does not imply same task.

### same_domain_related

Pattern:

```text
math_a -> followup_using_math_a_result
```

Constraint:

The follow-up must explicitly reference the prior result.

Purpose:

Test that task-scoped selection can retrieve context when it is actually needed.

### old_constraint_conflict

Pattern:

```text
agentif_json_only -> agentif_plain_text -> agentif_option_only
```

Purpose:

Test whether old output constraints contaminate later instructions.

### memory_update_conflict

Pattern:

```text
profile_fact_old -> profile_fact_update -> query_current_fact
```

Purpose:

Test whether newer facts override older facts.

### tool_reuse_conflict

Pattern:

```text
tool_task_a -> tool_task_b_same_tool_different_goal
```

Purpose:

Test stale tool arguments, stale tool state, and wrong tool reuse.

### ambiguous_reference

Pattern:

```text
task_a -> task_b -> "do the same for that one"
```

Purpose:

Test whether the agent asks for clarification instead of guessing.

## Ordering Rules

Use seeded generation so the mixed sessions are reproducible.

Rules:

- Do not split one benchmark task internally unless the original benchmark is multi-turn.
- Do not place two related tasks together unless the template says they are related.
- Keep at least one unrelated task between repeated domains in `cross_domain_switch`.
- For `same_domain_unrelated`, use similar surface forms where possible, such as repeated variable names.
- For `old_constraint_conflict`, ensure the current task has a different output constraint from the previous one.
- For memory update templates, include both the old fact and the newer fact in the same session.

## Ground Truth Labels

Every task in the mixed session needs task-level labels:

```json
{
  "session_id": "mixed:0001",
  "turn_id": "turn:0012",
  "task_uid": "math:algebra:test:0007",
  "gold_boundary": "new_task",
  "gold_need_type": "no_context",
  "gold_allowed_context_task_ids": [],
  "gold_forbidden_context_task_ids": ["agentif:0003", "math:0006"],
  "gold_tools": [],
  "should_clarify": false
}
```

## Policies To Compare

Run the same mixed sessions with:

- `full_session`
- `recent_n`
- `retrieval_only`
- `need_gated`
- `task_scoped`
- `task_scoped_tool_filter`
- `oracle_boundary`

## Metrics

Benchmark-native task score:

- MATH / GSM8K answer accuracy.
- AgentIF CSR / ISR or code-constraint pass rate.
- BFCL tool-call accuracy.
- LongMemEval QA accuracy.

Context-isolation score:

- `boundary_accuracy`
- `need_context_accuracy`
- `unnecessary_context_rate`
- `missed_context_rate`
- `context_contamination_rate`
- `stale_constraint_rate`
- `stale_variable_rate`
- `wrong_memory_rate`
- `wrong_tool_rate`
- `over_filter_tool_rate`
- `input_tokens_m`
- `output_tokens_m`

## Reporting

Do not report only a single session-level score.

Report:

- Per-task benchmark score.
- Per-template score.
- Per-domain score.
- Context-isolation error type.
- Token cost by policy.

## Role In The Paper

The public benchmark single-task results prove that the method does not break original tasks.

The mixed single-session protocol proves the main research claim: task-scoped context selection is more reliable than full-session or recent-window context when heterogeneous tasks are mixed into one chat thread.

