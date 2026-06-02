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
2. 增加 tool-router stress session：
   - `same_tool_unrelated`
   - `irrelevant_tool_history`
   - `schema_distractor`
3. 比较：
   - `full_session`
   - `recent_n`
   - `task_scoped_tool_filter`

## 备注

BFCL 官方 leaderboard 当前说明 V3 引入 multi-turn categories，V4 继续加入 multi-step 和 memory/function composition 等更复杂类别。当前项目优先接 V3 multi-turn，因为它最直接对应 skill/tool router 污染。
