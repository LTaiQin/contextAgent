# Phase 3: 接入轻量 Agent Runtime

## 目标

把 Phase 1/2 的 context isolation layer 接到主实现 baseline，并让真实 benchmark runner 可以切换上下文策略。

优先级:

1. LightAgent
2. LangGraph
3. MiroFlow optional integration

当前执行状态：

- 已选择 LightAgent 作为主 runtime。
- MiroFlow 只保留为参考或后续 optional smoke，不再作为主要 baseline。
- Phase 3 已开始：新增 MATH same-session policy runner，用来测试同一个聊天 session 中连续做公开 MATH 题时，不同上下文策略是否会引入历史污染。

## 原则

1. 主实现不依赖完整 deep-research 工具链。
2. 优先 wrapper，不改第三方 core。
3. 保留原始 baseline，可一键切换策略。
4. 所有实验通过统一 policy 参数控制。
5. 运行成本必须可控，不能默认触发 web search / code sandbox。

## 方案 A: LightAgent Wrapper

目标接口:

```python
class IsolatedLightAgent:
    def __init__(self, agent, context_policy):
        self.agent = agent
        self.context_policy = context_policy

    def run(self, session_id, user_id, message, raw_history=None, tools=None, **kwargs):
        selected = self.context_policy.select(
            session_id=session_id,
            user_id=user_id,
            current_message=message,
            raw_history=raw_history or [],
            available_tools=tools,
        )
        return self.agent.run(
            query=message,
            history=selected.messages,
            tools=selected.tools,
            system_addendum=selected.system_addendum,
            **kwargs,
        )
```

如果 LightAgent 原生接口不支持 `tools` 或 `system_addendum`，则做最小 adapter:

```text
selected.messages -> history
selected.tools -> skill/tool candidate registry filter
selected.system_addendum -> prompt prefix
```

当前已落地：

- `src/context_isolation/wrappers/lightagent.py`
- `experiments/run_math_same_session_policy.py`

runner 的核心逻辑：

```text
load public MATH samples
  -> keep one shared raw_history
  -> policy.select(current_problem, raw_history)
  -> LightAgent.run(history=selected.messages)
  -> score current task
  -> append current user/assistant turns to the same raw_history
```

这和普通独立评测不同：所有题都在同一个 session 里发生，但每一道题仍按公开 MATH 标准答案评分。

## 方案 B: LangGraph Controlled Runtime

如果 LightAgent 接入成本高，直接用 LangGraph 建固定 runtime:

```text
UserMessage
  -> ContextPolicyNode
  -> ToolFilterNode
  -> AgentNode
  -> MemoryUpdateNode
  -> TraceNode
```

优点:

- 状态显式。
- policy 节点可替换。
- 方便 benchmark adapter 调用。
- 不依赖外部 web/code 工具。

## 方案 C: Optional MiroFlow Integration

MiroFlow 不作为主线，但保留可选集成:

```text
benchmark sample -> context policy -> MiroFlow task input
```

用途:

- 最后做 1 到 3 道 smoke。
- 展示强 agent 框架也可接入 context policy。
- 不强求完整官方工具链复现。

## 策略切换

统一 CLI:

```bash
python experiments/run_math_same_session_policy.py \
  --policy task_scoped \
  --limit 10 \
  --out-dir experiments/runs/math_same_session_task_scoped_10
```

支持:

```text
--policy full_session
--policy recent_n
--policy retrieval_only
--policy need_gated
--policy task_scoped
```

无成本流程验证：

```bash
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_math_same_session_policy.py \
  --policy task_scoped \
  --limit 3 \
  --dry-run
```

tmux 实验命令模板：

```bash
tmux new -s math_same_session_task_scoped
conda run --no-capture-output -n miroflow-py312 \
  python experiments/run_math_same_session_policy.py \
  --policy task_scoped \
  --limit 10 \
  --out-dir experiments/runs/math_same_session_task_scoped_10
```

## Cross-task Stress Setting

公开 benchmark 往往是单任务或单会话。为了测试聊天 session 污染，需要 adapter:

```text
sample_i as distractor history
sample_j as current task
```

规则:

- 不修改 current task 的答案和评分器。
- distractor 只作为 chat history。
- distractor 来自公开 benchmark 其他任务。
- 可控制干扰强度:
  - same-domain unrelated
  - different-domain unrelated
  - same-tool unrelated
  - same-entity related
  - explicit reference
  - ambiguous reference

## 输出日志

每个样本保存:

- benchmark id
- agent runtime
- policy
- original sample id
- distractor ids
- context decision
- selected context
- selected/suppressed tool candidates
- final answer
- score
- cost
- errors

## 验收标准

- LightAgent 原始独立 baseline 可运行。已完成。
- `full_session`、`recent_n`、`task_scoped` 至少三种策略可切换。已完成。
- 能在公开 benchmark 小样本上比较不同策略的上下文输入。MATH same-session runner 已完成。
- trace 中能看到为什么没有检索旧上下文。已完成。
- MiroFlow optional integration 不阻塞主实验。已调整为 optional。

## 下一步

1. 跑 MATH same-session dry-run，确认 trace 和日志格式。
2. 用 `task_scoped` 小样本真实调用 3 到 10 题，观察输入 token 是否明显低于 `full_session`。
3. 再跑同样样本的 `full_session` 和 `recent_n`，形成第一组策略对比。
4. 将同样的策略接口接到 AgentIF runner。
5. 开始构造跨 benchmark mixed single-session validation adapter。
