# LightAgent 代码地图

日期: 2026-06-02。

## 基本信息

- 本地路径: `/22liushoulong/agent/agent-context-isolation/third_party/LightAgent`
- GitHub: https://github.com/wanxingai/LightAgent
- 当前 commit: `396ea2de930aad4cd2849061f99968198a059ac3`
- 版本: `0.7.0`
- License: Apache-2.0
- Python: `>=3.10,<4.0`
- 依赖管理: `pyproject.toml` + `requirements.txt`
- 当前复用环境: `miroflow-py312`

## Phase 0 环境处理

未创建新 conda 环境。

为了让 LightAgent 顶层 import 和 mock smoke 能跑通，已在已有 `miroflow-py312` 环境安装最小缺失依赖:

```bash
conda run -n miroflow-py312 python -m pip install boto3 colorama loguru
```

没有安装完整 `requirements.txt`，也没有安装 `mem0ai` 和 `langfuse`。后续若需要真实 memory 或 Langfuse tracing，再按需安装。

## 最小 Smoke

脚本:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

运行:

```bash
conda run -n miroflow-py312 python /22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

结果:

```text
content: x = 4
trace_types: ['run_start', 'model_request', 'model_response', 'run_end']
message_count: 4
roles: ['system', 'user', 'assistant', 'user']
last_user: Solve 2x + 3 = 11
has_tools: True
trace_request: {'model': 'mock-model', 'stream': False, 'message_count': 4, 'tools': ['execute_python_code', 'execute_python_file', 'execute_python_code_stream', 'upload_file_to_oss']}
```

结论:

- `agent.run(query, history=...)` 可直接接收 OpenAI message 格式历史。
- `result_format="object", trace=True` 能导出结构化 trace。
- 默认会暴露内置工具，即使没有传 runtime tools。
- 后续 `task_scoped_tool_filter` 需要显式控制可见工具，不能默认让全部内置工具进入模型请求。

## 运行入口

主入口:

```text
LightAgent/core.py
  LightAgent.__init__(...)
  LightAgent.run(...)
```

`run` 关键参数:

```python
agent.run(
    query: str,
    tools: list | None = None,
    history: list | None = None,
    user_id: str = "default_user",
    use_skills: bool = True,
    result_format: str = "str",
    trace: bool = False,
)
```

最适合 Phase 1 接入的方式:

```text
raw user message
  -> ContextPolicy.select(...)
  -> selected.messages
  -> selected.tools
  -> LightAgent.run(query, history=selected.messages, tools=selected.tools, trace=True)
```

先做 wrapper，不直接改 LightAgent 内部。

## Message Assembly

位置:

```text
LightAgent/core.py
  LightAgent.run(...)
```

关键逻辑:

```python
self.chat_params = {
    "model": self.model,
    "messages": [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": query}
    ],
    "stream": stream,
}
```

可插入点:

1. 外部 wrapper 预先裁剪 `history`。
2. 外部 wrapper 改写 `query`，加入 selected memory。
3. 后续如必须内部集成，可在这段 message assembly 前加 `ContextPolicy.select(...)`。

## Memory

协议:

```text
LightAgent/protocol.py
  MemoryProtocol.store(data, user_id)
  MemoryProtocol.retrieve(query, user_id)
  MemoryPolicy
```

注入位置:

```text
LightAgent/core.py
  _add_memory_context(query, user_id)
```

行为:

- 如果 `self.memory` 为空，不注入记忆。
- 如果存在 memory，会先 retrieve，再把结果拼进 query。
- 然后调用 `memory.store(data=query, user_id=...)`。
- `self_learning=True` 时还会检索 agent 自身记忆。

对本项目的影响:

- 初期建议不使用 LightAgent 内置 memory 自动注入。
- 由 `ContextPolicy` 自己选择 memories，再通过 wrapper 注入。
- 这样才能比较 `retrieval_only`、`need_gated`、`task_scoped`。
- 后期可实现一个受控 `MemoryProtocol`，内部只返回 policy 允许的 memory。

## Tools

位置:

```text
LightAgent/tools.py
  ToolRegistry
  ToolLoader
  AsyncToolDispatcher
