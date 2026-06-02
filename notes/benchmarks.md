# 开源 Benchmark 重新选择方案

检查日期: 2026-06-02。

本项目不再把 MiroFlow/HLE/GAIA 作为主实验路线。当前研究对象是聊天软件绑定 agent 中的上下文污染、任务边界判断、记忆检索门控和 skill/tool router，因此 benchmark 必须优先覆盖这些能力，而不是优先覆盖深度搜索、浏览器、多模态或代码修复。

## 选择原则

1. 必须是开源或公开可下载 benchmark，尽量保留官方评分器。
2. 优先评测“是否该用历史上下文”和“是否该调用某个工具/skill”，而不是只评测模型本身知识。
3. 优先低外部依赖、低成本、可局部抽样运行的 benchmark。
4. 同时保留论文认可度: 最好有 arXiv/会议论文、官方代码、公开 leaderboard 或官方 reported results。
5. MiroFlow 只作为强 agent paper/reference，不再作为主要实现 baseline。

## 最终优先级

| 优先级 | Benchmark | 主要用途 | 为什么适合本项目 | 接入复杂度 |
| --- | --- | --- | --- | --- |
| P0 | AgentIF | 长 agentic instruction、约束保持、工具约束 | 可测试历史 instruction 是否错误污染当前任务 | 低 |
| P0 | MultiChallenge | 多轮聊天中的指令保持、上下文推理、自洽和版本编辑 | 接近普通聊天 session 中的上下文漂移 | 中 |
| P0 | BFCL multi-turn | function/tool calling、多轮工具路由、irrelevance detection | 直接对应 skill 多了以后 router 出错的问题 | 中 |
| P0 | LongMemEval / LoCoMo / memory-benchmarks | 长期记忆、多 session 问答、更新和拒答 | 直接测试“不是每句话都要检索历史”的门控策略 | 中 |
| P1 | tau-bench / tau2-bench | 用户-agent-工具多轮任务、状态更新、Pass^k | 更真实的业务 agent 场景，可作为主论文级 end-to-end 证明 | 中高 |
| P1 | ToolSandbox | 有状态工具执行、工具轨迹和 guardrail | 测试旧工具状态/旧工具轨迹是否污染后续任务 | 中高 |
| P1 | STATE-Bench | 企业工作流、memory、skills、prompt optimization | 语义上很贴近，但接入和复现实验成本高于 P0 | 高 |
| P2 | GAIA text-only small | 通用 agent 参考指标 | 可做背景展示，不适合验证上下文隔离主张 | 高 |
| P2 | MiroFlow/HLE smoke | 强 agent reference | 只保留少量 smoke，不再做主实验 | 高 |
| P2 | WebArena/OSWorld/SWE-bench | 浏览器/桌面/代码 agent 泛化 | 任务重要但偏离当前核心问题，成本高 | 高 |

## P0 Benchmark 说明

### AgentIF

来源:

- 项目页: https://agentif.github.io/
- 代码: https://github.com/THU-KEG/AgentIF
- 数据: https://huggingface.co/datasets/THU-KEG/AgentIF
- 论文: AgentIF, 2025。

评测重点:

- agentic instruction following。
- 长指令、多约束、工具约束、格式约束。
- 历史任务中的 constraint 是否会泄漏到当前任务。

核心指标:

- CSR: Constraint Success Rate。
- ISR: Instruction Success Rate。
- 按 constraint type 的分项得分。

首轮抽样:

- 先抽 50 条，其中工具约束、格式约束、条件约束各覆盖一部分。
- 每条构造两种版本: 原始任务和带无关历史任务的 stress session。
- 对比 `full_session`、`recent_n`、`need_gated`、`task_scoped`。

为什么放 P0:

- 成本低，不要求真实外部工具。
- 很适合证明“旧 instruction 不应自动继承到新任务”。

### MultiChallenge

来源:

- 论文: https://arxiv.org/abs/2501.17399
- 论文时间: 2025。

评测重点:

- multi-turn conversation。
- instruction retention。
- inference memory。
- self-coherence。
- version editing。

核心指标:

- APR: Average Pass Rate。
- ARS: Average Rubric Score。

首轮抽样:

- 先抽 30 到 50 个多轮样例。
- 不改官方评分 rubric。
- 额外记录当前策略注入的历史 turn 数和 token 数。

为什么放 P0:

- 它比单轮 IF 更接近真实聊天软件 session。
- 可观察“需要保留前文”和“不该保留无关前文”的边界。

### BFCL Multi-Turn

来源:

- Leaderboard/代码: https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard
- 官方站: https://gorilla.cs.berkeley.edu/leaderboard.html

评测重点:

- tool/function selection。
- 参数生成。
- multi-turn function calling。
- relevance/irrelevance detection。
- memory-management 类多轮调用。

核心指标:

- overall accuracy。
- multi-turn accuracy。
- AST / executable accuracy。
- wrong tool rate。
- wrong argument rate。
- irrelevance detection accuracy。

首轮抽样:

- multi-turn 50 条。
- irrelevance/relevance 50 条。
- 每条加同 domain 或同 tool family 的无关历史工具调用记录。

为什么放 P0:

- 它直接评测“skill 多了 router 是否会选错”。
- 不需要搭复杂网页或外部 sandbox，主要是结构化 tool call 评测。

### LongMemEval / LoCoMo / memory-benchmarks

来源:

- LongMemEval: https://github.com/xiaowu0162/LongMemEval
- LongMemEval 论文: https://arxiv.org/abs/2410.10813
- LoCoMo: 常用于长对话记忆评测。
- memory-benchmarks: https://github.com/mem0ai/memory-benchmarks

