# Phase 5: 实验与消融

更新时间: 2026-06-02。

## 目标

形成可写论文的实验闭环:

1. 主实验: 证明 task-scoped context isolation 在公开 benchmark 上有效。
2. 消融: 证明 need gate、task boundary、retrieval、tool filter 各自有贡献。
3. 成本: 证明不是靠更多 token 和更多检索换分数。
4. 错误分析: 明确方法在哪些任务会失败。

## 主实验表

| Benchmark | Full Session | Recent-N | Retrieval-Only | Need-Gated | Task-Scoped | Task+Tool Filter | Oracle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AgentIF | CSR/ISR | CSR/ISR | CSR/ISR | CSR/ISR | CSR/ISR | 可选 | Oracle boundary |
| MultiChallenge | APR/ARS | APR/ARS | APR/ARS | APR/ARS | APR/ARS | 可选 | Oracle needed turns |
| BFCL multi-turn | Tool Acc | Tool Acc | Tool Acc | Tool Acc | Tool Acc | Tool Acc | Oracle tool |
| LongMemEval/LoCoMo | QA/Recall | QA/Recall | QA/Recall | QA/Recall | QA/Recall | 不适用 | Oracle evidence |
| tau-bench/tau2 | Pass^k | Pass^k | 可选 | 可选 | Pass^k | Pass^k | Oracle task |
| ToolSandbox | State/Trace | State/Trace | 可选 | 可选 | State/Trace | State/Trace | Oracle state |
| STATE-Bench | pass@1/pass^5 | pass@1/pass^5 | 可选 | 可选 | pass@1/pass^5 | pass@1/pass^5 | 可选 |

## 实验策略定义

### Full Session

输入当前消息和完整历史。模拟聊天软件里把所有上下文都塞进同一 session。

预期问题:

- 无关旧任务污染当前回答。
- 旧工具调用结果被误用。
- 输入 token 最高。

### Recent-N

只保留最近 N 轮，N 先设为 4、8、16。

预期问题:

- 旧但必要的信息可能被截掉。
- 最近但无关的信息仍会污染当前任务。

### Retrieval-Only

每条消息都从全历史中检索 top-k，k 先设为 3、5、10。

预期问题:

- 自足问题也会检索，产生 unnecessary retrieval。
- embedding 相似但任务无关的历史可能被召回。

### Need-Gated

先判断当前消息是否信息充足。只有不充足时才检索历史。

关键问题:

- gate 不能完全依赖人工规则。
- 要统计 false_self_sufficient 和 unnecessary_retrieval。

### Task-Scoped

先判断当前消息属于新任务、继续任务、相关任务还是需要澄清。只在相关 task scope 内选择上下文。

关键问题:

- 同领域但无关任务不能混在一起。
- 显式引用前文时必须能找回必要上下文。

### Task+Tool Filter

在 Task-Scoped 基础上，只把当前 task 相关的 tool/skill 暴露给 agent。

关键问题:

- 不能错删必要工具。
- 要降低 wrong tool 和 irrelevant tool call。

### Oracle

使用人工或 benchmark 标注给任务边界、证据或工具选择上界。

用途:

- 判断当前方法离理论上界还有多远。
- 不作为真实部署方案。

## 消融实验

| 消融 | 删除内容 | 目的 |
| --- | --- | --- |
| No Need Gate | 每轮都执行 retrieval/boundary | 测 need gate 对成本和污染的贡献 |
| No Boundary | 只按相似度检索 | 测 task boundary 对 same-domain-unrelated 的贡献 |
| No Retrieval | 只用当前消息和最近 turns | 测记忆检索对 explicit-reference 的贡献 |
| No Summary | 只用 raw turns | 测 task summary 是否降低 token 且保留信息 |
| No Tool Filter | 工具全集暴露 | 测 tool filter 对 BFCL/tau2 的贡献 |
| No Evidence Validation | 不验证召回证据是否支持回答 | 测错误记忆过滤贡献 |
| Rule Gate Only | 只用规则判断自足 | 测纯规则上限 |
| LLM Gate Only | 每轮都用大模型 gate | 测效果上限和 token 成本 |
| Cascaded Gate | 规则 + 小分类器 + 必要时 LLM | 主方案 |
| Oracle Boundary | 真实任务边界 | 测边界模块上界 |

## 成本实验

比较对象:

- Always Full Session。
- Always Retrieve。
- Always LLM Router。
- Rule-only Gate。
- Small Classifier Gate。
- Cascaded Gate。

统计:

- LLM router 调用率。
- 平均 input tokens，单位 M。
- 平均 output tokens，单位 M。
- 平均 cache tokens，单位 M。
- 平均 tool calls。
- 平均 latency。
- benchmark score。
- cost per correct task。

报告格式:

| Policy | Score | Input M | Output M | Cache M | Tool Calls | Latency | Cost/Correct |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 错误分析分类

