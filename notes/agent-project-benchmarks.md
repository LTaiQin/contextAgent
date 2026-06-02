# Open-Source Agent Projects With Benchmark Experiments

Date checked: 2026-06-01.

Goal: find open-source agent projects that already run many public agent benchmarks, so this project can reuse their harnesses, reported numbers, or experimental protocol instead of building a full evaluation stack from scratch.

## Shortlist

| Project | Repo / Paper | Benchmarks Covered | What To Reuse | Fit For This Project |
| --- | --- | --- | --- | --- |
| MiroFlow | https://github.com/MiroMindAI/MiroFlow, https://arxiv.org/abs/2602.22808 | FutureX, GAIA, HLE, BrowseComp-EN/ZH, xBench-DeepSearch | Newest broad open-source research-agent baseline with reported multi-benchmark results | Best 2025/2026 baseline |
| OAgents | https://github.com/OPPO-PersonalAI/OAgents, https://arxiv.org/abs/2506.15741 | GAIA, BrowseComp | Modular agent design ablations and robust evaluation protocol | Best for agent component ablation |
| OpAgent | https://github.com/codefuse-ai/OpAgent, https://arxiv.org/abs/2602.13559 | WebArena | 2026 SOTA-style web-navigation baseline | Best web-agent baseline |
| EvoAgentX | https://github.com/EvoAgentX/EvoAgentX, https://arxiv.org/abs/2507.03616 | GAIA optimization of Open Deep Research and OWL | Workflow optimization framework and eval integration | Good for workflow optimization baseline |
| OpenHands Benchmarks | https://github.com/OpenHands/benchmarks | SWE-Bench, SWE-Bench Pro, GAIA, Commit0, OpenAgentSafety, ProgramBench | Broad benchmark harness and coding/general-assistant evaluation infrastructure | Best practical eval harness |
| Magentic-One / AutoGenBench | https://github.com/microsoft/autogen, https://arxiv.org/abs/2411.04468 | GAIA, AssistantBench, WebArena | Paper results, AutoGenBench protocol, repeated isolated runs | Best paper-backed general-agent baseline |
| AgentLab + BrowserGym | https://github.com/ServiceNow/AgentLab, https://arxiv.org/abs/2412.05467 | MiniWoB, WebArena, WorkArena, VisualWebArena through BrowserGym | Scalable web-agent benchmarking and result analysis | Best for web-agent experiments |
| OWL / CAMEL-AI | https://github.com/camel-ai/owl | GAIA | Strong open-source GAIA agent baseline | Good general-agent reference, narrower benchmark coverage |
| OpenHands / CodeAct | https://github.com/OpenHands/OpenHands, https://arxiv.org/abs/2407.16741 | SWE-Bench, WebArena, plus other incorporated tasks in paper | Agent architecture and reported software/web agent results | Strong coding-agent reference |

## Best Candidates

### 0. MiroFlow

Repo: https://github.com/MiroMindAI/MiroFlow

Paper: https://arxiv.org/abs/2602.22808

Why it matters:

- It is a newer 2025/2026 open-source agent baseline.
- The repo describes MiroFlow as a research-agent framework with reproducible results on FutureX, GAIA, HLE, BrowseComp, and xBench-DeepSearch.
- It reports a benchmark table: GAIA Val 82.4%, HLE 27.2%, HLE-Text 29.5%, BrowserComp-EN 33.2%, BrowserComp-ZH 47.1%, and xBench-DeepSearch 72.0%.
- It has tools for search, file reading, Python, VQA, audio transcription, E2B, and reasoning.

Use it for:

- Main new baseline.
- Directly citing reported multi-benchmark results.
- Testing context isolation in research-style long-horizon tool use.

Limitation:

- It is strongest for deep research / web research tasks, not coding-agent benchmarks like SWE-bench.

### 1. OpenHands Benchmarks

Repo: https://github.com/OpenHands/benchmarks

Why it matters:

- It is explicitly an evaluation harness for OpenHands agents.
- The README lists active benchmark pipelines for:
  - SWE-Bench
  - SWE-Bench Pro
  - GAIA
  - Commit0
  - OpenAgentSafety
  - ProgramBench
- It supports Docker workspaces and remote runtime, which matters for reproducible agent evaluation.
- It logs tool calls, agent messages, patches, and errors.

Use it for:

- Reusing an existing multi-benchmark evaluation harness.
- Comparing a context-isolation wrapper against existing agent scaffolds on standard tasks.
- Coding-agent and general-assistant evaluation.

