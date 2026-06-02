# Phase 6: 轻量分类器与成本优化

## 目标

把 Phase 2 中依赖 LLM judge 的上下文需求判断蒸馏成轻量分类器，降低 token 成本和延迟。

## 为什么需要

如果每条消息都调用大模型判断:

- token 成本高
- 延迟高
- benchmark 运行成本高
- 系统复杂度高

因此最终方案应是级联式:

```text
高精度规则 -> 轻量分类器 -> LLM judge only for uncertain cases -> clarification
```

## 训练数据来源

| 来源 | 标签 |
| --- | --- |
| AgentIF | no_context, tool/spec dependency, clarification |
| MultiChallenge | task_local, related_summary, version_editing, clarification |
| BFCL multi-turn | tool_state, tool_needed, no_tool_needed |
| LongMemEval / LoCoMo | global memory, temporal memory, update memory, abstention |
| tau2 | task_local, tool_state, clarification |
| cross-task stress sessions | unnecessary retrieval negatives |
| LLM judge sampled labels | ambiguous / hard cases |

## 标签体系

```text
no_context
task_local
related_summary
global_profile
project_memory
tool_state
clarification
```

辅助标签:

```text
self_sufficient: bool
need_history: bool
confidence: float
risk_if_using_history: low|medium|high
```

## 模型选择

从低到高:

1. 规则 + BM25 features + logistic regression。
2. sentence-transformer embedding + MLP。
3. 小型 encoder classifier。
4. 小 LLM few-shot classifier。
5. 蒸馏自强 LLM judge。

建议先做 1 和 2，因为成本低、可解释。

## 特征

- 当前消息 embedding。
- 最近任务摘要 embedding。
- 是否包含指代词。
- 是否包含工具状态词。
- 当前消息长度。
- 是否包含完整代码/数学表达式/文件引用。
- 与 active task summary 相似度。
- 与 global memory top-k 相似度。
- domain classifier 输出。

## 评估指标

- need-context accuracy。
- no-context precision。
- need-context recall。
- unnecessary retrieval rate。
- missed-context rate。
- LLM judge fallback rate。
- downstream benchmark score。
- router token / latency。

## 级联阈值

建议:

- 规则高置信直接返回。
- 轻量分类器置信度 > 0.85 直接返回。
- 置信度 0.55-0.85 调用 LLM judge。
- 置信度 < 0.55 且缺失对象明显，直接澄清。

阈值需要在 validation set 上调。

## 验收标准

- Cascaded Router 的下游分数接近 Always LLM Router。
- LLM judge 调用率显著低于 30%。
- token 成本低于 Always Retrieve 和 Always LLM Router。
- 不必要检索率显著下降。
