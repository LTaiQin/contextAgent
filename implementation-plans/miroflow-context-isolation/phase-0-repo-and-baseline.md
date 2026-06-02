# Phase 0: Baseline 决策与仓库准备

## 目标

完成 baseline 重新选择，并把实现主线从 MiroFlow 调整为轻量 agent runtime。

新决策:

```text
主实现 baseline: LightAgent
备选实现 baseline: LangGraph
强参考 baseline: MiroFlow
```

## 背景

前期已经下载并测试过 MiroFlow:

```text
/22liushoulong/agent/agent-context-isolation/third_party/MiroFlow
```

MiroFlow commit:

```text
95857bc962c128b9e925c8e9e85b55fdfb1a8ba6
```

已完成:

- 跑通过 DeepSeek Flash / GPT 兼容接口 smoke。
- 定位了 MiroFlow 插入点。
- 分析了单题成本。
- 确认完整 MiroFlow baseline 依赖搜索、reading、E2B、reasoning 等外部服务。

结论:

```text
MiroFlow 太重，不适合作为主实现 baseline。
```

## 新 Phase 0 输出

必须完成:

- `third_party/LightAgent/`: 已完成。
- LightAgent commit hash、license、quickstart: 已完成。
- LightAgent 最小 chat run: 已完成，使用 mock client，不消耗 API。
- LightAgent 的 history/memory/tool/skill 插入点地图: 已完成。
- LangGraph 备选 runtime 设计草图: 已完成。
- MiroFlow 降级说明和 optional integration 位置: 已完成。

完成记录:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/phase-0-completion.md
/22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent-code-map.md
/22liushoulong/agent/agent-context-isolation/implementation-notes/langgraph-runtime-sketch.md
```

## 0.1 下载 LightAgent

状态: 已完成。本地已存在 LightAgent 仓库。

```bash
cd /22liushoulong/agent/agent-context-isolation
mkdir -p third_party
git clone https://github.com/wanxingai/LightAgent.git third_party/LightAgent
```

记录:

- commit hash: `396ea2de930aad4cd2849061f99968198a059ac3`
- license: Apache-2.0
- Python version: `>=3.10,<4.0`
- dependency manager: `pyproject.toml` + `requirements.txt`
- quickstart command: `agent.run("...")`
- 是否支持 history 参数: 支持，`agent.run(query, history=...)`
- 是否支持 memory/skill/tool/MCP: 支持

## 0.2 跑通 LightAgent 最小示例

状态: 已完成，使用 mock OpenAI client。

脚本:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

命令:

```bash
conda run -n miroflow-py312 python /22liushoulong/agent/agent-context-isolation/implementation-notes/lightagent_phase0_smoke.py
```

输出摘要:

```text
content: x = 4
trace_types: ['run_start', 'model_request', 'model_response', 'run_end']
message_count: 4
roles: ['system', 'user', 'assistant', 'user']
```

目标不是高分，而是拿到完整 trace:

- 输入消息
- history 输入方式
- skill/tool 候选列表
- memory 读写位置
- final response
- token/cost 统计方式

最低要求:

```text
query: "Solve 2x + 3 = 11"
history: []
expected: x = 4
```

## 0.3 代码结构摸底

需要定位:

- agent 入口
- `run(query, history=...)` 或等价入口
- memory store
- skill registry / router
- tool/MCP registry
- message assembly
- callback/logging hook

输出到:

```text
implementation-notes/lightagent-code-map.md
```

状态: 已完成。

## 0.4 LangGraph 备选设计

如果 LightAgent 不适合，使用 LangGraph 自建固定 runtime:

```text
intake
  -> context_policy
  -> tool_filter
  -> llm_agent
  -> memory_update
```

输出:

```text
implementation-notes/langgraph-runtime-sketch.md
```

状态: 已完成。

## 0.5 MiroFlow 保留方式

MiroFlow 只保留为:

1. 强 reported baseline。
2. deep-research 参考系统。
3. optional integration。
4. 成本/复杂度对照案例。

不再要求完整复现 MiroFlow 官方结果。

状态: 已完成。

## 验收标准

- LightAgent 下载完成: 已完成。
- LightAgent 最小 demo 跑通: 已完成。
- 明确 context isolation 能插入的位置: 已完成。
- 明确 MiroFlow 不再是主实现 baseline: 已完成。
- 后续 Phase 1/2 可以在不依赖 MiroFlow 的情况下继续开发: 已满足。
