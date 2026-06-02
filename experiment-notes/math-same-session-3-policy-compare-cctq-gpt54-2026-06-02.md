# MATH Same-Session 三策略小样本对照

日期：2026-06-02

## 设置

Benchmark：

```text
EleutherAI/hendrycks_math
category: algebra
limit: 3
```

运行方式：

```text
同一个 session 中连续做 3 道公开 MATH 题。
每道题仍按 MATH 标准答案评分。
区别只在于当前题能看到哪些历史 turns。
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

| policy | normalized accuracy | selected history counts | input token estimates |
| --- | ---: | --- | --- |
| `task_scoped` | 3/3 | 0, 0, 0 | 92, 91, 97 |
| `full_session` | 3/3 | 0, 2, 4 | 92, 279, 424 |
| `recent_n` | 3/3 | 0, 2, 4 | 92, 284, 431 |

## 关键观察

1. 三个策略在这 3 道简单 algebra 题上都能答对。
2. `task_scoped` 判断每道题都是自足新任务，因此没有带入旧题历史。
3. `full_session` 会持续累积前面所有题，输入 token 估算从 92 增长到 424。
4. `recent_n=4` 在 3 道题内和 full session 基本等价，因为历史还没有超过 4 turns。
5. 这组样本还不足以证明准确率优势，但已经验证了成本和上下文污染暴露机制。

## 评分修正

`full_session` 第 3 题原始抽取为：

```text
\frac97
```

标准答案为：

```text
\dfrac{9}{7}
```

二者数学等价。已在 `experiments/math_eval.py` 中补充 TeX 简写分数归一化：

```text
\frac97 -> \frac{9}{7}
```

因此最终 normalized accuracy 为 3/3。

## 结果文件

```text
experiments/runs/math_same_session_task_scoped_3_cctq_gpt54_compare/results.json
experiments/runs/math_same_session_full_session_3_cctq_gpt54_compare/results.json
experiments/runs/math_same_session_recent_n_3_cctq_gpt54_compare/results.json
```

## 下一步

1. 对 AgentIF 运行同样的三策略真实小样本。
2. 在 AgentIF 中重点观察旧输出约束是否污染后续任务。
3. 后续扩大到 10 或 20 条时，优先看 token 增长、wrong constraint、stale instruction，而不是只看总分。
