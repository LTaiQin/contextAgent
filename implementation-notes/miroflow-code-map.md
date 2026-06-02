# MiroFlow 代码地图

日期: 2026-06-02

目标: 给后续上下文隔离实现提供最短路径的代码定位。

## 1. 运行入口

- `main.py`
  - 选择 `common-benchmark` 作为主入口。
- `common_benchmark.py`
  - benchmark 读取、任务调度、单样本执行、结果汇总。

## 2. 主 agent 核心

- `src/core/orchestrator.py`
  - `run_main_agent(...)`
  - 组装初始 user message
  - 生成 system prompt
  - 发起主循环
  - 执行最终摘要与答案提取

关键插入点:

1. `initial_user_content` 生成之后
2. `message_history = [{"role": "user", ...}]` 之前或之后
3. `tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()`
4. `system_prompt = ...`
5. `message_history` 每轮更新前后

## 3. 历史与 token 裁剪

- `src/llm/provider_client_base.py`
  - `_remove_tool_result_from_messages(...)`
  - `_filter_message_history(...)`
  - `create_message(...)`

这里是做“只保留相关历史”或“按任务裁剪上下文”的最直接位置。

## 4. 工具与 skill 候选集

- `src/tool/manager.py`
  - `get_all_tool_definitions()`
  - `execute_tool_call()`
  - `_find_servers_with_tool()`

这里适合接入 tool/skill router，做候选过滤或任务级屏蔽。

## 5. 提示词层

- `config/agent_prompts/main_agent_prompt_gaia.py`
- `config/agent_prompts/main_boxed_answer.py`

这里决定 task guidance、最终总结格式、工具暴露方式。

## 6. 评测层

- `common_benchmark.py`
  - `run_single_task(...)`
  - `_evaluate_attempt(...)`
  - `run_parallel_inference(...)`

这里适合做小样本 benchmark、ablation、deterministic scoring。

## 7. 已确认的上下文隔离切入顺序

建议按这个顺序实现：

1. `task boundary detector`
2. `context selector`
3. `tool candidate filter`
4. `message history pruning`
5. `trace logger`

## 8. 当前已知约束

- DeepSeek Flash smoke 跑通，但不代表官方分数复现。
- 当前缺少完整外部搜索/代码工具密钥，严格官方链路未补齐。
- 先做 wrapper，不要直接重构 MiroFlow 核心流程。
