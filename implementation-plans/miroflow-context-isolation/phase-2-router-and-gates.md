# Phase 2: 上下文需求路由与门控

## 目标

实现“不是每条消息都检索历史”的核心逻辑:

```text
自足性判断 -> 历史依赖判断 -> 任务边界检测 -> 上下文需求分类 -> 范围受控检索 -> 证据验证
```

当前状态:

```text
Phase 2 已启动，规则版实现已落地。
记录: /22liushoulong/agent/agent-context-isolation/implementation-notes/phase-2-started.md
```

已实现模块:

- `src/context_isolation/gates.py`
- `src/context_isolation/boundary.py`
- `src/context_isolation/retrieval.py`
- `src/context_isolation/evidence.py`
- `src/context_isolation/tool_filter.py`

## 2.1 自足性判断器

### 目标

判断当前消息在不看历史的情况下是否足够完成任务。

### 输出

```json
{
  "self_sufficient": true,
  "missing_info": [],
  "needs_history": false,
  "risk_if_using_history": "high",
  "confidence": 0.92,
  "reason": "题面完整，旧上下文可能污染变量解释。"
}
```

### 三层实现

| 层级 | 方法 | 覆盖对象 | 备注 |
| --- | --- | --- | --- |
| 高精度规则 | 少量规则 | 明确继续、明确新问题、完整数学题、明显工具状态 | 只早退，不追求覆盖率 |
| 轻量分类器 | 小模型 / embedding + classifier / 蒸馏模型 | 大部分普通消息 | Phase 6 再训练，Phase 2 先用 LLM judge mock |
| LLM judge | 便宜模型或主模型 | 歧义样本 | 调用率应被控制 |

### 规则例子

高置信依赖:

- 包含 “刚才 / 上一个 / 继续 / 按那个 / 照之前 / 这个文件 / 那份表格”
- 包含 “取消刚订的 / 改那个日历 / 继续写”

高置信自足:

- 明确完整数学题: 包含完整表达式和求解目标。
- 明确翻译: “把 XXX 翻译成英文”。
- 明确独立问答: “什么是 XXX”。
- 明确代码问题且包含错误/代码片段。

注意:

- 规则只判断明显样本。
- 不允许写大量 domain-specific if-else。
- 低置信度必须交给分类器或澄清。

## 2.2 历史依赖类型分类

分类标签:

| 标签 | 说明 |
| --- | --- |
| `no_context` | 当前消息自足，不需要历史 |
| `task_local` | 需要当前任务上下文 |
| `related_summary` | 需要相关旧任务摘要 |
| `global_profile` | 需要长期用户偏好/事实 |
| `project_memory` | 需要项目级记忆 |
| `tool_state` | 需要工具状态 |
| `clarification` | 信息不足，应向用户澄清 |

## 2.3 任务边界检测

输出:

- `new_task`
- `continue_task`
- `related_task`
- `ambiguous`

关键原则:

- 同领域不等于同任务。
- “数学题 A -> 数学题 B”默认新任务，除非用户显式说“类似刚才”。
- “旅行东京 -> 旅行大阪”默认新任务或 related summary，不直接继承具体行程。
- “修改刚才文档”是 continue。
- 多候选引用时返回 ambiguous。

## 2.4 检索范围控制

只有 `need_type != no_context` 时才检索。

| need_type | 允许检索范围 |
| --- | --- |
| task_local | 当前 task turns / artifacts / tool_state |
| related_summary | 相关 task summaries，不取 raw turns |
| global_profile | 用户画像记忆 |
| project_memory | 项目记忆 |
| tool_state | task-local 或确认过的 global tool state |
| clarification | 不检索或只取候选任务名用于澄清 |

## 2.5 证据验证

检索结果进入 prompt 前必须过验证器。

验证项:

1. 是否补足当前缺失信息。
2. 是否和当前实体一致。
3. 是否来自被引用任务。
4. 是否是长期偏好而非临时约束。
5. 是否存在冲突或过期。
6. 是否可能改变独立问题语义。

## 2.6 成本控制

目标:

- 大多数消息不调用 LLM router。
- 只有歧义样本调用 LLM judge。
- 所有 router 调用记录 token 和 latency。

指标:

- LLM judge 调用率。
- 平均 router token。
- 平均 router latency。
- 自足性判断准确率。
- 必要上下文漏检率。
- 不必要检索率。

## 验收标准

- 输入单条消息和 mock history，能输出完整 `ContextDecision`: 已完成。
- 明显自足消息不会检索历史: 已完成。
- 明显引用历史消息能定位到 task_local: 已完成。
- 同领域新任务不会错误继承旧任务 raw turns: 初步完成，待补专门测试。
- 所有决策都有 reason 和 confidence: 已完成。

当前验证命令:

```bash
python /22liushoulong/agent/agent-context-isolation/experiments/run_context_policy_smoke.py
```
