# Phase 0-3 补充记录

日期：2026-06-02

## 补充原因

前三阶段已经能继续推进，但为了让后续 benchmark 对比更可信，补齐了以下缺口：

1. Phase 2 缺少专门行为测试。
2. MATH 评分逻辑在不同 runner 中不统一。
3. same-session runner 的 trace summary 需要更稳定。
4. 三策略 same-session 对照需要先做无成本 dry-run 验证。

## 新增与修改文件

新增：

- `experiments/math_eval.py`
- `experiments/run_phase2_policy_tests.py`
- `implementation-notes/phase-0-3-supplement-2026-06-02.md`

修改：

- `experiments/run_math_same_session_policy.py`
- `experiments/run_math_baseline_10_tmux.py`
- `src/context_isolation/boundary.py`
- `src/context_isolation/tool_filter.py`

## Phase 2 补充

新增固定行为测试：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_phase2_policy_tests.py
```

覆盖场景：

1. 同领域但无关的新数学题：不检索历史。
2. 明确“上一题”：检索最近数学任务。
3. 模糊指代：不直接检索，标记 clarification。
4. 工具状态引用：回找最近含工具状态证据的任务。
5. 自足翻译任务：不检索历史。

测试结果：

```text
PASS same_domain_unrelated_math
PASS explicit_previous_math
PASS ambiguous_pronoun
PASS tool_state_reference
PASS global_profile_like_self_contained
```

输出：

```text
experiments/runs/phase2_policy_tests/results.json
```

## 修复的问题

原规则中，`tool_state` 引用会默认解析到最近任务。如果最近任务是数学题，而更早任务才是 calendar/reminder/order 相关任务，就会选错上下文。

修复后：

```text
Change the calendar reminder I booked earlier.
```

会回找最近含有 `calendar/reminder/booked/order` 等工具状态证据的任务，而不是盲目继承最新 task。

同时，普通 `task_local` 引用不再默认暴露所有工具。只有：

- `need_type == tool_state`
- 或当前消息显式提到 search/weather/file/database/tool/api

才暴露工具候选。

## MATH 评分补充

新增公共评分工具：

```text
experiments/math_eval.py
```

提供：

- `last_boxed`
- `extract_prediction`
- `normalize_answer`
- `score_prediction`

统一处理：

```text
\dfrac -> \frac
\tfrac -> \frac
\left / \right 移除
空格和简单 LaTeX spacing 移除
```

两个 runner 已同步：

- `experiments/run_math_same_session_policy.py`
- `experiments/run_math_baseline_10_tmux.py`

结果字段：

```json
{
  "correct_raw": false,
  "correct_normalized": true
}
```

旧 runner 为兼容历史记录，仍保留：

```json
{
  "correct_exact": true
}
```

但其含义已经等同 normalized correct。

## Phase 3 trace summary 补充

`run_math_same_session_policy.py` 每个样本新增：

```json
{
  "context_summary": {
    "policy": "...",
    "need_type": "...",
    "boundary": "...",
    "task_id": "...",
    "confidence": 0.0,
    "selected_turn_ids": [],
    "selected_memory_ids": [],
    "selected_tools": [],
    "suppressed_tools": [],
    "raw_history_count": 0,
    "selected_history_count": 0,
    "input_tokens_est": 0,
    "reason": "..."
  }
}
```

后续不同 benchmark adapter 应尽量复用这个字段结构。

## 三策略 dry-run 对照

命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_math_same_session_policy.py \
  --policy task_scoped \
  --limit 3 \
  --categories algebra \
  --dry-run \
  --out-dir experiments/runs/math_same_session_task_scoped_dryrun_phase补充

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_math_same_session_policy.py \
  --policy full_session \
  --limit 3 \
  --categories algebra \
  --dry-run \
  --out-dir experiments/runs/math_same_session_full_session_dryrun_phase补充

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_math_same_session_policy.py \
  --policy recent_n \
  --limit 3 \
  --categories algebra \
  --dry-run \
  --out-dir experiments/runs/math_same_session_recent_n_dryrun_phase补充
```

结果摘要：

| policy | task 1 selected | task 2 selected | task 3 selected | token est trend |
| --- | ---: | ---: | ---: | --- |
| `task_scoped` | 0 | 0 | 0 | 92 -> 91 -> 97 |
| `full_session` | 0 | 2 | 4 | 92 -> 190 -> 295 |
| `recent_n` | 0 | 2 | 4 | 92 -> 190 -> 295 |

解释：

- `task_scoped` 判断这三道题都是自足新任务，因此不带旧历史。
- `full_session` 会持续累积前面题目。
- `recent_n=4` 在三题内和 full session 等价，样本更多时会截断到最近 4 turns。

## 当前状态判断

Phase 0：完成。

Phase 1：完成，已有可替换 policy 层。

Phase 2：规则版完成，并补了固定行为测试。

Phase 3：LightAgent 接入和 MATH same-session runner 完成，小样本真实调用已跑通，三策略 dry-run 对照已验证。

## 下一步建议

1. 用同一批 5 到 10 道 MATH 样本真实跑 `full_session/recent_n/task_scoped`，形成第一组策略对比。
2. 把 same-session policy runner 接到 AgentIF。
3. 构造 mixed single-session adapter：MATH + AgentIF + LongMemEval/MultiChallenge 的公开任务混合。
4. 再决定是否引入 embedding/SQLite/LLM judge。
