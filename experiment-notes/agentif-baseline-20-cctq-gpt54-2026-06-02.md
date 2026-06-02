# AgentIF Baseline 20 条 Smoke

日期: 2026-06-02。

## 这是什么测试任务

本次跑的是 **AgentIF** 的公开 benchmark 小样本。

AgentIF 不是数学题，也不是知识问答。它主要测试 agent 是否能遵守复杂指令和约束，例如:

- 必须输出指定章节。
- 必须只输出指定选项之一。
- 必须遵守格式限制。
- 必须遵守系统指令里的任务规则。
- 某些样本会涉及工具/代码类约束。

本次为了控制成本，选的是 AgentIF 全量 707 条中 prompt 最短的 20 条。它们主要包含两类:

1. 空气质量 + 用户健康状况 + 必须输出四个健康建议章节。
2. 只允许输出 `products`、`support`、`finance` 三个选项之一。

## 配置

```text
agent: LightAgent baseline
policy: full_session / 原始 baseline
model: gpt-5.4
base_url: https://www.cctq.ai/v1
API format: /v1/chat/completions
benchmark: AgentIF
sample_count: 20
tmux session: agentif20_gpt54
```

说明:

- 没有接入我们的 `ContextPolicy`。
- 没有做上下文污染 stress session。
- 没有使用 MiroFlow。
- 没有调用外部搜索、浏览器、E2B、Jina、Serper。
- 清空了 LightAgent 默认内置工具，避免工具暴露影响 AgentIF 指令测试。

## 运行命令

```bash
tmux attach -t agentif20_gpt54
```

实际 runner:

```text
/22liushoulong/agent/agent-context-isolation/experiments/run_agentif_baseline_20_tmux.py
```

结果目录:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/agentif_baseline_20_cctq_gpt54/
```

## 结果

```text
pass: 20
fail: 0
total: 20
```

20 条样本 idx:

```text
[405, 377, 99, 9, 333, 171, 259, 462, 475, 256, 492, 37, 349, 54, 61, 224, 106, 192, 175, 147]
```

结果文件:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/agentif_baseline_20_cctq_gpt54/results.json
```

## 成本粗估

这 20 条的本地字符统计:

```text
chars_sum: 38,015
query_chars_sum: 35,507
avg_chars_per_sample: 1,900.75
```

按字符/token 粗略换算:

| chars/token | 输入 token 估计 |
| ---: | ---: |
| 2.5 | 0.0152M |
| 3.0 | 0.0127M |
| 3.5 | 0.0109M |
| 4.0 | 0.0095M |

这批是最短样本，所以不能用它线性代表全量 AgentIF。全量 AgentIF 的平均样本长度明显更高。

## 重要限制

这不是完整 AgentIF 官方分数。

原因:

1. 只跑了 20 条最短样本。
2. 当前只执行了样本里可直接运行的 `code` constraint 检查。
3. 没有覆盖全部 constraint 类型。
4. 没有接完整 CSR/ISR 官方 scorer。
5. 没有测试上下文污染。
6. 没有比较 `recent_n`、`need_gated`、`task_scoped`。

## 当前结论

当前 `cctq gpt-5.4 + LightAgent` 可以稳定运行 AgentIF 短样本 baseline。

这说明:

- API 配置可用。
- tmux 运行方式可用。
- LightAgent baseline 调用链可用。
- AgentIF 数据读取和基本 code constraint 检查可用。

下一步:

1. 跑 100 条 baseline，覆盖更长 prompt 和更多 constraint 类型。
2. 接 AgentIF 官方 CSR/ISR scorer。
3. 实现 `ContextPolicy` 后，对同一批样本构造 stress session，再比较 baseline 和 task-scoped 方法。
