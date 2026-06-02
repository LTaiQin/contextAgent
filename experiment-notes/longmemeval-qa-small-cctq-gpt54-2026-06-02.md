# LongMemEval QA Small Run

日期：2026-06-02

模型：

```text
gpt-5.4 via https://www.cctq.ai/v1
```

本次目标：

验证 LongMemEval 从检索 smoke 进入真实模型 QA 后，`oracle evidence` 和简单 `lexical retrieval` 的实际差异。

## 运行命令

oracle，answer session 每条最多保留 4 turn：

```bash
python experiments/run_longmemeval_qa_policy.py \
  --split s_cleaned \
  --limit 3 \
  --mode oracle \
  --max-sessions 3 \
  --max-turns-per-session 4 \
  --max-tokens 120 \
  --out-dir experiments/runs/longmemeval_qa_oracle_3_cctq_gpt54
```

oracle，answer session 每条最多保留 20 turn：

```bash
python experiments/run_longmemeval_qa_policy.py \
  --split s_cleaned \
  --limit 3 \
  --mode oracle \
  --max-sessions 3 \
  --max-turns-per-session 20 \
  --max-tokens 120 \
  --out-dir experiments/runs/longmemeval_qa_oracle_3_fullsession_cctq_gpt54
```

lexical，每条最多保留 20 turn：

```bash
python experiments/run_longmemeval_qa_policy.py \
  --split s_cleaned \
  --limit 3 \
  --mode lexical \
  --max-sessions 3 \
  --max-turns-per-session 20 \
  --max-tokens 120 \
  --out-dir experiments/runs/longmemeval_qa_lexical_3_turn20_cctq_gpt54
```

## 结果

| mode | max turns | answer session hit | pass | full input tokens est | query input tokens est | avg compression ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| oracle | 4 | 3/3 | 1/3 | 426,921 | 4,579 | 0.0107 |
| oracle | 20 | 3/3 | 3/3 | 426,921 | 12,155 | 0.0285 |
| oracle | ranked turn mode, max turn 4 | 3/3 | 3/3 | 426,921 | 5,610 | 0.0132 |
| lexical | 20 | 2/3 | 1/3 | 426,921 | 34,081 | 0.0799 |

## 观察

1. `oracle + 4 turns` 虽然命中了 answer session，但经常截掉真正答案所在 turn，导致模型回答 `Not mentioned`。
2. `oracle + 20 turns` 在 3 条小样本上 3/3 正确，同时仍然把输入从约 0.427M tokens 压到约 0.012M tokens。
3. `lexical + 20 turns` 只有 1/3 正确：
   - 第 1 条没有命中 answer session。
   - 第 3 条命中了 answer session，但仍被其他检索 session 干扰，回答成 `in my email inbox`，gold 是 `Target`。
4. 这说明 LongMemEval 不能只靠简单词重叠检索；后续需要 evidence validator 或 hybrid retrieval。
5. `oracle + ranked turn mode` 在 3/3 正确的前提下，把输入进一步压到约 5.6K tokens，说明 session 内 turn ranking 比固定前 N 轮更适合作为默认 evidence 裁剪策略。

## 下一步

1. 增加 `oracle_session_full` 或动态 turn 裁剪策略：选中 answer/retrieved session 后不要固定前 N 轮，而是按 question-evidence relevance 选择局部窗口。
2. 增加 session 内 evidence ranking，避免 lexical 检索命中 session 后仍带入太多无关 turn。
3. Phase 5 小实验中，LongMemEval 至少比较：
   - full haystack
   - oracle evidence
   - lexical retrieval
   - improved evidence retrieval
   - oracle + ranked turn mode
