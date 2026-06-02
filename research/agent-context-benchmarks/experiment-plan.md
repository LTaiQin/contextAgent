# Experiment Plan

检索日期: 2026-06-01

## 研究目标

验证一个核心命题:

> 在普通用户长 session 中，显式 task-level context isolation 能减少上下文污染、错误记忆检索和错误工具/skill 激活，同时保持或提升公开 agent benchmark 的任务成功率与可靠性。

## 主 Baseline

主 baseline: **MiroFlow**

原因:

- 2026 年开源 agent framework。
- 已报告多个 benchmark: GAIA、BrowseComp-EN/ZH、HLE、xBench-DeepSearch、FutureX。
- 论文明确关注 reproducible performance、workflow robustness、tool coordination。
- 框架包含 agent graph、reasoning mode、workflow execution，非常适合插入 context selector。

辅助 baseline:

- **OAgents**: 用于组件消融实验设计参考。
- **OpenHands/CodeActAgent**: 用于成熟 benchmark harness 和老 baseline。
- **LightAgent**: 只作为轻量原型，不作为主论文 baseline。

## 被测方法

比较以下上下文策略:

| 策略 | 描述 | 目的 |
| --- | --- | --- |
| Full Session | 把同一聊天 session 历史全部传给 agent | 普通聊天软件最直接 baseline |
| Recent-N | 只保留最近 N turns | 常见工程 baseline |
| Retrieval-Only | 对全 session 做 embedding/BM25 检索 | 常见 memory baseline |
| Task-Scoped | 先做 task boundary detection，再只传当前 task 的上下文 | 核心方法 |
| Task-Scoped + Summary | 当前 task 全量 + 相关旧 task 摘要 | 控制 token 成本 |
| Task-Scoped + Skill/Tool Filter | 在 task scope 内选择工具/skill 候选 | 验证 router 污染减少 |

## 实验 1: GAIA / GAIA-Val-Text 对齐主流 agent

目的:

- 证明方法不会损害通用 agent 能力。
- 与 MiroFlow、OAgents、OpenHands 的已有结果对齐。

数据:

- GAIA validation。
- 优先跑 GAIA-Val-Text 103 题，成本低且 MiroFlow 文中使用过。

指标:

- accuracy / pass@1。
- avg@3 或 avg@8，如果复现实验预算允许。
- token cost。
- tool call count。
- context token length。
- failed task error category。

做法:

1. 运行 MiroFlow 原始配置。
2. 在 agent 输入前加 context policy wrapper。
3. 对每个 GAIA task 构造同一 session 中的前置干扰历史，干扰历史来自同 benchmark 其他任务或公开历史任务，不改 benchmark answer。
4. 分别跑 Full Session、Recent-N、Retrieval-Only、Task-Scoped。
5. 报告 benchmark accuracy 和 contamination-sensitive 指标。

注意:

- 如果使用公开 GAIA 官方评测，最终答案格式必须遵循官方规则。
- 干扰历史只用于 agent 上下文，不修改 benchmark 样本本身。

## 实验 2: AgentIF 长指令/工具约束实验

目的:

- 验证 task-scoped context 是否提升长 agentic instruction 遵循。
- 直接对应 skill 多、router 难、system/tool spec 容易互相污染的问题。

数据:

- AgentIF 707 条 human-annotated instructions。
- 每条平均 1723 words，最多 15630 words，平均 11.9 constraints。

指标:

- CSR: Constraint Success Rate。
- ISR: Instruction Success Rate。
- 分 constraint type: tool, condition, semantic, formatting, example。

做法:

1. 按 AgentIF 官方代码和 HuggingFace 数据集运行。
2. 在每条 instruction 前拼接无关 agentic instruction 作为 session history。
3. 比较 Full Session vs Task-Scoped。
4. 对工具规格约束单独统计 CSR。
5. 报告长 instruction 区间上的性能变化，例如 >6000 words 的 ISR。

预期:

- Full Session 在 tool/condition constraints 上更容易被旧 instruction 污染。
- Task-Scoped 应提高 CSR/ISR，尤其是 tool specs 和 condition constraints。

## 实验 3: tau2/tau3 多轮 user-agent-tool 状态任务

目的:

- 验证方法在真实交互式任务中是否提升稳定性。
- 评估上下文隔离对工具调用、状态更新、用户交互的影响。

