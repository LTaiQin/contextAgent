# Mixed Old-Constraint Filtered 真实小样本

日期：2026-06-02

## 目标

在 mixed single-session runner 中开启真实模型调用，测试 `old_constraint_conflict` 模板。

模板含义：

```text
AgentIF -> AgentIF -> AgentIF -> AgentIF -> AgentIF
```

这些任务来自公开 AgentIF。每个任务都被视为一个新的、自足任务，因此先前任务都是 forbidden context。

## 数据筛选修正

第一次真实运行时发现一个问题：

- 第 5 条 AgentIF 样本本身显式引用 previous context。
- 但 `old_constraint_conflict` 模板假设每条任务都是新任务。
- 因此该样本不适合放入该模板。

已修正：

```text
experiments/run_mixed_single_session_policy.py
```

现在用于新任务模板的 AgentIF 样本会排除包含以下历史引用的样本：

```text
previous / above / earlier / continue / history / context
刚才 / 上一个 / 继续 / 前面 / 上面 / 沿用 等
```

## 设置

模型：

```text
gpt-5.4 via https://www.cctq.ai/v1
```

策略：

- `task_scoped`
- `full_session`
- `recent_n`

样本数：

```text
limit = 5
```

其中：

- 4 条有可执行 AgentIF code scorer。
- 1 条没有 code scorer，标记为 `NO_CODE_SCORE`，不计入 benchmark pass/fail。

## 结果

| policy | benchmark scored pass | no-code-score | context_ok | forbidden_inclusion | input token estimate total |
| --- | ---: | ---: | ---: | ---: | ---: |
| `task_scoped` | 4/4 | 1 | 5/5 | 0 | 5329 |
| `full_session` | 4/4 | 1 | 1/5 | 4 | 12787 |
| `recent_n` | 4/4 | 1 | 1/5 | 4 | 11130 |

## 关键观察

1. 这组 5 条样本中，三种策略在有 code scorer 的 4 条上都通过。
2. `task_scoped` 的上下文选择 5/5 正确，没有引入旧 AgentIF 任务。
3. `full_session` 从第 2 条开始持续引入旧任务，context_ok 只有 1/5。
4. `recent_n` 虽然截断窗口，但仍会引入最近旧任务，context_ok 也是 1/5。
5. `task_scoped` 的输入 token 估算总量为 5329，明显低于 `full_session` 的 12787 和 `recent_n` 的 11130。

## 结论

短样本上，原生 AgentIF code-constraint 分数还没有拉开差距；但 context-level 指标已经稳定显示：

```text
full_session / recent_n 会系统性把 forbidden context 放入 prompt；
task_scoped 可以避免这类旧约束污染风险，并显著降低输入 token。
```

这支持后续扩大到更多样本，重点观察：

- stale constraint 是否开始影响原生 AgentIF 分数。
- 当任务更长、约束更冲突时，full/recent 是否更容易失败。
- task_scoped 的 token 优势是否随 session 变长继续扩大。

## 结果文件

```text
experiments/runs/mixed_old_constraint_task_scoped_5_filtered_cctq_gpt54_compare/results.json
experiments/runs/mixed_old_constraint_full_session_5_filtered_cctq_gpt54_compare/results.json
experiments/runs/mixed_old_constraint_recent_n_5_filtered_cctq_gpt54_compare/results.json
```

## 下一步

1. 跑 `same_domain_unrelated` 的 MATH 5 到 10 条真实 mixed。
2. 跑 `old_constraint_conflict` 的 AgentIF 10 条真实 mixed。
3. 如果 10 条仍然原生分数无差距，扩大到 20 条，但先估算成本。
