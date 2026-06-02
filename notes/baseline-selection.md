# Baseline Selection

Date updated: 2026-06-02.

## Current Decision

Do **not** use MiroFlow as the primary implementation baseline.

Use:

```text
Primary implementation baseline: LightAgent
Secondary implementation baseline: LangGraph
Strong paper-level reference: MiroFlow
Optional integration target: MiroFlow
```

## Why The Decision Changed

The first selection prioritized recency, strong reported benchmark results, and broad agent benchmarks. That made MiroFlow attractive on paper.

After local execution, MiroFlow proved too heavy for this project stage:

- It is a deep-research agent, not a lightweight chat-session agent.
- It expects search, reading, code sandbox, and reasoning MCP services.
- Complete baseline requires keys such as `SERPER_API_KEY`, `JINA_API_KEY`, `E2B_API_KEY`, and a reasoning LLM key.
- A single HLE sample can trigger many worker calls, large final summaries, and hundreds of thousands of tokens.
- The experiment becomes dominated by external tool availability and cost rather than context-isolation quality.

The research idea is not about building a best deep-research agent. It is about:

```text
task boundary detection
self-sufficiency gating
history/memory selection
skill/tool candidate filtering
context contamination reduction
```

Therefore a lighter baseline is a better fit.

## Primary Baseline: LightAgent

Repository:

```text
https://github.com/wanxingai/LightAgent
```

Use it for:

- Main method implementation.
- `history` control.
- Memory selection.
- Skill/tool routing.
- Low-cost ablations.

Why:

- Lightweight enough to modify quickly.
- Closer to ordinary chat-app agent usage.
- Has concepts like memory, tools, MCP, skills, and multi-agent delegation.
- The insertion point for context isolation should be much cleaner than MiroFlow.

Expected integration:

```text
user message
  -> ContextPolicy.select(...)
  -> LightAgent.run(query, history=selected.messages, tools=selected.tools)
  -> task memory update
  -> trace
```

## Secondary Baseline: LangGraph

Repository:

```text
https://github.com/langchain-ai/langgraph
```

Use it if:

- LightAgent is too opinionated or unstable.
- A cleaner paper prototype is needed.
- Explicit state graph, persistence, and memory routing are important.

Why:

- Strong state-machine abstraction.
- Mature support for persistent state, memory, subgraphs, and tools.
- Easy to express policies as nodes:

```text
intake -> boundary detector -> context selector -> tool router -> agent -> memory update
```

Tradeoff:

- It is a framework, not a fixed public agent baseline with many reported benchmark scores.
- We need to define the actual runtime ourselves.

## Strong Reference Baseline: MiroFlow

Repository:

```text
https://github.com/MiroMindAI/MiroFlow
```

Paper:

```text
https://arxiv.org/abs/2602.22808
```

Use it for:

- Paper-level reference.
- Reported score comparison.
- Optional final integration.
- Demonstrating why heavyweight deep-research agents are expensive for context-isolation development.

Do not use it for:

- Main method implementation.
- Daily debugging.
- Full benchmark loops.
- Low-cost pilot experiments.

Reported benchmark table from the repo:

| Benchmark | MiroFlow reported score |
| --- | --- |
| GAIA Val | 82.4% |
| HLE | 27.2% |
| HLE-Text | 29.5% |
| BrowserComp-EN | 33.2% |
| BrowserComp-ZH | 47.1% |
| xBench-DeepSearch | 72.0% |

Local finding:

- MiroFlow smoke can run with substitute models.
- Strict official reproduction is blocked without complete external tool keys.
- The cost profile is too high for method iteration.

## Other Related Baselines

### OAgents

Repository:

```text
https://github.com/OPPO-PersonalAI/OAgents
```

Paper:

```text
https://arxiv.org/abs/2506.15741
```

Use it as a related method/ablation reference for agent component analysis.

### OpenHands / CodeActAgent

Repository:

```text
https://github.com/OpenHands/OpenHands
```

Use it as an older broad agent reference, especially for coding/software-engineering tasks. It is too large for the first context-isolation prototype.

### Agent Zero / OpenManus

Useful as product-style general agents, but heavier than needed for the first research prototype.

## Benchmark Strategy

Do not bind the project to MiroFlow benchmarks.

Primary benchmarks:

1. AgentIF
2. MultiChallenge
3. BFCL multi-turn
4. LongMemEval / LoCoMo
5. tau-bench / tau2-bench
6. ToolSandbox

Optional/reference benchmarks:

1. STATE-Bench small subset
2. GAIA text-only subset
3. MiroFlow/HLE smoke
4. BrowseComp / xBench only if budget allows and deep-search generalization is needed

## Final Recommendation

Use **LightAgent first**.

If LightAgent integration is messy, build the controlled runtime in **LangGraph**.

Keep **MiroFlow** as a strong reported baseline and optional integration target, not the primary development baseline.
