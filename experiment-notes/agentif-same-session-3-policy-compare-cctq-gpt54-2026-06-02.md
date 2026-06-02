# AgentIF Same-Session 三策略小样本对照

日期：2026-06-02

## 设置

Benchmark：

```text
AgentIF
limit: 3
sample selection: 当前 runner 选择输入长度较短的样本
```

运行方式：

```text
同一个 session 中连续执行 3 条 AgentIF 任务。
每条任务仍按 AgentIF code constraint 评分。
区别只在于当前任务能看到哪些历史 turns。
```

模型：

```text
gpt-5.4 via https://www.cctq.ai/v1
```

策略：

- `task_scoped`
- `full_session`
- `recent_n`

## 结果

| policy | code-constraint pass | selected history counts | input token estimates |
| --- | ---: | --- | --- |
| `task_scoped` | 3/3 | 0, 0, 0 | 497, 498, 499 |
| `full_session` | 3/3 | 0, 2, 4 | 497, 1581, 2701 |
| `recent_n` | 3/3 | 0, 2, 4 | 497, 1508, 2621 |

## 关键观察

1. 三个策略在这 3 条短 AgentIF 样本上都通过了 code constraint。
2. `task_scoped` 判断每条 AgentIF 样本都是自足新任务，因此没有带入旧任务历史。
3. `full_session` 和 `recent_n=4` 会把前面任务及答案持续带入 prompt。
4. 第 3 条时，`task_scoped` 的输入估算约 499 tokens，而 `full_session` 已到 2701 tokens。
5. 这组样本还没有构成旧约束冲突，只证明了成本增长和历史注入机制。后续需要专门构造 `old_constraint_conflict` mixed session。

## 结果文件

```text
experiments/runs/agentif_same_session_task_scoped_3_cctq_gpt54_compare/results.json
experiments/runs/agentif_same_session_full_session_3_cctq_gpt54_compare/results.json
experiments/runs/agentif_same_session_recent_n_3_cctq_gpt54_compare/results.json
```

## 下一步

1. 构造 mixed single-session adapter。
2. 优先支持两个模板：
   - `same_domain_unrelated`
   - `old_constraint_conflict`
3. 从公开 MATH / AgentIF 样本生成 session，不手写 benchmark 题目。
4. 评测除 benchmark 原生分数外，还记录：
   - selected history count
   - input token estimate
   - unnecessary context rate
   - forbidden context inclusion
