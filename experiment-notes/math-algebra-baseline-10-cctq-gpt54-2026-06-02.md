# MATH Algebra Baseline 10 条 Smoke

日期: 2026-06-02。

## 这是什么测试任务

本次跑的是 Hendrycks MATH benchmark 的 algebra test 小样本。

MATH 是竞赛数学 benchmark，题目比 GSM8K 更难，覆盖:

- algebra
- geometry
- number theory
- counting and probability
- prealgebra
- precalculus
- intermediate algebra

本次由于 HuggingFace 临时 DNS 问题，跨类别 parquet 下载失败；本地已经成功下载 algebra test，所以先跑:

```text
MATH algebra test 前 10 题
```

这次是独立单题 baseline，不是同 session 上下文污染测试。

## 配置

```text
agent: LightAgent baseline
policy: independent / history=[]
model: gpt-5.4
base_url: https://www.cctq.ai/v1
API format: /v1/chat/completions
benchmark: EleutherAI/hendrycks_math
category: algebra
sample_count: 10
tmux session: math10_gpt54
```

说明:

- 没有接入我们的 `ContextPolicy`。
- 没有使用历史上下文。
- 没有使用工具。
- 没有使用 MiroFlow。
- 清空了 LightAgent 默认内置工具。

## Runner

```text
/22liushoulong/agent/agent-context-isolation/experiments/run_math_baseline_10_tmux.py
```

结果目录:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/math_algebra_baseline_10_cctq_gpt54/
```

结果文件:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/math_algebra_baseline_10_cctq_gpt54/results.json
```

## 结果

严格字符串 exact:

```text
6 / 10
```

宽松 LaTeX normalization:

```text
10 / 10
```

严格 exact 中的 4 个 FAIL 都是格式等价问题:

| n | prediction | gold | 判断 |
| ---: | --- | --- | --- |
| 3 | `\frac{9}{7}` | `\dfrac{9}{7}` | 等价 |
| 7 | `[-2,\,7]` | `x \in [-2,7]` | 等价 |
| 8 | `7\%` | `7` | 题目要求 percent rate，等价 |
| 9 | `4,\ 6,\ 14,\ 15` | `4,6,14,15` | 等价 |

因此，本次人工可接受/宽松归一化结果为:

```text
10 / 10
```

## 重要限制

这不是完整 MATH benchmark 分数。

原因:

1. 只跑了 algebra 前 10 题。
2. 不是跨类别抽样。
3. 当前 scorer 是本地简化答案抽取和 normalization。
4. 没有使用官方完整 MATH evaluator。
5. 没有做 same-session stress。

## 对当前研究的意义

这个结果说明:

- `cctq gpt-5.4 + LightAgent` 在独立 MATH algebra 小样本上表现正常。
- MATH 数据读取、答案抽取、tmux 实时日志都可用。
- 后续可以构造数学同 session stress:
  - 多道独立题连续出现。
  - 多题使用相同变量名 `x`。
  - 当前题自足，但历史中有相似题。
  - 当前题明确引用上一题结果。

下一步建议:

1. 下载更多 MATH 类别，跑跨类别 20 条。
2. 实现更稳的数学答案 evaluator。
3. 构造同 session stress，比较 `full_session` 和 `task_scoped`。