```

工具格式:

- Python 函数需要 `tool_info`。
- `ToolRegistry.register_tool(...)` 会转成 OpenAI function schema。

`run` 中工具优先级:

```text
active_tools from ToT
  > runtime_tools passed to run(...)
  > self.tool_registry.get_tools()
```

风险:

- 初始化时会自动注册内置工具:
  - `execute_python_code`
  - `execute_python_file`
  - `execute_python_code_stream`
  - `upload_file_to_oss`
- 如果 wrapper 没传 runtime tools，模型仍会看到这些默认工具。

建议:

- benchmark 运行时优先用 `tools=selected_tools` 覆盖默认工具。
- 若某个策略不允许工具，应传空工具并在 wrapper 或 LightAgent subclass 中阻断默认 registry。
- Phase 1/3 需要实现 `LightAgentContextWrapper`，显式处理 no-tool 场景。

## Skills

位置:

```text
LightAgent/skills.py
LightAgent/skill_tools.py
```

初始化逻辑:

- `auto_discover_skills=True` 时扫描 `skills_directories`。
- 如果发现 skill，会自动注册:
  - `list_skills`
  - `activate_skill`
  - `execute_skill_script`
  - `read_skill_reference`

`run` 逻辑:

- `use_skills=True` 且有 skills 时，会把 skill metadata 加进 system prompt。
- 模型可调用 `activate_skill` 加载完整 SKILL.md。

对本项目的意义:

- 这正好对应用户担心的“skill 多了 router 变难”。
- 初期 benchmark 不要自动暴露全部 skills。
- `task_scoped_tool_filter` 应把 skill metadata 和 skill tools 一起过滤。

建议:

- 实验初始化时设置 `auto_discover_skills=False`。
- 由 wrapper 传入当前 benchmark 需要的 skill/tool。
- 后续做 skill-routing 实验时，再打开受控 skill registry。

## Trace

位置:

```text
LightAgent/tracing.py
LightAgent/result.py
LightAgent/core.py
  export_trace()
  _record_trace(...)
  _build_model_request_trace(...)
```

能力:

- `run_start`
- `model_request`
- `tool_call`
- `tool_result`
- `model_response`
- `run_end`
- `error`

限制:

- `model_request` trace 默认只记录摘要，不记录完整 messages。
- 这对安全是好事，但 benchmark 错误分析需要额外保存 selected context。

建议:

- ContextPolicy wrapper 另写 `context_trace.json`。
- LightAgent trace 保存模型请求摘要和工具调用轨迹。
- 两者通过 `trace_id` 或 sample id 关联。

## Phase 1 推荐 Wrapper

目标文件:

```text
src/context_isolation/wrappers/lightagent.py
```

推荐接口:

```python
class LightAgentContextWrapper:
    def __init__(self, agent, context_policy):
        self.agent = agent
        self.context_policy = context_policy

    def run(self, session_id, user_id, current_message, raw_history, available_tools=None):
        selected = self.context_policy.select(
            session_id=session_id,
            user_id=user_id,
            current_message=current_message,
            raw_history=raw_history,
            available_tools=available_tools,
        )
        result = self.agent.run(
            current_message,
            history=selected.messages,
            tools=selected.tools,
            user_id=user_id,
            result_format="object",
            trace=True,
        )
        return result, selected.trace
```

## 关键风险

1. 默认内置工具会进入请求，需要在 wrapper 层显式屏蔽。
2. LightAgent memory 自动注入会干扰本项目的 retrieval policy 对比，初期应关闭。
3. skill metadata 注入 system prompt 也会造成“隐式可见 skill”，需要受控。
4. ToT 会额外调用模型做工具过滤，不适合低成本主实验，初期应关闭 `tree_of_thought`。
5. 当前 LightAgent 顶层 import 依赖 `boto3`，即使不使用对象存储工具。

## Phase 0 结论

LightAgent 适合作为主实现 baseline。

原因:

- 有明确 `history` 参数。
- 有 runtime `tools` 参数。
- 有 memory protocol。
- 有 skill manager。
- 有结构化 trace。
- 代码体量比 MiroFlow 小，wrapper 接入成本低。