数据:

- tau2/tau3 retail、airline、telecom。
- 优先 telecom，因为 tau2 论文显示 dual-control 对 agent 更难。

指标:

- Pass^1。
- Pass^k，建议 k=3 或 5。
- final state correctness。
- issue type breakdown。
- action count / turn count。
- wrong tool call rate。

做法:

1. 使用 tau2/tau3 官方 user simulator 和 domain tools。
2. 原始 agent 作为 baseline。
3. 为同一用户建立跨任务 session，把多个 domain task 顺序放入同一聊天 session。
4. Full Session 允许历史跨任务进入 agent。
5. Task-Scoped 只给当前 task 的 state/history。
6. 每个任务至少 3 次独立运行，报告均值和方差。

关键点:

- tau2 的 Pass^k 是 reliability 指标，特别适合证明上下文隔离降低随机失败。
- 不要只报 Pass^1，必须报 Pass^k 或多 run 方差。

## 实验 4: LongMemEval 长期记忆

目的:

- 验证方法不是简单丢弃历史，而是区分相关记忆和无关上下文。

数据:

- LongMemEval-S。
- LongMemEval-M。

指标:

- QA accuracy。
- recall@k，如果系统暴露 retrieval result。
- category accuracy: information extraction, multi-session reasoning, temporal reasoning, knowledge update, abstention。

做法:

1. 对每个用户历史建立 task-level memory index。
2. 比较全历史检索、embedding retrieval、task-aware retrieval。
3. 报告 recall@5/10 和最终 QA accuracy。
4. 对 temporal/update/abstention 单独分析。

关键消融:

- 只按 embedding similarity 检索。
- 加 task_id filter。
- 加 time-aware/task-aware summary。

## 实验 5: AgentIF-OneDay 普通用户日常任务

目的:

- 最贴近产品假设: 普通人用聊天软件发生活/办公/学习任务。

数据:

- AgentIF-OneDay 104 tasks, 767 scoring points。
- 类别: Open Workflow Execution, Latent Instruction, Iterative Refinement。
- 附件类型包括 PDF、PNG 等，要求输出文件。

指标:

- scoring-point accuracy。
- instance-level rubric score。
- 按三类任务分别统计。
- LLM judge 与人工一致性需要按官方 pipeline。

做法:

1. 接入官方数据和 verifier。
2. 对每个 task 运行 agent。
3. 对 Iterative Refinement 重点测试上下文隔离: 只保留当前 artifact/task 历史，而不是全 session。
4. 对 Latent Instruction 测试附件隐含规则是否被正确迁移，不被无关历史覆盖。

## 实验 6: Tool/Skill Router Stress Test

目的:

- 将公开 benchmark 的 tool/instruction 数据转成 router 诊断，而不是自造 toy case。

数据来源:

- AgentIF tool specification constraints。
- BFCL multi-turn / memory-management / irrelevance categories。
- tau2/tau3 domain tools。

指标:

- correct tool selected。
- wrong tool selected。
- no-tool-needed accuracy。
- wrong argument rate。
- stale-tool activation rate。

做法:

1. 从公开 benchmark 中提取每步 gold/expected tool 行为。
2. 给 agent 安装额外无关 tools/skills。
3. 观察 Full Session vs Task-Scoped + Tool Filter 的工具调用差异。
4. 报告 tool-level confusion matrix。

## 实验 7: 消融实验

至少做:

| Ablation | 问题 |
| --- | --- |
| 无 boundary detector，只用 recent-N | recent window 是否足够 |
| boundary detector only | 任务边界本身贡献 |
| retrieval only | embedding 检索是否会召回语义相似但任务错误的历史 |
| task summary only | summary 是否丢失关键局部细节 |
| task full context + summary | 准确率/成本折中 |
| tool filter on/off | 是否减少 wrong skill/tool activation |
| memory global/local | 个人偏好应该跨任务，临时变量不应该跨任务 |

## 实验 8: 成本与稳定性

必须报告:

- 输入 tokens。
- 输出 tokens。
- tool calls。
- wall-clock latency。
- per-task cost。
- failed tool-call retry count。
- benchmark score variance over repeated runs。

因为你的方法不仅要提升准确率，还应该减少无关历史带来的 token 成本和不稳定性。

