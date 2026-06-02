# Dataset And Benchmark Catalog

检索日期: 2026-06-01

## 第一优先级: 必做

| Benchmark | 数据/代码入口 | 覆盖能力 | 关键指标 | 为什么必须做 |
| --- | --- | --- | --- | --- |
| AgentIF-OneDay | https://github.com/xbench-ai / https://huggingface.co/xbench-ai | 普通用户日常工作/生活/学习任务，附件理解，文件产出，多轮 refinement | instance-level rubric score, scoring-point accuracy, human-judge agreement | 最接近“普通用户通过聊天软件使用 agent”的问题 |
| tau2 / tau3 | https://github.com/sierra-research/tau2-bench | user-agent-tool 多轮任务，retail/airline/telecom，dual-control | Pass^k, Pass^1, final state correctness, issue-type breakdown | 适合测任务状态、用户交互、工具调用可靠性 |
| AGENT IF | https://github.com/THU-KEG/AgentIF / https://huggingface.co/datasets/THU-KEG/AgentIF | 真实 agent 应用中的长 system prompt、工具约束、条件约束 | CSR, ISR | 直接测 skill/tool instruction 是否被长上下文污染 |
| LongMemEval | https://github.com/xiaowu0162/LongMemEval | 长期对话记忆、跨 session 推理、时间推理、信息更新、abstention | QA accuracy, recall@k, category accuracy | 直接测记忆检索和上下文选择是否正确 |
| GAIA | https://huggingface.co/gaia-benchmark | 通用 assistant 任务，工具、浏览、文件、多模态 | accuracy by level / overall | 主流 agent 论文都用，便于和 MiroFlow/OAgents/OpenHands 对齐 |

## 第二优先级: 证明泛化

| Benchmark | 数据/代码入口 | 覆盖能力 | 关键指标 | 备注 |
| --- | --- | --- | --- | --- |
| BrowseComp / BrowseComp-ZH | 论文/官方数据入口见 MiroFlow 引用 | hard-to-find web browsing 信息检索 | accuracy / avg@k | MiroFlow 和 MiroThinker 都报告 |
| HLE | https://lastexam.ai/ | 多学科高难问题，含多模态 | accuracy | 适合证明复杂推理能力不下降 |
| xBench-DeepSearch | https://github.com/xbench-ai | 深度搜索 / 信息检索工具使用 | score / accuracy | 与 deep research agent 相关 |
| FutureX | 见 MiroFlow 论文引用 | 未来事件预测，动态更新，污染控制 | leaderboard score | 适合强调 live/contamination-controlled |
| WebArena | https://github.com/web-arena-x/webarena | 自托管 web 操作，shopping/CMS/forum/GitLab/map/Wikipedia | task success rate | web agent 泛化，OpAgent 主 benchmark |
| SWE-Bench Lite/Verified | https://github.com/SWE-bench/SWE-bench | GitHub issue 修复 | resolved % | 若要证明 coding agent 不受影响再做 |
| OpenHands Benchmarks | https://github.com/OpenHands/benchmarks | SWE-Bench, GAIA, Commit0, OpenAgentSafety, ProgramBench | benchmark-native metrics | 复用 harness，而不是单一数据集 |

## 第三优先级: 多轮对话漂移

| Benchmark | 入口 | 覆盖能力 | 指标 |
| --- | --- | --- | --- |
| MultiChallenge | https://arxiv.org/abs/2501.17399 | 多轮对话、指令保持、歧义消解、版本编辑、自洽 | APR, ARS / average accuracy |
| Multi-IF | https://evalscope.readthedocs.io/en/latest/benchmarks/multi_if.html | 多轮多语种 instruction following | prompt/inst strict, prompt/inst loose |
| memory-benchmarks | https://github.com/mem0ai/memory-benchmarks | LOCOMO, LongMemEval, BEAM 等记忆评测集合 | benchmark-specific memory metrics |

## 数据集选择建议

最小可发表实验组合:

1. GAIA-Val 或 GAIA-Val-Text: 对齐 MiroFlow/OAgents/OpenHands。
2. AgentIF: 证明长 agentic instruction 和 tool/skill constraints 不被污染。
3. tau2/tau3: 证明多轮 user-agent-tool 状态型任务稳定。
4. LongMemEval: 证明长期记忆检索与任务上下文隔离有效。

更强版本:

1. 加 AgentIF-OneDay: 更贴普通用户日常 agent。
2. 加 BrowseComp / xBench-DeepSearch: 对齐 MiroFlow deep research。
3. 加 WebArena: 证明 web 操作泛化。

