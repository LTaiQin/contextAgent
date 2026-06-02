# Phase 4: Benchmark Adapters

更新时间: 2026-06-02。

当前实施状态: Phase 4 已完成第一轮可运行 adapter 骨架和本地 smoke，尚未完成所有官方 evaluator 集成。

## 目标

为 LightAgent 主线实现公开 benchmark adapter。adapter 必须复用官方数据和官方评分器，额外增加统一 session 构造、上下文策略注入、trace 日志和成本统计。

MiroFlow/HLE/GAIA 不再是本 phase 的主线，只保留 optional smoke。

## Adapter 统一接口

```python
class BenchmarkAdapter:
    name: str

    def load_samples(self, split: str, max_samples: int | None = None):
        ...

    def build_session(self, sample, stress_type: str | None = None):
        ...

    def run_agent(self, agent, session, context_policy):
        ...

    def score(self, sample, prediction, trace):
        ...

    def export_result(self, sample, prediction, trace, score):
        ...
```

每条结果统一写 JSONL:

```json
{
  "benchmark": "bfcl",
  "sample_id": "...",
  "policy": "task_scoped_tool_filter",
  "model": "...",
  "stress_type": "same-tool-unrelated",
  "official_score": {},
  "project_metrics": {},
  "token_usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_tokens": 0
  },
  "trace_path": "..."
}
```

## 优先级

| 优先级 | Adapter | 先做原因 |
| --- | --- | --- |
| P0 | AgentIF | 最低成本验证旧 instruction 污染 |
| P0 | BFCL multi-turn | 最直接验证 skill/tool router |
| P0 | LongMemEval / LoCoMo | 最直接验证记忆检索门控 |
| P0 | MultiChallenge | 贴近真实聊天多轮上下文漂移 |
| P1 | tau-bench / tau2-bench | 端到端工具 agent 证明 |
| P1 | ToolSandbox | 状态化工具污染证明 |
| P1 | STATE-Bench | 企业 workflow/memory/skills 小样本 |
| P2 | GAIA text-only / MiroFlow HLE smoke | 只做参考 |

## AgentIF Adapter

来源:

- https://agentif.github.io/
- https://github.com/THU-KEG/AgentIF
- https://huggingface.co/datasets/THU-KEG/AgentIF

指标:

- CSR。
- ISR。
- constraint type score。

实现步骤:

1. 下载/加载 AgentIF 数据。
2. 跑通官方 scorer，先不用 LightAgent。
3. 写 `AgentIFAdapter.load_samples()`。
4. 写 `build_session()`:
   - `none`: 原始 instruction。
   - `different-domain`: 前面插入完全不同领域 instruction。
   - `same-domain-unrelated`: 前面插入同类但无关 instruction。
   - `old-constraint-conflict`: 前一任务要求某种格式，当前任务要求另一种格式。
5. 接入 LightAgent wrapper。
6. 记录 selected context、继承了哪些历史约束、输出是否违反当前约束。

首轮 smoke:

- 20 条。
- 策略: `full_session`、`recent_n`、`need_gated`、`task_scoped`。

正式小实验:

- 100 到 300 条。
- 增加 `oracle_boundary`。

验收:

- 输出官方 CSR/ISR。
- 能统计旧约束污染率。

## BFCL Multi-Turn Adapter

来源:

- https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard
- https://gorilla.cs.berkeley.edu/leaderboard.html

指标:

- overall accuracy。
- multi-turn accuracy。
- AST / executable accuracy。
- wrong tool rate。
- wrong argument rate。
- irrelevant tool call rate。

实现步骤:

1. 拉取 BFCL 数据和 evaluator。
2. 先跑官方单条样例 scorer。
3. 写 tool schema 转换层，把 BFCL function schema 转成 LightAgent tool/skill schema。
4. 写 `build_session()`:
   - `none`: 原始多轮工具任务。
   - `same-tool-unrelated`: 前面插入同工具不同目标的调用历史。
   - `irrelevant-tool-history`: 前面插入当前不应调用的工具历史。
   - `schema-distractor`: 可用工具列表中放入相似但不正确的工具。
5. 让 `task_scoped_tool_filter` 只暴露当前 task 相关工具候选。
6. 记录模型输出 tool name、arguments、是否调用工具、调用轮次。

首轮 smoke:

- multi-turn 20 条。
- relevance/irrelevance 20 条。

正式小实验:

- multi-turn 100 到 300 条。
- relevance/irrelevance 100 到 300 条。

验收:

- 能复用官方 BFCL scorer。
- 能输出 wrong tool、wrong argument、unnecessary tool call。

## LongMemEval / LoCoMo Adapter

来源:

