# Task-Scoped Context Isolation Implementation Plans

日期: 2026-06-02

目标: 基于轻量 agent runtime 实现并评估“聊天式 agent 的任务级上下文隔离”。MiroFlow 不再作为主实现 baseline，只作为强系统参考和可选集成目标。

## 为什么调整

前期尝试复现 MiroFlow 后确认:

- MiroFlow 是 deep-research agent，默认依赖搜索、网页读取、代码沙箱、多 worker 总结。
- 完整工具链需要 `SERPER_API_KEY`、`JINA_API_KEY`、`E2B_API_KEY`、reasoning LLM 等外部服务。
- 单题成本和时间过高，不适合作为日常方法开发 baseline。
- 本研究核心是长聊天 session 的上下文污染、任务边界、记忆检索和 skill/tool 路由，不需要从完整 deep-research agent 起步。

因此主线改为:

```text
LightAgent/LangGraph 轻量主实现
  + 公开 benchmark adapter
  + Task-Scoped Context Isolation
  + MiroFlow 作为强参考/可选集成
```

## 文档结构

| 阶段 | 文档 | 目标 |
| --- | --- | --- |
| Handoff | [00-new-chat-handoff.md](00-new-chat-handoff.md) | 新开对话后的总交接文档，说明完整目标、阶段、接口和下一步 |
| Phase 0 | [phase-0-repo-and-baseline.md](phase-0-repo-and-baseline.md) | 确认 baseline 决策，保留 MiroFlow 调研结论，准备 LightAgent/LangGraph 主线 |
| Phase 1 | [phase-1-context-layer-design.md](phase-1-context-layer-design.md) | 设计通用上下文隔离层的数据结构和接口 |
| Phase 2 | [phase-2-router-and-gates.md](phase-2-router-and-gates.md) | 实现自足性判断、上下文需求路由、任务边界检测 |
| Phase 3 | [phase-3-miroflow-integration.md](phase-3-miroflow-integration.md) | 接入轻量 agent runtime；MiroFlow 只做可选集成 |
| Phase 4 | [phase-4-benchmark-adapters.md](phase-4-benchmark-adapters.md) | 接入 AgentIF、MultiChallenge、BFCL、LongMemEval/LoCoMo 等公开 benchmark |
| Phase 5 | [phase-5-experiments-and-ablations.md](phase-5-experiments-and-ablations.md) | 设计主实验、消融、成本和错误分析 |
| Phase 6 | [phase-6-classifier-and-optimization.md](phase-6-classifier-and-optimization.md) | 用日志训练轻量 context need classifier，降低 LLM router 成本 |
| Phase 7 | [phase-7-paper-ready-package.md](phase-7-paper-ready-package.md) | 整理论文级复现、表格、图和风险检查 |

## Baseline 决策

### 主实现 baseline

优先:

```text
LightAgent
```

原因:

- 轻量，便于改 `history`、memory、skill router。
- 符合普通用户聊天软件里的 agent 使用形态。
- 可快速实现 full-session、recent-N、retrieval-only、task-scoped 等对照策略。

备选:

```text
LangGraph
```

原因:

- 状态图和 memory/control-flow 更规范。
- 适合做干净的论文 prototype。
- 但它更像 framework，需要自己定义固定 agent runtime。

### 强参考 baseline

```text
MiroFlow
```

用途:

- 引用官方 reported scores。
- 作为 deep-research agent 相关系统参考。
- 可选做 1 到 3 道 smoke 或最终 optional integration。

不再用于:

- 主方法实现。
- 反复调参。
- 低成本大批量实验。

## 总体原则

1. 主实现不再依赖完整 MiroFlow 工具链。
2. 方法实现为可插拔 context policy layer，优先接 LightAgent/LangGraph。
3. 每个 benchmark 保留原始评分器，不修改答案标准。
4. 主实验优先使用不依赖 live web 的 benchmark。
5. Web/deep-search 类 benchmark 只作为补充，不作为主实验。
6. 所有策略都必须记录 trace，方便错误分析和消融。

## 核心对照策略

- `full_session`: 全聊天历史直接进入 agent。
- `recent_n`: 只保留最近 N 轮。
- `retrieval_only`: 对全 session 做检索。
- `need_gated`: 先判断是否需要上下文，再检索。
- `task_scoped`: 任务级上下文隔离。
- `task_scoped_tool_filter`: 任务级隔离 + tool/skill 候选过滤。
- `oracle_boundary`: 用 oracle task id 做上界。

## 主 benchmark

优先级:

1. AgentIF: 长 agentic instruction、上下文依赖、约束污染。
2. MultiChallenge: 多轮聊天上下文漂移、指令保持和版本编辑。
3. BFCL multi-turn: function/tool routing。
4. LongMemEval / LoCoMo: 长期记忆检索和上下文需求门控。
5. tau-bench / tau2-bench: 用户-agent-tool 状态任务。
6. ToolSandbox: 状态化工具执行。

补充:

- GAIA text-only 小样本。
- MiroFlow/HLE smoke。
- STATE-Bench 小样本。
- BrowseComp / xBench 只在预算充足且需要 deep-search 泛化时做。