| Error Type | 说明 | 主要出现 benchmark |
| --- | --- | --- |
| false_self_sufficient | 实际需要上下文，却判断自足 | LongMemEval、MultiChallenge |
| unnecessary_retrieval | 实际自足，却检索历史 | LongMemEval、AgentIF |
| wrong_task_boundary | 新任务/继续任务/相关任务判断错 | 全部 |
| wrong_memory | 召回错误记忆并使用 | LongMemEval、LoCoMo |
| missed_memory | 漏掉必要记忆 | LongMemEval、MultiChallenge |
| stale_instruction | 使用旧任务 instruction/constraint | AgentIF、MultiChallenge |
| stale_tool_state | 使用过期工具状态 | ToolSandbox、tau2 |
| wrong_tool | 选错 skill/tool | BFCL、tau2、STATE-Bench |
| wrong_argument | 工具正确但参数错误 | BFCL、tau2 |
| over_filter_tool | tool filter 错删必要工具 | BFCL、tau2 |
| summary_loss | task summary 丢失关键信息 | LongMemEval、MultiChallenge |
| should_clarify | 应澄清但没有澄清 | MultiChallenge、tau2 |

## 运行阶段

### Stage 0: 单 benchmark 调试

每个 adapter 先跑 5 条:

- 只测数据加载。
- 只测 scorer。
- 只测日志输出。
- 不比较方法效果。

当前状态:

- AgentIF、MATH、Mixed Session、BFCL、LongMemEval 的基础 adapter 或 runner 已跑通。
- BFCL 已接入官方 checker 的直接调用 smoke。
- LongMemEval 已完成 oracle、旧 lexical、新 `lexical_turn + weighted` 的 smoke 对比。

### Stage 1: P0 Smoke

规模:

- AgentIF 20。
- BFCL 20。
- LongMemEval/LoCoMo 20。
- MultiChallenge 20。

策略:

- `full_session`。
- `recent_n`。
- `need_gated`。
- `task_scoped`。
- BFCL 额外跑 `task_scoped_tool_filter`。

目标:

- 判断方法是否明显减少污染或工具误选。
- 估算每题 token 和耗时。

当前新增策略:

- `lexical_turn`: LongMemEval 专用非 oracle 检索策略，按 turn-level weighted evidence 给 session 排名。
- `weighted` turn mode: 在选中 session 内按 IDF 加权问题词 overlap 选择 top-k turn。
- LongMemEval QA prompt 增加答案类型约束，用于减少“证据来源”和“动作发生地点”混淆。

当前小样本结论:

- 旧 `lexical` 前 5 条 session hit 为 4/5，真实 QA 3 条为 1/3。
- 新 `lexical_turn + weighted` 前 20 条 session hit 为 20/20，前 100 条为 94/100。
- 固定把 LongMemEval `max_sessions` 从 3 提高到 8 后，前 100 条 session hit 提升到 97/100，但 token 从 0.4477M 增加到 1.0883M，不适合作为默认主策略。
- 新 `lexical_turn + weighted + answer-type prompt` 真实 QA 3 条为 3/3，输入 token 约为 full session 的 2.62%。

下一步:

- 分析 LongMemEval 100 条 dry-run 的 6 个 miss，重点看抽象改写和 multi-session。
- 实现 adaptive session budget: 默认取 3 个 session，multi-session/聚合/低置信时扩到 6 或 8。
- LongMemEval 真实模型先跑 10 条，确认新策略是否稳定。
- 实现 benchmark mixer，把 AgentIF、MATH、LongMemEval QA task 以 task 为单位混入同一 session，并支持可控冲突规则。

### Stage 2: P0 小规模正式实验

规模:

- AgentIF 100 到 300。
- BFCL 100 到 300。
- LongMemEval/LoCoMo 100 到 300。
- MultiChallenge 50 到 100。

策略:

- 跑完整主实验表。
- 每个策略先 1 次。
- 有提升后关键策略 3 次重复。

### Stage 3: P1 End-to-End

规模:

- tau2 30 到 100。
- ToolSandbox 30 到 100。
- STATE-Bench 10 到 30。

策略:

- `full_session`。
- `recent_n`。
- `task_scoped_tool_filter`。
- 预算允许再补 `retrieval_only` 和 `need_gated`。

### Stage 4: 论文级补强

条件:

- P0 至少 3 个 benchmark 有稳定提升。
- 成本没有显著增加。
- P1 至少一个 benchmark 有正结果。

补强:

- 扩大样本。
- 增加重复运行。
- 做显著性分析。
- 整理 case study。

## 最小可发表结果

必须包含:

1. AgentIF 100+。
2. BFCL multi-turn/relevance 100+。
3. LongMemEval 或 LoCoMo 100+。
4. MultiChallenge 50+。
5. 一个 P1 benchmark 小样本，优先 tau2。
6. 完整消融表。
7. 成本表。
8. 错误分析。

## 强结果版本

增加:

1. AgentIF full。
2. BFCL 大子集或 full。
3. LongMemEval-S/M。
4. LoCoMo。
5. tau2 一个完整 domain。
6. ToolSandbox 大子集。
7. STATE-Bench 小样本。

## 预算规则

默认不直接全量运行。

任何满足以下条件之一，运行前都需要重新确认:

- 单 benchmark 超过 100 条。
- 单次实验输入 token 预计超过 1M。
- 单次实验输出 token 预计超过 0.2M。
- 使用需要付费的外部搜索、浏览器或 sandbox 服务。
- 需要 judge LLM 大规模评分。