- LongMemEval: https://github.com/xiaowu0162/LongMemEval
- LongMemEval paper: https://arxiv.org/abs/2410.10813
- memory-benchmarks: https://github.com/mem0ai/memory-benchmarks

指标:

- QA accuracy。
- recall@k。
- category accuracy。
- update correctness。
- abstention accuracy。

实现步骤:

1. 优先用 `memory-benchmarks` 跑通 LongMemEval/LoCoMo 小样本。
2. 写 memory store 统一接口:
   - raw full history。
   - embedding retrieval。
   - task-scoped retrieval。
   - oracle evidence。
3. 写 `build_session()`:
   - `explicit-reference`: 当前问题明确依赖过去事实。
   - `self-contained`: 当前问题不需要历史。
   - `updated-fact`: 新事实覆盖旧事实。
   - `missing-info`: 历史中没有答案，应拒答。
   - `same-domain-unrelated`: 同领域但无关历史。
4. 接入 need gate:
   - 判断当前问题是否自足。
   - 自足时不检索。
   - 不自足时只在相关 task/memory cluster 检索。
5. 记录 retrieved memories、evidence ids、是否使用了错误记忆。

首轮 smoke:

- LongMemEval 20。
- LoCoMo 20。

正式小实验:

- LongMemEval/LoCoMo 各 100 到 300。

验收:

- 能输出 QA accuracy 和 recall@k。
- 能统计 unnecessary retrieval、missed memory、wrong memory。

## MultiChallenge Adapter

来源:

- https://arxiv.org/abs/2501.17399

指标:

- APR。
- ARS。

实现步骤:

1. 获取公开数据和 evaluator；如果官方 evaluator 需要 judge LLM，先做 20 条低成本 judge smoke。
2. 写 `build_session()`:
   - 原始 multi-turn conversation。
   - 前置一个无关对话任务。
   - 插入同领域无关问答。
   - 插入显式版本编辑历史。
3. 针对每轮消息调用 context policy。
4. 记录 policy 是否选择了必要前文，是否带入无关前文。

首轮 smoke:

- 20 条。

正式小实验:

- 50 到 100 条。

验收:

- 能输出 APR/ARS。
- 能对错误做 `missed_context` 和 `context_contamination` 分类。

## tau-bench / tau2 Adapter

来源:

- tau-bench: https://github.com/sierra-research/tau-bench
- tau-bench paper: https://arxiv.org/abs/2406.12045
- tau2-bench paper: https://arxiv.org/abs/2506.07982
- tau2-bench code: https://github.com/sierra-research/tau2-bench

指标:

- Pass^1。
- Pass^k。
- final state correctness。
- action count。
- wrong tool/action rate。

实现步骤:

1. 先确认 tau2 代码和任务数据能本地跑通。
2. 选择一个 domain，不全量跑。
3. 把 LightAgent tool calling 适配到 tau2 domain tools。
4. 写跨任务 session stress:
   - 上一任务同 domain 但不同用户目标。
   - 上一任务调用过同一工具但参数不同。
   - 当前任务显式引用历史或完全不引用历史。
5. 先只比较 `full_session`、`recent_n`、`task_scoped_tool_filter`。

首轮 smoke:

- 10 到 20 个任务。
- 每个策略 1 次。

正式小实验:

- 30 到 100 个任务。
- 关键策略 3 次重复，计算 Pass^k。

验收:

- 能输出 final state correctness。
- 能统计 stale tool state 和 wrong action。

## ToolSandbox Adapter

来源:

- https://github.com/apple/ToolSandbox

指标:

- milestone DAG score。
- snapshot similarity。
- tool trace similarity。
- guardrail similarity。

实现步骤:

1. 本地跑通 ToolSandbox 官方最小示例。
2. 写 LightAgent tool schema 适配层。
3. 构造 same-tool-unrelated 历史轨迹。
4. 记录工具调用 trace、state snapshot、guardrail 违规。

首轮 smoke:

- 10 到 20 个任务。

正式小实验:

- 30 到 100 个任务。

验收:

- 能输出官方四类分数。
- 能定位 stale tool state。

## STATE-Bench Adapter

来源:

- https://github.com/microsoft/STATE-Bench

指标:

- pass@1。
- pass^5。
- UX Score。
- Cost Per Task。

实现步骤:

1. 先只安装和运行一个 domain 的最小样例。
2. 不追求复现 leaderboard。
3. 只接 `full_session`、`recent_n`、`task_scoped_tool_filter`。
4. 记录 memory/skill 相关失败。

首轮 smoke:

- 10 个任务。

验收:

- 能生成 pass@1 和成本。
- 若接入成本过高，停止在 P1 optional，不阻塞主线。

## Optional: GAIA / MiroFlow

用途:

