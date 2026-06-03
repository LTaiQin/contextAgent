# Phase 5.1: LongMemEval 检索预算调优

日期: 2026-06-02。

## 目标

在不使用 oracle session label 的前提下，提高 LongMemEval 检索命中率，同时控制输入 token。

当前已知结果:

| 策略 | N | Session Hit | Query Input Tokens | Compression |
| --- | ---: | ---: | ---: | ---: |
| `lexical_turn + weighted + max_sessions=3` | 100 | 94/100 | 0.4477M | 0.0316 |
| `lexical_turn + weighted + max_sessions=8` | 100 | 97/100 | 1.0883M | 0.0767 |
| `lexical_adaptive + weighted` | 100 | 97/100 | 0.9620M | 0.0679 |

阶段目标:

1. 保持或接近 97/100 session hit。
2. 把 query input token 降到 0.75M 以下。
3. 保留失败样本分类，避免只调前 100 条过拟合。

## 当前问题

`lexical_adaptive` 阈值偏宽，导致 single-session-user 样本也大量扩展:

- 70 条 single-session-user 中，53 条扩到 6 或 8 个 session。
- 30 条 multi-session 全部扩到 8 个 session，这是合理但成本较高。

主要剩余 miss:

1. negative/unanswerable: 正确 session 排名很靠后，纯词法难以召回。
2. multi-session aggregation: 需要多个证据 session，且答案常是计数/汇总。
3. paraphrase/low-overlap: 正确 session 排在第 4 到 5，适合低成本扩展到 6。

## 实施步骤

### Step 1: 阈值搜索脚本

新增一个 dry-run sweep 脚本:

- 输入 LongMemEval split 和 limit。
- 枚举 adaptive 参数:
  - single-session 扩展到 6 的 `next_ratio` 阈值。
  - single-session 扩展到 6 的 `boundary_gap` 阈值。
  - multi-session 固定扩到 6 或 8。
- 输出:
  - session hit。
  - token 估算。
  - 平均 compression。
  - budget 分布。

### Step 2: 选择候选策略

优先选择:

1. hit >= 96/100 且 token < 0.75M。
2. 如果没有，则选择 hit/token 性价比最高的 Pareto 点。

### Step 3: 写入 adapter

把选出的参数写回 `LongMemEvalAdapter.adaptive_session_budget`。

### Step 4: 真实模型小实验

只跑 10 条，使用 CCTQ `gpt-5.4`:

- `lexical_turn + weighted + prompt`
- `lexical_adaptive + weighted + prompt`

对比:

- QA score。
- answer_session_hit。
- query input tokens。

### Step 5: 决策

如果 adaptive 比 lexical_turn 明显提高 QA，保留为 LongMemEval 主策略。

如果 adaptive 只提高 session hit 但 QA 不提升，下一步优先做:

- answer-type aware evidence validation。
- semantic rerank/query expansion。

## 停止条件

阶段 5.1 完成条件:

1. sweep 脚本可复现运行。
2. 选出一个默认 adaptive 参数。
3. 100 条 dry-run 表格写入 experiment notes。
4. 至少完成一组 10 条真实模型小实验，或明确因成本暂停。
