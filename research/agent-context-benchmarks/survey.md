# Survey And Final Recommendation

检索日期: 2026-06-01

## 一句话结论

如果要做“普通用户长 session 中的 agent 上下文隔离”研究，主 baseline 应该从 LightAgent 切到 **MiroFlow**；主 benchmark 组合应该是 **AgentIF-OneDay + tau2/tau3 + AgentIF + LongMemEval + GAIA**。这套组合覆盖日常任务、多轮工具状态、长 agentic instruction、长期记忆和主流通用 agent 能力。

## 为什么不是只用一个 benchmark

你的问题不是单一能力，而是多个能力交叉:

- session 中任务边界识别
- 临时上下文隔离
- 长期记忆选择
- skill/tool router 选择
- 多轮状态维护
- 指令保持
- 成本和稳定性

没有一个公开 benchmark 完整覆盖这些维度。因此推荐用一个主 baseline + 五类公开 benchmark。

## Baseline 决策

### 主 baseline: MiroFlow

事实:

- 2026-02-26 arXiv 论文。
- 开源仓库: https://github.com/MiroMindAI/MiroFlow
- 论文称其为 high-performance and robust open-source agent framework。
- 报告 benchmark 包括 GAIA、BrowseComp-EN/ZH、HLE、xBench-DeepSearch、FutureX。
- 论文强调 reproducible performance、workflow robustness、tool coordination。

判断:

- 它是当前最适合做 2025-2026 新 baseline 的项目。
- 其 agent graph / robust workflow / tools 设计适合接入 context isolation wrapper。

### 方法论参考: OAgents

事实:

- 2025-06-23 arXiv。
- 对 GAIA 和 BrowseComp 做 agent 组件实证研究。
- 重点讨论 evaluation protocol、random variance、planning/memory/tool use 等设计选择。

判断:

- 你的实验消融可以直接借鉴 OAgents 的组件研究写法。

### 轻量 prototype: LightAgent

事实:

- 本地已 clone 到 `third_party/LightAgent`。
- `LightAgent.run(query, history=...)` 是清晰的插入点。

判断:

- 适合快速验证 wrapper，不适合作为主论文 baseline，因为缺少多 benchmark 历史结果。

## 最终实验路线

### Stage A: 快速验证

目标: 证明方法不是空想。

跑:

1. AgentIF small subset。
2. LongMemEval-S small subset。
3. LightAgent 或 MiroFlow wrapper smoke test。

输出:

- CSR/ISR 是否提升。
- recall@k / QA accuracy 是否提升。
- token cost 是否下降。

### Stage B: 主实验

目标: 支撑论文主结果。

跑:

1. GAIA-Val-Text 或 GAIA-Val。
2. AgentIF full。
3. tau2/tau3 selected domains。
4. LongMemEval-S/M。
5. AgentIF-OneDay。

输出:

- 通用 agent accuracy。
- Pass^k reliability。
- instruction CSR/ISR。
- memory QA/retrieval。
- daily-task rubric score。

### Stage C: 泛化实验

目标: 证明不是只在某类 benchmark 有效。

跑:

1. BrowseComp / BrowseComp-ZH。
2. xBench-DeepSearch。
3. WebArena subset。
4. SWE-Bench Lite, optional。

## 需要测试的数据集清单

必须:

- GAIA validation / GAIA-Val-Text。
- AgentIF。
- tau2/tau3。
- LongMemEval。
- AgentIF-OneDay。

建议:

- BrowseComp / BrowseComp-ZH。
- xBench-DeepSearch。
- WebArena。
- OpenHands benchmark subset。

可选:

- HLE。
- FutureX。
- SWE-Bench Lite/Verified。
- MultiChallenge。
- Multi-IF。

## 论文贡献写法

可以把你的方法表述为:

> We introduce task-level context isolation for chat-bound general agents. Unlike session-level context passing or pure recency/retrieval-based memory, our method separates transport sessions from reasoning tasks, maintains task-scoped working memory, and constrains tool/skill routing to the selected task scope.

核心对照:

- full session context
- recent-N context
- retrieval-only memory
- task-scoped context
- task-scoped + summary
- task-scoped + tool filter

核心证据:

- AgentIF: CSR/ISR 提升，说明长 instruction/tool spec 不易污染。
- tau2/tau3: Pass^k 提升，说明多轮工具状态更稳定。
- LongMemEval: recall@k/QA 提升，说明不是简单丢历史。
- GAIA: accuracy 不下降或提升，说明通用 agent 能力保持。
- AgentIF-OneDay: 日常任务 rubric 提升，说明贴近真实用户价值。

## 风险

1. MiroFlow 可能依赖昂贵模型/API，完整复现成本高。
2. AgentIF-OneDay 是 2026 新 benchmark，数据/代码入口可能还在更新。
3. tau2/tau3 交互式环境 debug 成本高。
4. GAIA 有部分数据访问限制和污染控制要求。
5. 如果只在构造的跨任务 session 上测，会被认为不是 benchmark 原生设置；需要清楚说明这是 benchmark-derived stress setting。

## 推荐下一步

1. Clone MiroFlow、AgentIF、LongMemEval、tau2-bench。
2. 先跑 AgentIF + LongMemEval 小子集，成本低、结果直接。
3. 实现统一 context policy wrapper 和日志格式。
4. 再接 MiroFlow GAIA-Val-Text。
5. 最后接 tau2/tau3 和 AgentIF-OneDay。

