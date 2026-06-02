# Mixed Single-Session Policy Dry-Run

日期：2026-06-02

## 目标

实现并验证 mixed single-session adapter 的第一版。

该 adapter 不先调用模型，而是用公开 benchmark 样本构造一个长 session，然后只评估上下文策略是否错误引入历史。

核心指标：

- `context_ok`
- `unnecessary_context`
- `forbidden_inclusion`
- `input_tokens_est_total`

## 新增 runner

```text
experiments/run_mixed_single_session_policy.py
```

支持策略：

- `task_scoped`
- `full_session`
- `recent_n`
- `retrieval_only`
- `need_gated`

支持模板：

- `same_domain_unrelated`
- `cross_domain_switch`
- `old_constraint_conflict`

当前 dry-run 不调用模型，因此无 API 成本。

## 模板 1：cross_domain_switch

顺序：

```text
MATH -> AgentIF -> MATH -> AgentIF
```

每个任务都是公开 benchmark 中的自足任务。所有先前 task 都标记为当前 task 的 forbidden context。

结果：

| policy | context_ok | unnecessary_context | forbidden_inclusion | input token estimate total |
| --- | ---: | ---: | ---: | ---: |
| `task_scoped` | 4/4 | 0 | 0 | 1178 |
| `full_session` | 1/4 | 3 | 3 | 2601 |
| `recent_n` | 1/4 | 3 | 3 | 2498 |

结论：

- `task_scoped` 正确判断 4 个任务都是新任务，不带旧历史。
- `full_session` 和 `recent_n` 从第 2 个任务开始带入旧任务。
- `recent_n` 虽然截断了历史，但仍会带入 forbidden context。

## 模板 2：old_constraint_conflict

顺序：

```text
AgentIF -> AgentIF -> AgentIF -> AgentIF
```

使用公开 AgentIF 样本，并尽量选择不同 constraint 描述的任务，模拟旧输出约束污染。

结果：

| policy | context_ok | unnecessary_context | forbidden_inclusion | input token estimate total |
| --- | ---: | ---: | ---: | ---: |
| `task_scoped` | 4/4 | 0 | 0 | 2938 |
| `full_session` | 1/4 | 3 | 3 | 6119 |
| `recent_n` | 1/4 | 3 | 3 | 5614 |

结论：

- `task_scoped` 没有把旧 AgentIF 指令和输出约束带入新任务。
- `full_session` 和 `recent_n` 都会把旧约束所在任务带入当前 prompt。
- 这为后续真实模型调用中的 stale constraint 错误分析提供了可控 session。

## 结果文件

```text
experiments/runs/mixed_cross_domain_task_scoped_dryrun/results.json
experiments/runs/mixed_cross_domain_full_session_dryrun/results.json
experiments/runs/mixed_cross_domain_recent_n_dryrun/results.json
experiments/runs/mixed_old_constraint_task_scoped_dryrun/results.json
experiments/runs/mixed_old_constraint_full_session_dryrun/results.json
experiments/runs/mixed_old_constraint_recent_n_dryrun/results.json
```

## 和前面真实小样本的关系

MATH 和 AgentIF 的真实 3 策略小样本显示：

- 短样本准确率暂时没有差距。
- `task_scoped` 的输入历史明显更少。

mixed dry-run 进一步显示：

- 如果以 task-level forbidden context 为标签，`full_session/recent_n` 会系统性引入不该进入 prompt 的旧任务。
- 这个指标比单纯 accuracy 更直接对应本项目的研究问题。

## 下一步

1. 在 mixed runner 中加入真实模型调用模式。
2. 对 `old_constraint_conflict` 做 5 到 10 条真实调用，观察 stale constraint 是否影响 AgentIF 原生分数。
3. 加入 `same_domain_unrelated` 的 MATH 10 条 dry-run 和真实调用。
4. 后续再接入 LongMemEval / BFCL，覆盖 memory 和 tool routing。
