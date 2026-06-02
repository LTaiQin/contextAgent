# Phase 0 完成记录

日期: 2026-06-02。

## 结论

Phase 0 已完成。

最终 baseline 决策:

```text
主实现 baseline: LightAgent
备选实现 baseline: LangGraph
强参考 baseline: MiroFlow
```

## 已完成事项

### 1. LightAgent 仓库确认

- 路径: `/22liushoulong/agent/agent-context-isolation/third_party/LightAgent`
- commit: `396ea2de930aad4cd2849061f99968198a059ac3`
- license: Apache-2.0
- 版本: `0.7.0`
- Python: `>=3.10,<4.0`
- 依赖文件: `pyproject.toml`, `requirements.txt`

### 2. 运行环境

没有创建新虚拟环境。

复用已有 conda 环境:

```text
miroflow-py312
```

为完成 LightAgent 顶层 import 和 Phase 0 mock smoke，安装了最小缺失依赖:

```bash
conda run -n miroflow-py312 python -m pip install boto3 colorama loguru
```

未安装完整 LightAgent requirements。

### 3. LightAgent 最小 demo

已跑通 mock demo，不调用真实模型 API。

脚本:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

运行命令:

```bash
conda run -n miroflow-py312 python /22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

输出:

```text
content: x = 4
trace_types: ['run_start', 'model_request', 'model_response', 'run_end']
message_count: 4
roles: ['system', 'user', 'assistant', 'user']
last_user: Solve 2x + 3 = 11
has_tools: True
trace_request: {'model': 'mock-model', 'stream': False, 'message_count': 4, 'tools': ['execute_python_code', 'execute_python_file', 'execute_python_code_stream', 'upload_file_to_oss']}
```

验证结果:

- `history` 参数可用。
- `trace=True` 可用。
- `result_format="object"` 可用。
- runtime 可被 mock client 测试，不必每次消耗 API。

重要发现:

- LightAgent 默认会暴露内置工具。
- 后续必须在 wrapper 中显式控制 tool visibility。
- 初期应关闭 `tree_of_thought`、`memory`、`self_learning` 和自动 skill discovery，避免影响上下文隔离实验。

### 4. LightAgent 代码地图

文档:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent-code-map.md
```

已定位:

- agent 入口: `LightAgent/core.py::LightAgent.run`
- history 注入点: `chat_params["messages"]`
- memory 注入点: `_add_memory_context`
- tool registry: `LightAgent/tools.py`
- skill registry: `LightAgent/skills.py`, `LightAgent/skill_tools.py`
- trace: `LightAgent/tracing.py`, `LightAgent/result.py`

### 5. LangGraph 备选方案

文档:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/langgraph-runtime-sketch.md
```

结论:

- 当前不切换到 LangGraph。
- 若 LightAgent 无法干净屏蔽默认工具、memory 或 skill 注入，再切换到 LangGraph。

### 6. MiroFlow 降级

MiroFlow 仍保留:

- 路径: `/22liushoulong/agent/agent-context-isolation/third_party/MiroFlow`
- commit: `95857bc962c128b9e925c8e9e85b55fdfb1a8ba6`
- license: Apache-2.0

用途:

1. 强 reported baseline。
2. deep-research 系统参考。
3. optional integration。
4. 成本/复杂度对照案例。

不再用于:

- 主实现 baseline。
- 日常低成本实验。
- 全量 HLE/GAIA 复现。

## Phase 1 入口

下一步应实现独立上下文隔离层:

```text
src/context_isolation/
  schema.py
  store.py
  policy.py
  trace.py
```

优先实现的策略:

1. `full_session`
2. `recent_n`
3. `retrieval_only`
4. `need_gated`
5. `task_scoped`
6. `task_scoped_tool_filter`

LightAgent 接入方式:

```text
raw_history + current_message + available_tools
  -> ContextPolicy.select(...)
  -> selected.messages + selected.tools
  -> LightAgent.run(...)
```

## Phase 0 验收状态

| 验收项 | 状态 |
| --- | --- |
| LightAgent 下载完成 | 已完成 |
| LightAgent commit/license/quickstart 记录 | 已完成 |
| LightAgent 最小 demo 跑通 | 已完成，mock client |
| history/memory/tool/skill 插入点地图 | 已完成 |
| LangGraph 备选 runtime 设计草图 | 已完成 |
| MiroFlow 降级说明 | 已完成 |
| 后续 Phase 1/2 可不依赖 MiroFlow 继续 | 已满足 |
