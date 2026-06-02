# Phase 4 BFCL Adapter Started

日期：2026-06-02

## 目标

开始接入 BFCL，用于后续验证 skill/tool router 污染问题。

## 已完成

新增：

```text
experiments/benchmark_adapters/bfcl_adapter.py
experiments/run_bfcl_adapter_smoke.py
```

已支持：

1. 加载本地 BFCL JSONL 数据。
2. 展开 BFCL `question` 字段中的多轮消息结构。
3. 将 BFCL `function` schema 转为 OpenAI-style tool schema：

```json
{
  "type": "function",
  "function": {
    "name": "...",
    "description": "...",
    "parameters": {}
  }
}
```

4. 构造统一 `TaskUnit`：

```text
source_benchmark = BFCL
domain = tool_calling
task_type = function_calling
scorer = bfcl_official_pending
```

## 已验证

命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_bfcl_adapter_smoke.py
```

结果：

```text
BFCL smoke 1/3 task=bfcl:simple_0 tools=1 first_tool=calculate_triangle_area
BFCL smoke 2/3 task=bfcl:simple_1 tools=1 first_tool=math.factorial
BFCL smoke 3/3 task=bfcl:simple_2 tools=1 first_tool=math.hypot
```

输出：

```text
experiments/runs/bfcl_adapter_smoke/results.json
```

## 2026-06-02 更新

已按用户建议使用 `7890` 代理重新下载 BFCL 数据，成功。

已下载到本地但不纳入 git：

```text
data/bfcl/BFCL_v3_simple.json
data/bfcl/BFCL_v3_multi_turn_base.json
data/bfcl/possible_answer/BFCL_v3_simple.json
data/bfcl/possible_answer/BFCL_v3_multi_turn_base.json
data/bfcl/multi_turn_func_doc/*.json
```

`.gitignore` 已排除 `data/`，不会提交这些数据文件。

已更新 `BFCLAdapter`：

1. `simple` 和 `multi_turn_base` 都可加载。
2. `possible_answer` 可合并为 `TaskUnit.gold`。
3. `multi_turn_func_doc` 可按样本 `path` 解析工具函数。
4. BFCL function schema 可转 OpenAI-style tool schema。

最新 smoke：

```text
BFCL smoke category=simple 1/3 task=bfcl:simple_0 tools=1 first_tool=calculate_triangle_area gold_present=True
BFCL smoke category=simple 2/3 task=bfcl:simple_1 tools=1 first_tool=math.factorial gold_present=True
BFCL smoke category=simple 3/3 task=bfcl:simple_2 tools=1 first_tool=math.hypot gold_present=True
BFCL smoke category=multi_turn_base 1/3 task=bfcl:multi_turn_base_0 tools=6 first_tool=find gold_present=True
BFCL smoke category=multi_turn_base 2/3 task=bfcl:multi_turn_base_1 tools=5 first_tool=ls gold_present=True
BFCL smoke category=multi_turn_base 3/3 task=bfcl:multi_turn_base_2 tools=7 first_tool=touch gold_present=True
```

## 下一步

1. 接入 BFCL 官方 scorer 或复用官方 AST/executable evaluator。
2. 将 tool-router stress 从 dry-run 扩展到真实模型输出：
   - `same_tool_unrelated`
   - `irrelevant_tool_history`
   - `schema_distractor`
3. 比较：
   - `full_session`
   - `recent_n`
   - `task_scoped_tool_filter`

## 备注

BFCL 官方 leaderboard 当前说明 V3 引入 multi-turn categories，V4 继续加入 multi-step 和 memory/function composition 等更复杂类别。当前项目优先接 V3 multi-turn，因为它最直接对应 skill/tool router 污染。

## 2026-06-02 第二次更新

本次补齐了 Phase 4 中 BFCL 的本地 scorer 和 tool-router stress dry-run。

新增文件：

```text
experiments/benchmark_adapters/bfcl_scoring.py
experiments/run_bfcl_scorer_smoke.py
experiments/run_bfcl_tool_stress_policy.py
```

修改：

```text
experiments/benchmark_adapters/bfcl_adapter.py
experiments/benchmark_adapters/scoring.py
src/context_isolation/gates.py
```

### BFCL 官方 scorer

当前 BFCL scorer 已接入官方 `bfcl_eval` 包的 evaluator：

1. `simple` 使用官方 `ast_checker`。
2. `multi_turn_base` 使用官方 `multi_turn_checker`。
3. 本地 `bfcl_local_ast_approx` 保留作为 fallback / 调试参考，但不再作为主结果。

冒烟测试：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_bfcl_scorer_smoke.py
```

结果：

```text
simple 3/3 passed
multi_turn_base 3/3 passed
```

注意：

1. BFCL 官方 checker 对模型名、函数名和 multi-turn 结构都比较严格。
2. 当前 smoke 使用 `gpt-5.2-2025-12-11` 作为官方 BFCL model key 的对齐参考。
3. multi-turn 样本需要传入 `initial_config` 和 `involved_classes`，否则官方 evaluator 无法执行。

### BFCL tool-router stress dry-run

命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_bfcl_tool_stress_policy.py \
  --category multi_turn_base \
  --policy task_scoped_tool_filter \
  --limit 3 \
  --out-dir experiments/runs/bfcl_tool_stress_task_scoped_dryrun_v4
```

结果：

```text
context_ok: 3/3
forbidden_inclusion: 0
unnecessary_context: 0
input_tokens_est_total: 588
```

这说明 `task_scoped_tool_filter` 在 BFCL 多轮工具样本串进同一个 session 时，不会把旧任务历史带进新任务。

注意：当前 `wrong_tool_exposed=True` 仍会被记录，但不作为 hard fail，因为 BFCL 原始样本本身可能携带同一任务内的 distractor tool。当前 hard fail 只判断：

1. 是否错误带入旧任务上下文。
2. 是否过度过滤导致 gold tool 不可用。

### NeedGate 修正

BFCL 文件名中可能出现 `previous_report.pdf` 这类字符串。旧规则会把 `previous` 误判成“引用聊天历史”。因此现在 `new independent task` / `independent task` 这类显式自足标记优先于 history-reference 词。

回归命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_phase2_policy_tests.py
```

结果：

```text
5/5 passed
```

## LongMemEval Adapter 补充

新增：

```text
experiments/benchmark_adapters/longmemeval_adapter.py
experiments/run_longmemeval_adapter_smoke.py
```

已支持：

1. 加载 `data/longmemeval/longmemeval_s_cleaned.json`。
2. 加载 `data/longmemeval/longmemeval_oracle.json`。
3. 将 LongMemEval 样本转为统一 `TaskUnit`。
4. 提供临时 string-contains scorer：`longmemeval_string_contains`。

冒烟命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_longmemeval_adapter_smoke.py
```

结果：

```text
3/3 passed
query_chars: 491K 到 509K
```

重要结论：

LongMemEval 单条样本如果直接拼完整 haystack，输入会接近 50 万字符。这正好说明它适合作为长历史检索/隔离压力测试，但正式实验不能直接把完整 haystack 全塞给模型。下一步需要接 memory store 和 evidence/oracle retrieval，只把相关 session 或片段注入上下文。

## LongMemEval Retrieval Smoke

新增：

```text
experiments/run_longmemeval_retrieval_smoke.py
```

目标：

验证 LongMemEval 不应采用 full haystack 直塞模型，而应先做证据检索/裁剪。

支持两种无模型检索模式：

1. `oracle`: 使用 benchmark 自带的 `answer_session_ids` 选择证据 session。这个模式用于方法上界和 token 成本上界估算。
2. `lexical`: 用当前 question 和每个 history session 的词重叠排序，选择 top-k。这个模式是不用 embedding、不调用模型的低成本 baseline。

命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_longmemeval_retrieval_smoke.py \
  --split s_cleaned \
  --limit 5 \
  --mode oracle \
  --out-dir experiments/runs/longmemeval_retrieval_oracle_smoke

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_longmemeval_retrieval_smoke.py \
  --split s_cleaned \
  --limit 5 \
  --mode lexical \
  --out-dir experiments/runs/longmemeval_retrieval_lexical_smoke
```

结果：

| mode | answer session hit | full input tokens est | compact input tokens est | avg compression ratio |
| --- | --- | ---: | ---: | ---: |
| oracle | 5/5 | 713,163 | 6,968 | 0.0098 |
| lexical | 4/5 | 713,163 | 20,131 | 0.0282 |

结论：

1. oracle evidence 可以把输入从约 0.713M tokens 压到约 0.007M tokens。
2. 简单 lexical retrieval 已经能大幅降成本，但 5 条中漏掉 1 条 answer session。
3. 后续正式实验需要比较：
   - full haystack
   - oracle evidence
   - lexical retrieval
   - 后续 hybrid / embedding retrieval
4. 这进一步支持本项目假设：长 session agent 不能每条消息无差别塞历史，也不能只靠最近 N 轮。
