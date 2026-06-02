# Agent Context Isolation

This folder collects notes for an agent design problem: when a general user talks to an agent through a chat app, many unrelated tasks often land in one long session. That can create context conflict, stale assumptions, and skill-routing mistakes.

## Core Problem

If the same chat session contains daily-life questions, math questions, tool-use requests, and several independent subproblems, the model may accidentally reuse irrelevant context from earlier turns.

Examples:

- A life-advice discussion influences a later technical answer.
- One math problem's variables, assumptions, or result leak into a different math problem.
- A previously selected skill biases the router even though the new user intent is unrelated.
- Many installed skills increase router ambiguity and make false activation more likely.

## Working Hypothesis

The agent should not treat a chat session as the only unit of context. It should introduce smaller task-level units, each with its own scoped context, memory, skill candidates, and termination condition.

## Initial Direction

Use a context isolation layer between the chat interface and the agent runtime:

1. Detect whether a new user message belongs to an existing task or starts a new task.
2. Assign each task a `task_id`.
3. Keep short-term context scoped by `task_id`.
4. Route skills inside the task scope, not across the whole chat history.
5. Use global memory only when explicitly relevant.
6. Summarize and archive completed tasks instead of keeping all raw history active.

## Key Design Question

The hard part is not just skill routing. It is deciding what context is allowed to influence the next answer.

The system needs a policy like:

- Same task: include recent task context.
- Related task: include a compact summary.
- Unrelated task: exclude prior context by default.
- Ambiguous task: ask a clarification or run with a conservative isolated context.

## Documents

- [problem-framing.md](notes/problem-framing.md): problem statement and failure modes.
- [architecture.md](notes/architecture.md): first-pass system design.
- [experiments.md](notes/experiments.md): ways to test whether isolation helps.
- [baseline-selection.md](notes/baseline-selection.md): candidate open-source agent baselines.
- [lightagent-integration.md](notes/lightagent-integration.md): downloaded baseline status and integration points.
- [benchmarks.md](notes/benchmarks.md): public benchmarks and paper-standard metrics for agent evaluation.
- [agent-project-benchmarks.md](notes/agent-project-benchmarks.md): open-source agent projects with benchmark experiments.

## Full Research Plan

- [paper-index.md](research/agent-context-benchmarks/paper-index.md): core papers, projects, PDFs, and roles.
- [datasets.md](research/agent-context-benchmarks/datasets.md): benchmark/data source catalog and priorities.
- [experiment-plan.md](research/agent-context-benchmarks/experiment-plan.md): all required experiments, metrics, and ablations.
- [proposal-plan.md](research/agent-context-benchmarks/proposal-plan.md): proposed method, borrowed techniques, innovations, strategies, and experiment table.
- [reproduction-guide.md](research/agent-context-benchmarks/reproduction-guide.md): clone commands, implementation structure, and run order.
- [survey.md](research/agent-context-benchmarks/survey.md): final recommendation and research narrative.
