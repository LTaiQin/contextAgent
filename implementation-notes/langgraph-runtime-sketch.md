# LangGraph 备选 Runtime 草图

日期: 2026-06-02。

## 目的

LangGraph 不作为当前主实现 baseline。它是 LightAgent 不适合时的备选方案，用来构建一个更可控、更论文化的固定 agent runtime。

## 适用条件

切换到 LangGraph 的条件:

1. LightAgent 默认工具/skill/memory 注入难以完全控制。
2. benchmark adapter 需要严格复现同一状态流。
3. 需要把 task boundary、context selection、tool routing、memory update 都显式表示成图节点。
4. 需要更容易做 oracle boundary 和 ablation。

不建议一开始切换:

- LangGraph 是 framework，不是固定 agent baseline。
- 需要自己写 agent runtime 和工具执行 loop。
- 早期会增加工程量。

## 最小状态定义

```python
from typing import TypedDict, Any


class AgentState(TypedDict):
    session_id: str
    user_id: str
    current_message: str
    raw_history: list[dict]
    available_tools: list[dict]
    context_decision: dict
    selected_messages: list[dict]
    selected_memories: list[dict]
    selected_tools: list[dict]
    llm_response: str
    tool_calls: list[dict]
    tool_results: list[dict]
    trace: dict[str, Any]
```

## 图结构

```text
intake
  -> need_gate
  -> boundary_detector
  -> context_selector
  -> evidence_validator
  -> tool_filter
  -> prompt_assembler
  -> llm_agent
  -> tool_executor
  -> memory_update
  -> export_trace
```

## 节点职责

### intake

输入 benchmark sample 或聊天消息，标准化为 `AgentState`。

### need_gate

判断当前消息是否自足。

输出:

```text
self_sufficient
need_type
confidence
```

### boundary_detector

判断当前消息是:

```text
new_task
continue_task
related_task
ambiguous
```

### context_selector

按策略选择上下文:

- `full_session`
- `recent_n`
- `retrieval_only`
- `need_gated`
- `task_scoped`
- `oracle_boundary`

### evidence_validator

检查召回历史是否真的支持当前任务。

### tool_filter

对 `available_tools` 做 task-local 过滤。

### prompt_assembler

把 system prompt、selected messages、selected memories 和当前消息组装为模型输入。

### llm_agent

调用 OpenAI-compatible chat/completions 或 responses。

### tool_executor

执行模型返回的 tool call。

### memory_update

根据任务边界更新:

- task summary。
- task-local memory。
- global profile memory。
- tool state。

### export_trace

输出统一 JSONL:

```text
sample_id
policy
context_decision
selected_context
tool_candidates
tool_calls
token_usage
official_score
project_metrics
```

## 与 LightAgent 的关系

LightAgent wrapper 可以先实现以下逻辑:

```text
ContextPolicy.select(...)
  -> LightAgent.run(...)
```

LangGraph 则是把 LightAgent 内部隐式流程显式拆成节点:

```text
ContextPolicy.select(...)
  -> prompt assembler
  -> model call
  -> tool loop
  -> memory update
```

如果 LightAgent 后续不能干净屏蔽默认工具或 memory 注入，LangGraph 是替代路线。

## Benchmark 接入方式

每个 benchmark adapter 不直接依赖 LightAgent 或 LangGraph，而是依赖统一 runner:

```python
class AgentRunner:
    def run_sample(self, sample, policy_name: str) -> dict:
        ...
```

这样后续可以替换:

```text
LightAgentRunner
LangGraphRunner
MiroFlowOptionalRunner
```

## Phase 0 结论

当前不切换到 LangGraph。

推荐:

1. Phase 1/2 先实现独立 `ContextPolicy`。
2. Phase 3 先接 LightAgent wrapper。
3. 如果工具暴露、memory 注入或 trace 控制出现结构性问题，再实现 LangGraph runner。
