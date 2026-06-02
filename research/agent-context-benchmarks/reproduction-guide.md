# Reproduction Guide

检索日期: 2026-06-01

## 环境准备

建议目录:

```text
agent-context-isolation/
  third_party/
    MiroFlow/
    OAgents/
    tau2-bench/
    AgentIF/
    LongMemEval/
    OpenHands-benchmarks/
```

当前已下载:

```text
third_party/LightAgent
```

GitHub 网络注意:

```bash
ALL_PROXY=socks5h://127.0.0.1:7890 \
HTTPS_PROXY=socks5h://127.0.0.1:7890 \
HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone <repo>
```

本环境此前 `socks5://` 会本地解析 DNS，导致 `Could not resolve host: github.com`。使用 `socks5h://` 正常。

## Clone Commands

```bash
cd /22liushoulong/agent/agent-context-isolation
mkdir -p third_party

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/MiroMindAI/MiroFlow.git third_party/MiroFlow

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/OPPO-PersonalAI/OAgents.git third_party/OAgents

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/sierra-research/tau2-bench.git third_party/tau2-bench

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/THU-KEG/AgentIF.git third_party/AgentIF

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/xiaowu0162/LongMemEval.git third_party/LongMemEval

ALL_PROXY=socks5h://127.0.0.1:7890 HTTPS_PROXY=socks5h://127.0.0.1:7890 HTTP_PROXY=socks5h://127.0.0.1:7890 \
git clone https://github.com/OpenHands/benchmarks.git third_party/OpenHands-benchmarks
```

## Suggested Implementation Structure

新增本项目代码:

```text
agent-context-isolation/
  src/
    context_isolation/
      task_boundary.py
      context_store.py
      context_selector.py
      skill_tool_filter.py
      wrappers/
        miroflow_wrapper.py
        lightagent_wrapper.py
        tau_wrapper.py
      logging.py
  experiments/
    gaia/
    agentif/
    tau2/
    longmemeval/
```

## Wrapper API

建议统一接口:

```python
class ContextPolicy:
    def select(self, session_id, user_id, current_message, raw_history, tools=None):
        return SelectedContext(
            task_id=...,
            messages=...,
            memories=...,
            tool_candidates=...,
            metadata=...,
        )
```

统一输出日志:

```json
{
  "benchmark": "agentif",
  "case_id": "...",
  "policy": "task_scoped",
  "task_id": "...",
  "selected_turn_ids": [],
  "selected_memory_ids": [],
  "selected_tools": [],
  "input_tokens": 0,
  "output_tokens": 0,
  "tool_calls": [],
  "answer": "...",
  "score": {},
  "error": null
}
```

## Phase 0: Smoke Test

1. Clone MiroFlow。
2. 跑一个最小 GAIA-Val-Text 样例。
3. 确认搜索、Python、文件读取工具可用。
4. 记录 baseline 输出日志。

## Phase 1: Main Experiments

按顺序跑:

1. AgentIF small split。
2. LongMemEval-S small split。
3. tau2 telecom 20 task subset。
4. GAIA-Val-Text 103 tasks。

原因:

- AgentIF 和 LongMemEval 成本较低，更能快速验证方法是否有效。
- tau2 是交互式系统，成本和 debug 难度更高。
- GAIA 用于对齐主流 agent baseline。

## Phase 2: Full Experiments

1. AgentIF full 707。
2. LongMemEval-S/M。
3. tau2/tau3 full selected domains。
4. GAIA full validation。
5. AgentIF-OneDay full 104 tasks。

## Phase 3: Generalization

1. BrowseComp-200。
2. xBench-DeepSearch。
3. WebArena subset。
4. SWE-Bench Lite only if coding-agent claim is needed。

## Required Tables

### Main Result Table

```text
Benchmark | Policy | Score | Cost | Turns | Tool Errors | Memory Recall | Notes
```

### Ablation Table

```text
Policy | Boundary | Retrieval | Summary | Tool Filter | Score | Cost | Error Rate
```

### Benchmark Coverage Table

```text
Dataset | Domain | Tasks | Public Results Available | We Run | Metric | Priority
```

### Error Analysis Table

```text
Error Type | Full Session | Recent-N | Retrieval | Task-Scoped | Example Source
```

Error types:

- stale context used
- wrong task boundary
- missed relevant memory
- wrong memory recalled
- wrong tool/skill selected
- wrong tool argument
- instruction forgotten
- summary lost key fact
- clarification should have been asked

