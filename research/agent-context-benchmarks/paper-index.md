# Paper And Project Index

检索日期: 2026-06-01

主题: 面向聊天软件中长 session、任务切换、上下文污染、记忆/工具/skill 路由的通用 agent 实验调研。

## 核心 Baseline / Benchmark 论文

| 类别 | 标题 | 日期 | 官方链接 | 代码/数据 | 本地 PDF | 用途 |
| --- | --- | --- | --- | --- | --- | --- |
| 新主 baseline | MiroFlow: Towards High-Performance and Robust Open-Source Agent Framework for General Deep Research Tasks | 2026-02-26 | https://arxiv.org/abs/2602.22808 | https://github.com/MiroMindAI/MiroFlow | `pdfs/miroflow-2602.22808.pdf` | 2026 开源 agent baseline，多 benchmark 结果，适合主线 |
| 新 agent 模型/数据 | MiroThinker: Agentic Reasoning Model with Reinforced Multi-Turn Tool Use | 2025-11-17 | https://arxiv.org/abs/2511.11793 | https://github.com/MiroMindAI/MiroThinker | `pdfs/mirothinker-2511.11793.pdf` | 参考多轮工具使用、agentic RL 和深度搜索训练 |
| 组件消融 baseline | OAgents: An Empirical Study of Building Effective Agents | 2025-06-23 | https://arxiv.org/abs/2506.15741 | https://github.com/OPPO-PersonalAI/OAgents | `pdfs/oagents-2506.15741.pdf` | 参考 agent 组件消融、复现协议、GAIA/BrowseComp |
| 对话工具 benchmark | tau2-Bench: Evaluating Conversational Agents in a Dual-Control Environment | 2025-06-09 | https://arxiv.org/abs/2506.07982 | https://github.com/sierra-research/tau2-bench | `pdfs/tau2-2506.07982.pdf` | 多轮 user-agent-tool 对话，Pass^k 可靠性 |
| 指令遵循 benchmark | AGENT IF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios | 2025-05-22 | https://arxiv.org/abs/2505.16944 | https://github.com/THU-KEG/AgentIF / https://huggingface.co/datasets/THU-KEG/AgentIF | `pdfs/agentif-2505.16944.pdf` | 长 system prompt、工具规格、约束遵循，CSR/ISR |
| 日常场景 benchmark | AgentIF-OneDay: A Task-level Instruction-Following Benchmark for General AI Agents in Daily Scenarios | 2026-01-30 | https://arxiv.org/abs/2601.20613 | https://github.com/xbench-ai / https://huggingface.co/xbench-ai | `pdfs/agentif-oneday-2601.20613.pdf` | 普通用户日常任务、附件、文件产出、多轮 refinement |
| Web baseline | OpAgent: Operator Agent for Web Navigation | 2026-02-13 | https://arxiv.org/abs/2602.13559 | https://github.com/codefuse-ai/OpAgent | `pdfs/opagent-2602.13559.pdf` | WebArena / web navigation 专项 baseline |
| 多轮对话 benchmark | MultiChallenge: A Realistic Multi-turn Conversation Benchmark Challenging to Frontier LLMs | 2025-01-29 | https://arxiv.org/abs/2501.17399 | 论文中给出 GitHub 入口 | `pdfs/multichallenge-2501.17399.pdf` | 指令保持、歧义消解、状态维护、自洽 |
| 长期记忆 benchmark | LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory | 2024-10-14 | https://arxiv.org/abs/2410.10813 | https://github.com/xiaowu0162/LongMemEval | `pdfs/longmemeval-2410.10813.pdf` | 长期记忆、跨 session 推理、时间推理、abstention |
| 老但成熟 baseline | OpenHands / CodeActAgent | 2024-07-24 | https://arxiv.org/abs/2407.16741 | https://github.com/OpenHands/OpenHands / https://github.com/OpenHands/benchmarks | `pdfs/codeact-2407.16741.pdf` | 多 benchmark harness，SWE-Bench/GAIA/WebArena 等 |

## 结论

主实验 baseline 建议使用 **MiroFlow**，因为它是 2026 年开源通用 deep research agent，已经报告 GAIA、BrowseComp、HLE、xBench-DeepSearch、FutureX 等多 benchmark 结果，并且论文特别强调可复现和稳定性。方法论和消融设计参考 **OAgents**。与普通用户聊天软件场景最贴的数据集是 **AgentIF-OneDay**、**tau2/tau3**、**AgentIF**、**LongMemEval**。

