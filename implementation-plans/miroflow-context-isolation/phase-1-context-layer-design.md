# Phase 1: 上下文隔离层设计

## 目标

设计一个独立的 `context_isolation` Python package，作为轻量 agent runtime 的前置层。它负责判断当前消息是否需要历史、属于哪个任务、可见哪些上下文、可用哪些工具。

第一接入目标是 LightAgent；备选接入目标是 LangGraph。MiroFlow 只作为 optional integration，不再是 Phase 1 的默认约束。

当前状态:

```text
Phase 1 最小实现已完成。
完成记录: /22liushoulong/agent/agent-context-isolation/implementation-notes/phase-1-completion.md
混合单 session 验证协议: /22liushoulong/agent/agent-context-isolation/implementation-notes/mixed-single-session-protocol.md
```

## 设计原则

1. 不把聊天 session 直接等同于推理上下文。
2. 默认不检索历史，除非当前消息需要历史。
3. 同领域不等于同任务。
4. 相似不等于相关。
5. 任何进入 prompt 的旧上下文都要有证据理由。
6. 所有决策都要写入 trace。

## 模块结构

```text
src/context_isolation/
  __init__.py
  schema.py
  policy.py
  trace.py
  wrappers/
    lightagent.py
```

最小实现已经包含:

- `schema.py`
- `policy.py`
- `trace.py`
- `wrappers/lightagent.py`

后续 Phase 2/4 再补:

- `store.py`
- `gates.py`
- `boundary.py`
- `retrieval.py`
- `evidence.py`
- `tool_filter.py`
- `assembler.py`
- `wrappers/langgraph.py`
- `wrappers/miroflow_optional.py`

## 核心数据结构

### ChatTurn

```python
@dataclass
class ChatTurn:
    turn_id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    task_id: str | None = None
    metadata: dict = field(default_factory=dict)
```

### TaskContext

```python
@dataclass
class TaskContext:
    task_id: str
    session_id: str
    status: Literal["active", "suspended", "completed", "archived"]
    title: str
    domain: str | None
    summary: str
    turn_ids: list[str]
    local_facts: dict
    tool_state: dict
    artifacts: dict
    skills_used: list[str]
    created_at: str
    updated_at: str
```

### ContextDecision

```python
@dataclass
class ContextDecision:
    self_sufficient: bool
    need_type: Literal[
        "no_context",
        "task_local",
        "related_summary",
        "global_profile",
        "project_memory",
        "tool_state",
        "clarification",
    ]
    boundary: Literal["new_task", "continue_task", "related_task", "ambiguous"]
    task_id: str | None
    confidence: float
    selected_turn_ids: list[str]
    selected_memory_ids: list[str]
    selected_tools: list[str]
    suppressed_tools: list[str]
    reason: str
```

### SelectedContext

```python
@dataclass
class SelectedContext:
    system_addendum: str
    messages: list[dict]
    memories: list[dict]
    tools: list[dict]
    trace: dict
```

## 存储设计

最初用本地 JSONL / SQLite:

```text
data/context_store/
  turns.jsonl
  tasks.jsonl
  memories.jsonl
  tool_state.jsonl
  traces.jsonl
```

后续如果需要可切到:

- SQLite + FTS
- LanceDB / Chroma
- Postgres + pgvector

## Context Policy 接口

```python
class ContextPolicy:
    def select(
        self,
        session_id: str,
        user_id: str,
        current_message: str,
        raw_history: list[dict],
        available_tools: list[dict] | None = None,
    ) -> SelectedContext:
        ...
```

## 策略插件

必须实现:

- `FullSessionPolicy`
- `RecentNPolicy`
- `RetrievalOnlyPolicy`
- `NeedGatedPolicy`
- `TaskScopedPolicy`
- `TaskScopedToolFilterPolicy`
- `OracleBoundaryPolicy`

## Trace 字段

每次决策记录:

```json
{
  "session_id": "...",
  "turn_id": "...",
  "policy": "task_scoped",
  "self_sufficient": true,
  "need_type": "no_context",
  "boundary": "new_task",
  "task_id": "...",
  "selected_turn_ids": [],
  "selected_memory_ids": [],
  "selected_tools": [],
  "suppressed_tools": [],
  "input_tokens_est": 0,
  "decision_latency_ms": 0,
  "reason": "当前问题题面完整，不需要旧数学题上下文。"
}
```

## 验收标准

- 数据结构定义完成: 已完成。
- 至少三种 policy 可运行: FullSession、RecentN、TaskScoped: 已完成。
- trace 可写入 JSONL: 已完成。
- 能在不接任何具体 agent runtime 的情况下对一段 mock session 输出 context decision: 已完成。

验证命令:

```bash
python /22liushoulong/agent/agent-context-isolation/experiments/run_context_policy_smoke.py
```