评测重点:

- 长期对话记忆。
- 多 session 事实召回。
- temporal reasoning。
- memory update。
- abstention，也就是信息不足时不乱答。

核心指标:

- QA accuracy。
- recall@k。
- category accuracy。
- update correctness。
- abstention accuracy。

首轮抽样:

- LongMemEval-S 或小样本 50 到 100 问。
- LoCoMo 小样本 50 问。
- 对比 always retrieve、need gated、task scoped retrieval。

为什么放 P0:

- 这是验证“先判断是否信息充足，再决定是否检索历史”的核心 benchmark。
- 可以清楚测出 unnecessary retrieval 和 missed memory。

## P1 Benchmark 说明

### tau-bench / tau2-bench

来源:

- tau-bench: https://github.com/sierra-research/tau-bench
- tau-bench 论文: https://arxiv.org/abs/2406.12045，2024。
- tau2-bench 论文: https://arxiv.org/abs/2506.07982，2025。
- tau2-bench 代码: https://github.com/sierra-research/tau2-bench

评测重点:

- user-agent-tool 三方多轮交互。
- 业务政策遵守。
- 状态更新和最终环境正确性。
- 多次运行稳定性。

核心指标:

- Pass^1 / Pass^k。
- final state correctness。
- action count。
- wrong tool/action rate。
- issue type breakdown。

首轮抽样:

- 先选一个 domain，10 到 20 个任务。
- 每个策略跑 1 次 smoke。
- 有效果后每个策略 3 次重复运行，计算 Pass^k。

为什么放 P1:

- 很适合作为论文级 end-to-end 证明。
- 但比 P0 更贵、更慢，不能作为最早调试用 benchmark。

### ToolSandbox

来源:

- 代码: https://github.com/apple/ToolSandbox

评测重点:

- stateful tool execution。
- 工具轨迹是否符合目标。
- guardrail 和 snapshot 一致性。

核心指标:

- milestone DAG score。
- snapshot similarity。
- tool trace similarity。
- guardrail similarity。

首轮抽样:

- 先跑 20 个不依赖复杂外部资源的任务。
- 构造同工具不同目标的历史轨迹干扰。

为什么放 P1:

- 很适合验证 stale tool state 问题。
- 但评测环境和 trace scorer 接入会比 BFCL 重。

### STATE-Bench

来源:

- 代码: https://github.com/microsoft/STATE-Bench

评测重点:

- enterprise workflow。
- memory。
- skills。
- prompt optimization。
- simulated user。

核心指标:

- pass@1。
- pass^5。
- UX Score。
- Cost Per Task。

首轮抽样:

- 先只做一个 domain 的 10 到 20 个任务。
- 不追求复现 leaderboard 全量。

为什么放 P1:

- 语义上很贴近“普通用户使用很多 skill 的 agent”。
- 但完整环境和成本不适合第一阶段。

## 不再作为主线的 Benchmark

### GAIA

GAIA 适合证明通用 agent 能力，但它更偏工具综合能力、网页/文件/多模态能力。它不能直接回答上下文隔离是否有效。只保留 `GAIA-Val-Text small` 做参考。

### HLE / BrowseComp / xBench-DeepSearch

这些 benchmark 更适合 deep research agent 或强搜索系统。当前方法创新点不是搜索能力，也不希望依赖 Serper/Jina/E2B 等外部工具链，因此不再放入主实验。

### WebArena / OSWorld / SWE-bench

这些 benchmark 很重要，但分别偏网页操作、桌面操作和代码修复。它们可以作为后续泛化验证，不适合作为第一篇方法验证的核心 benchmark。

## 主实验矩阵

| Benchmark | 原始指标 | 额外记录的本项目指标 |
| --- | --- | --- |
| AgentIF | CSR / ISR | 历史约束污染率、上下文 token、是否误继承旧约束 |
| MultiChallenge | APR / ARS | 需要前文时的 missed context、不需要前文时的 contamination |
| BFCL multi-turn | tool accuracy / executable accuracy | wrong tool rate、wrong argument rate、unnecessary tool call |
| LongMemEval / LoCoMo | QA accuracy / recall@k | unnecessary retrieval、missed memory、wrong memory、abstention |
| tau-bench / tau2 | Pass^k / final state correctness | stale state、wrong action、turn count、cost |
| ToolSandbox | milestone/snapshot/tool trace score | stale tool state、state contamination |
| STATE-Bench | pass@1 / pass^5 / UX / cost | wrong skill、memory misuse、cost per success |

## 推荐实验顺序

1. LightAgent + context policy wrapper 接入 AgentIF，先跑 20 条 smoke。
2. 接入 BFCL multi-turn，先跑 20 到 50 条，验证 tool/skill router 指标。
3. 接入 LongMemEval/LoCoMo，验证 need gate 和 task scoped retrieval。
4. 三个 P0 都跑通后，扩展到 100 到 300 条小规模正式实验。
5. 再接 tau2 或 ToolSandbox 做 end-to-end agent 证明。
6. 最后选择性报告 STATE-Bench 小样本或官方 baseline 结果。

## 论文中可写的核心 claim

1. 在 instruction-following benchmark 上，task-scoped context 降低旧约束污染，同时不损害需要前文的任务。
2. 在 BFCL multi-turn 上，task-scoped tool filtering 降低 wrong tool 和 irrelevant tool call。
3. 在 long-memory benchmark 上，need gate 降低 unnecessary retrieval，并提升 abstention/update 类问题稳定性。
4. 在 tau2/ToolSandbox 上，该方法能减少 stale tool state 和错误状态更新。
5. 相比 always retrieve / full session，该方法降低输入 token 和工具调用成本。