- 只做小样本 reference。
- 不用于证明主要创新。
- 不要求完整复现 MiroFlow 官方工具链。

保留原因:

- 论文相关工作中可引用强 agent benchmark。
- 可说明为什么本文选择更贴近上下文隔离的 benchmark。

## 输出目录

建议结构:

```text
experiments/
  benchmark_adapters/
  runs/
    agentif_smoke_YYYYMMDD/
    bfcl_smoke_YYYYMMDD/
    longmemeval_smoke_YYYYMMDD/
  reports/
    benchmark_summary.md
    error_analysis.md
```

## Phase 4 完成标准

必须完成:

1. AgentIF adapter 可运行并可评分。
2. BFCL multi-turn adapter 可运行并可评分。
3. LongMemEval 或 LoCoMo adapter 可运行并可评分。
4. 所有 adapter 都输出统一 JSONL。
5. 每条 trace 都保存 context policy 决策。
6. token 统计区分 input、output、cache，报告单位可转 M。

可选完成:

1. MultiChallenge adapter。
2. tau2 adapter。
3. ToolSandbox adapter。
4. STATE-Bench smoke。

## 当前进度记录

日期: 2026-06-02。

已完成并通过本地验证：

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 统一 `TaskUnit` / `BenchmarkResult` | 已完成 | MATH、AgentIF、BFCL、LongMemEval adapter 共用 |
| MATH same-session runner | 已完成 | 可比较 `full_session`、`recent_n`、`task_scoped` |
| AgentIF same-session runner | 已完成 | 支持 code constraint scorer，小样本已跑通 |
| Mixed single-session runner | 已完成 | 可把公开 benchmark task 混到同一 session，统计旧上下文污染 |
| BFCL adapter | 已完成第一版 | 支持 `simple` 和 `multi_turn_base` 数据加载、gold 合并、tool schema 转换 |
| BFCL local scorer | 已完成第一版 | `bfcl_local_ast_approx`，用于 smoke 和压力测试，不等价于官方 evaluator |
| BFCL tool-router stress dry-run | 已完成第一版 | 可比较旧工具/旧上下文污染，不调用模型 |
| LongMemEval adapter | 已完成第一版 | 可加载 cleaned/oracle 数据并构造 `TaskUnit` |
| LongMemEval 临时 scorer | 已完成第一版 | `longmemeval_string_contains`，只用于冒烟测试 |
| LongMemEval retrieval smoke | 已完成第一版 | 支持 oracle evidence 和 lexical retrieval，不调用模型 |

本次验证命令：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_longmemeval_adapter_smoke.py

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_bfcl_scorer_smoke.py

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_bfcl_tool_stress_policy.py \
  --category multi_turn_base \
  --policy task_scoped_tool_filter \
  --limit 3 \
  --out-dir experiments/runs/bfcl_tool_stress_task_scoped_dryrun_v4

conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_phase2_policy_tests.py

python -m py_compile experiments/benchmark_adapters/*.py \
  src/context_isolation/*.py \
  experiments/run_*.py

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

本次验证结果：

```text
LongMemEval adapter smoke: 3/3 passed
BFCL scorer smoke: simple 3/3 passed, multi_turn_base 3/3 passed
BFCL task_scoped_tool_filter dry-run: context_ok 3/3, forbidden_inclusion 0, input_tokens_est_total 588
Phase 2 policy tests: 5/5 passed
py_compile: passed
LongMemEval oracle retrieval smoke: answer_session_hit 5/5, 713K -> 7K input tokens est
LongMemEval lexical retrieval smoke: answer_session_hit 4/5, 713K -> 20K input tokens est
```

重要限制：

1. BFCL 当前 scorer 是本地 AST 近似评分器，不能作为论文中的 BFCL 官方分数。
2. LongMemEval 当前 string-contains scorer 只能做 adapter smoke，正式实验需要官方/LLM judge 或 memory-benchmarks evaluator。
3. LongMemEval cleaned 样本完整 haystack 输入接近 50 万字符，当前已补 oracle/lexical retrieval smoke，但正式实验还需要更强 retrieval 和真实模型 QA。
4. 当前 BFCL tool-router stress 是 dry-run，只验证 context policy 和 tool exposure，不验证模型真实 tool call 能力。

下一步进入 Phase 5 前，Phase 4 还应补：

1. 将 BFCL 官方 evaluator 接进 `score_task()`，至少跑 10 到 20 条真实模型 tool-call 小样本。
2. 为 LongMemEval 增加真实模型 QA runner，比较 full haystack、oracle evidence、lexical retrieval 和后续 hybrid retrieval。
3. 选择是否优先接 MultiChallenge 或 tau2；如果预算紧，先不接 P1/P2。
