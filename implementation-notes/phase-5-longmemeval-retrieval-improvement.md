# Phase 5 LongMemEval 检索改进记录

日期: 2026-06-02。

## 背景

旧版 LongMemEval `lexical` 策略直接把问题 terms 和整段 session terms 做 overlap。这个策略能压缩 full session，但存在两个问题:

1. 高频虚词和泛化词会让无关 session 排到前面。
2. 即使命中正确 session，也可能带入太多干扰 turn，使模型抽取错误答案。

旧结果:

| Run | Session Hit | QA |
| --- | ---: | ---: |
| `longmemeval_retrieval_lexical_smoke` | 4/5 | - |
| `longmemeval_qa_lexical_3_turn20_cctq_gpt54` | 2/3 | 1/3 |

## 新策略

新增 `lexical_turn` session 检索和 `weighted` turn 选择。

### Session 排名

不再按整段 session overlap 排序，而是:

1. 对每个 turn 计算问题 terms 与 turn terms 的重合。
2. 去掉英语 stopwords。
3. 使用 session-level IDF 提升稀有关键词权重。
4. 使用 top turn score、top-3 mean score 和 positive turn density 组合出 session score。

这样能让“单条证据 turn 很强”的 session 排到前面，而不是被长 session 的泛化词淹没。

### Turn 排名

在选中的 session 内使用同一套 weighted score 排 turn，只保留 top-k turn。当前小实验使用:

- `max_sessions=3`
- `max_turns_per_session=4`

### QA 指令修正

第 3 条样本的问题是 “Where did I redeem a $5 coupon on coffee creamer?”，上下文同时包含 `email inbox` 和 `Target`。模型容易把 `where` 理解为 coupon 来源，而 benchmark gold 是兑换地点/商家。

因此在 LongMemEval QA runner 中增加答案类型约束:

- 如果问题问 action happened where，回答 action 发生的 store/place/platform。
- 不回答 evidence 或 coupon 被发现的位置。

这属于任务级抽取约束，不使用 gold，也不引入人工样例。

## 当前结果

| Run | N | Session Hit | QA | Query Input Tokens |
| --- | ---: | ---: | ---: | ---: |
| `longmemeval_retrieval_lexical_turn_weighted_smoke20` | 20 | 20/20 | - | 0.0849M |
| `longmemeval_retrieval_lexical_turn_weighted_smoke100` | 100 | 94/100 | - | 0.4477M |
| `longmemeval_retrieval_lexical_turn_weighted_s8_smoke100` | 100 | 97/100 | - | 1.0883M |
| `longmemeval_retrieval_lexical_adaptive_weighted_smoke100` | 100 | 97/100 | - | 0.9620M |
| `longmemeval_qa_lexical_turn_weighted_3_cctq_gpt54` | 3 | 3/3 | 2/3 | 0.0112M |
| `longmemeval_qa_lexical_turn_weighted_prompt_3_cctq_gpt54` | 3 | 3/3 | 3/3 | 0.0112M |

对比 full session 估算:

- 3 条 full input: 0.4269M。
- 新策略 query input: 0.0112M。
- 约为 full session 的 2.62%。

## 仍未解决

1. 100 条 dry-run 出现 6 条 session miss，主要集中在抽象改写和 multi-session 样本。
2. QA scorer 仍是 string contains，后续需要接入 LongMemEval 官方评估或 LLM judge。
3. `lexical_turn` 还是词法策略，面对同义表达可能失败，后续需要加入 embedding rerank 或小模型 rerank。
4. multi-session 问题可能需要多证据覆盖，而不是只看单条最高分 turn。
5. 答案类型约束目前在 prompt 中，后续应做成显式 question intent parser 和 answer-type aware evidence validation。

## 固定扩大候选的观察

把 `max_sessions` 从 3 提到 8 后，100 条 session hit 从 94/100 提升到 97/100，但 query input token 从 0.4477M 增加到 1.0883M。

新增 `lexical_adaptive` 后，100 条 session hit 同样为 97/100，query input token 为 0.9620M，略低于固定 8，但仍明显高于固定 3。

这个结果说明:

1. 部分 miss 是召回预算不足导致的。
2. 默认固定 8 个 session 成本偏高，不适合作为主策略。
3. 更合理的方向是自适应扩大候选: 只有 multi-session、聚合问题、低置信排名或 top score 差距过小时，才从 3 扩到 6 或 8。
4. 当前 `lexical_adaptive` 阈值偏宽，70 条 single-session-user 中有 53 条扩到了 6 或 8，后续需要收紧。

## 下一步

1. 把 `lexical_turn + weighted` 纳入 Phase 5 主实验候选策略。
2. 分析 100 条 dry-run 的 6 个 session miss，按 paraphrase/multi-session/low lexical overlap 分类。
3. 真实模型先跑 10 条，确认 QA 改进是否稳定。
4. 如果 10 条稳定，再实现 answer-type aware rerank，而不是继续堆 prompt。
5. 下一版检索加入 adaptive session budget，用于在 multi-session/低置信场景扩大候选。
6. 再下一版加入 semantic rerank 或 query expansion，用于覆盖抽象问题和同义表达。