Limitation:

- It is strongest for software-engineering and general-assistant tasks, not specifically memory/skill-router isolation.

### 2. Magentic-One / AutoGenBench

Paper: https://arxiv.org/abs/2411.04468

Microsoft article: https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/

AutoGenBench article: https://microsoft.github.io/autogen/0.2/blog/2024/01/25/AutoGenBench/

Why it matters:

- Magentic-One is an open-source generalist multi-agent system.
- The paper evaluates it on GAIA, AssistantBench, and WebArena.
- The paper reports statistically competitive results against state-of-the-art systems.
- AutoGenBench is a standalone tool for running and reporting agent benchmarks.
- AutoGenBench supports repeated and isolated runs, which is relevant to measuring stochastic instability and context contamination.

Use it for:

- Paper-backed related work.
- A generalist multi-agent baseline.
- Benchmark protocol design: repeated runs, isolation, public tasks, standardized reports.

Limitation:

- AutoGen itself is now in maintenance mode, so it may be better as a reference protocol than a long-term implementation base.

### 3. OAgents

Repo: https://github.com/OPPO-PersonalAI/OAgents

Paper: https://arxiv.org/abs/2506.15741

Why it matters:

- It is not just another agent framework; it is an empirical study of agent component choices.
- The paper studies GAIA and BrowseComp.
- It emphasizes reproducibility, variance, and robust evaluation protocol.
- It is modular, so components like planning, memory, and tool use are easier to analyze.

Use it for:

- Framing this project as an agent-component study.
- Designing ablations for context isolation:
  - full context vs scoped context
  - tool/skill candidate filtering
  - memory retrieval policy
  - summarization and archival policy

Limitation:

- It is mainly GAIA/BrowseComp focused, so it does not cover as many benchmark families as OpenHands.

### 4. AgentLab + BrowserGym

AgentLab repo: https://github.com/ServiceNow/AgentLab

BrowserGym paper: https://arxiv.org/abs/2412.05467

Why it matters:

- AgentLab is explicitly for developing, testing, and benchmarking web agents.
- It integrates benchmarks such as MiniWoB, WebArena, and WorkArena.
- BrowserGym + AgentLab reports the first large-scale multi-benchmark web-agent experiment comparing six LLMs across available BrowserGym benchmarks.

Use it for:

- Web task evaluation.
- Reproducible multi-benchmark browser-agent runs.
- Testing whether context isolation helps when web sessions have long trajectories and many stateful interactions.

Limitation:

- It is web-agent specific.

### 5. OWL / CAMEL-AI

Repo: https://github.com/camel-ai/owl

Why it matters:

- OWL is an open-source multi-agent framework built on CAMEL-AI.
- The repo reports a 69.09 average GAIA score and claims top open-source framework ranking.
- It has many toolkits: browser, search, code execution, maps, scholar, weather, data, video/audio/image analysis, etc.

Use it for:

- A strong open-source GAIA-oriented baseline.
- Studying skill/tool explosion in a real multi-tool agent.

Limitation:

- Public benchmark reporting is mostly GAIA-centered, not a broad multi-benchmark matrix.

## Recommendation

For this project, use:

1. **MiroFlow** as the newest broad baseline with many reported benchmark results.
2. **OAgents** as the closest methodological reference for component ablation.
3. **OpAgent** if the comparison is specifically web navigation.
4. **OpenHands Benchmarks** as the most useful reusable evaluation harness.
5. **STATE-Bench** as the most aligned benchmark for memory/skills, even though it is less of a canonical paper-backed agent project.

LightAgent can still be a lightweight implementation baseline, but it does not already have the broad benchmark history that OpenHands, Magentic-One, OAgents, and AgentLab have.

## Practical Choice

If the goal is to **avoid reproducing every baseline result**, cite:

1. Magentic-One paper results on GAIA, AssistantBench, and WebArena.
2. OAgents paper results on GAIA and BrowseComp.
3. OWL repository/paper result on GAIA.
4. OpenHands published/blog/repo results for SWE-Bench-style software tasks.

If the goal is to **run this project's method with minimal eval engineering**, reuse:

1. OpenHands Benchmarks for broad benchmark execution.
2. AutoGenBench for repeated isolated agent-run reporting.
3. AgentLab/BrowserGym for web-agent benchmarks.

If the goal is to **write the method section**, follow:

1. OAgents for component ablation framing.
2. tau-bench/tau2 for Pass^k reliability framing.
3. STATE-Bench for memory/skills/cost/UX metric framing.
