# 实验设计

检查日期: 2026-06-02。

## 目标

验证 Task-Scoped Context Isolation 是否能在公开 benchmark 上减少上下文污染、错误记忆检索和错误 skill/tool routing，同时降低输入 token 与工具调用成本。

## 评测对象

主实现 baseline:

- LightAgent 原始版本。
- LightAgent + context policy wrapper。

参考 baseline:

- LangGraph，作为备选框架。
- MiroFlow，只作为强 agent paper/reference，不作为主实验实现线。

## 策略对比

| 策略 | 含义 | 目的 |
| --- | --- | --- |
| `full_session` | 当前消息加完整聊天历史 | 模拟普通聊天软件绑定 agent 的默认风险 |
| `recent_n` | 当前消息加最近 N 轮 | 工程常见低成本策略 |
| `retrieval_only` | 每轮都从全历史检索 top-k | 常见 memory/RAG 策略 |
| `need_gated` | 先判断当前消息是否自足，需要时才检索 | 验证“不必每句话都检索历史” |
| `task_scoped` | 判断任务边界，只在相关 task 内选上下文 | 主方法 |
| `task_scoped_tool_filter` | task-scoped context 加 task-local 工具候选过滤 | 验证 skill/router 改进 |
| `oracle_boundary` | 用人工或 benchmark 标注给任务边界 | 方法上界，不作为真实系统 |

## 公开 Benchmark

| 优先级 | Benchmark | 运行目的 | 首轮规模 |
| --- | --- | --- | --- |
| P0 | AgentIF | 测旧 instruction/constraint 是否污染新任务 | 20 smoke，正式 100 到 300 |
| P0 | MultiChallenge | 测真实多轮聊天中的上下文漂移 | 20 smoke，正式 50 到 100 |
| P0 | BFCL multi-turn | 测 skill/tool router 和无关工具调用 | 20 smoke，正式 100 到 300 |
| P0 | LongMemEval / LoCoMo | 测记忆检索门控、更新、拒答 | 20 smoke，正式 100 到 300 |
| P1 | tau-bench / tau2-bench | 测端到端用户-agent-tool 状态任务 | 10 smoke，正式 30 到 100 |
| P1 | ToolSandbox | 测状态化工具轨迹污染 | 10 smoke，正式 30 到 100 |
| P1 | STATE-Bench | 测企业 workflow、memory、skills | 10 smoke，正式视成本决定 |
| P2 | GAIA text-only / MiroFlow HLE smoke | 只做参考展示 | 不做主实验 |

## 指标

### Benchmark 原始指标

- AgentIF: CSR、ISR、constraint type score。
- MultiChallenge: APR、ARS。
- BFCL: overall accuracy、multi-turn accuracy、AST/executable accuracy。
- LongMemEval/LoCoMo: QA accuracy、recall@k、category accuracy、abstention。
- tau-bench/tau2: Pass^1、Pass^k、final state correctness。
- ToolSandbox: milestone DAG、snapshot similarity、tool trace similarity、guardrail similarity。
- STATE-Bench: pass@1、pass^5、UX Score、Cost Per Task。

### 本项目额外指标

- `context_contamination_rate`: 无关历史影响最终回答的比例。
- `unnecessary_retrieval_rate`: 当前消息自足但仍检索历史的比例。
- `missed_context_rate`: 当前消息需要历史但未取到关键上下文的比例。
- `wrong_memory_rate`: 取到错误记忆并用于回答的比例。
- `wrong_tool_rate`: 选择错误 skill/tool 的比例。
- `irrelevant_tool_call_rate`: 当前任务不需要工具但仍调用工具的比例。
- `stale_tool_state_rate`: 使用旧任务的工具状态或旧结果的比例。
- `input_tokens_m`: 输入 token，单位 M。
- `output_tokens_m`: 输出 token，单位 M。
- `cache_tokens_m`: 缓存 token，单位 M。
- `latency_sec`: 每题耗时。

## Stress Session 构造

不自己发明 benchmark 题目，只在公开 benchmark 样例外层构造 session 历史。评分仍使用官方样例和官方评分器。

| 干扰类型 | 说明 | 对应 benchmark |
| --- | --- | --- |
| different-domain | 历史任务来自完全不同领域 | AgentIF、BFCL、LongMemEval |
| same-domain-unrelated | 同领域但任务互不相关，例如两道独立数学题 | AgentIF、MultiChallenge、LongMemEval |
| same-tool-unrelated | 旧任务和当前任务都可调用同类工具，但目标不同 | BFCL、ToolSandbox、tau2 |
| related-summary-needed | 当前任务只需要旧任务摘要，不需要完整 raw turns | LongMemEval、MultiChallenge |
| explicit-reference | 当前消息明确引用前文 | MultiChallenge、LongMemEval |
| ambiguous-reference | 当前消息指代不清，系统应澄清 | MultiChallenge、tau2 |

## 阶段实验

### Stage A: 低成本 smoke

目标:

- 确认 adapter、评分器、日志、token 统计都能工作。
- 不追求统计显著性。

规模:

- AgentIF 20。
- BFCL 20。
- LongMemEval/LoCoMo 20。
- MultiChallenge 20。

通过标准:

- 每个 benchmark 至少能输出官方指标和本项目额外指标。
- 日志能记录 selected context、need gate 决策、task boundary、tool candidates。

### Stage B: P0 小规模正式实验

目标:

- 判断方法是否值得继续扩大。

规模:

- AgentIF 100 到 300。
- BFCL 100 到 300。
- LongMemEval/LoCoMo 100 到 300。
- MultiChallenge 50 到 100。

运行:

- 每个策略至少 1 次。
- 若结果有提升，再对关键策略跑 3 次重复。

### Stage C: P1 end-to-end agent 实验

目标:

- 证明方法不只在离线评分里有效，也能改善真实多轮工具 agent。

规模:

- tau2 一个 domain 30 到 100。
- ToolSandbox 30 到 100。
- STATE-Bench 小样本 10 到 30。

运行:

- 先只跑 `full_session`、`recent_n`、`task_scoped_tool_filter`。
- 有预算再补全 `retrieval_only` 和 `need_gated`。

### Stage D: 消融和上界

目标:

- 证明每个模块的贡献。

消融:

- 去掉 need gate。
- 去掉 task boundary。
- 去掉 evidence validation。
- 去掉 tool filter。
- 去掉 summary，只用 raw retrieval。
- 用 oracle boundary 给上界。

## 成本控制

默认执行顺序:

1. 每个 benchmark 先跑 5 条调试。
2. 再跑 20 条 smoke。
3. smoke 结果进入文档后，由用户决定是否扩大到正式规模。

任何超过以下规模的运行都需要单独确认:

- 单 benchmark 超过 100 条。
- 单次运行预计输入 token 超过 1M。
- 单次运行预计输出 token 超过 0.2M。
- 需要外部搜索、浏览器、sandbox 付费 API。

## 最小可发表实验包

最低要求:

1. AgentIF 100+。
2. BFCL multi-turn 100+。
3. LongMemEval/LoCoMo 100+。
4. MultiChallenge 50+。
5. 完整策略对比和成本表。
6. 至少一个 P1 benchmark 小样本验证，优先 tau2 或 ToolSandbox。

强结果版本:

1. AgentIF full。
2. BFCL multi-turn full 或大子集。
3. LongMemEval-S/M。
4. tau2 一个完整 domain。
5. ToolSandbox 大子集。
6. STATE-Bench 小样本。
