# 长对话存储与检索优化路线

## 背景

本项目研究的是聊天软件绑定场景下的 agent：所有任务都发生在同一个 session 里，用户可能连续问生活、数学、代码、工具调用、长期偏好等问题。核心风险不是“上下文越多越好”，而是旧上下文会污染当前任务。

因此，存储层和检索层要服务于一个原则：

```text
先判断当前消息是否需要历史，再决定到哪里找、找多少、能不能用。
```

## 不建议的方案

1. 每条消息都无条件向量检索。
   - 相似不等于相关。
   - 两道数学题可能很相似，但彼此无关。
   - 无条件检索会增加 token 成本，也会增加错误引用旧信息的概率。

2. 只保留一个全局 memory。
   - 会丢失审计和复现实验能力。
   - 无法判断某条结论来自哪个任务。
   - 很难做 task-level 的隔离和回滚。

3. 只保留完整 raw history。
   - 长 session 成本会快速增长。
   - 后续模型容易被早期任务、旧约束、旧工具状态干扰。

## 推荐的分层存储

短期先用 JSONL，后续可以迁移到 SQLite / LanceDB / pgvector。

### 1. 原始消息层：`turns.jsonl`

保存每一轮用户和助手消息，用于审计、复现、错误分析。

字段建议：

```json
{
  "turn_id": "turn_000123",
  "session_id": "session_a",
  "task_id": "math_0007",
  "role": "user",
  "content": "...",
  "timestamp": "...",
  "metadata": {
    "benchmark": "MATH",
    "sample_id": "algebra_7"
  }
}
```

这层不应该默认进入 prompt，只作为可追溯底账。

### 2. 任务层：`tasks.jsonl`

每个 task 保存边界、状态、摘要和局部事实。

字段建议：

```json
{
  "task_id": "math_0007",
  "session_id": "session_a",
  "status": "completed",
  "domain": "math",
  "title": "Solve algebra problem 7",
  "summary": "Solved an independent algebra problem. Final answer was ...",
  "turn_ids": ["turn_000121", "turn_000122"],
  "local_facts": {},
  "skills_used": [],
  "updated_at": "..."
}
```

这层是后续检索的主入口。大多数情况下，检索任务摘要比检索每条原始消息更稳定、更省 token。

### 3. 长期记忆层：`memories.jsonl`

只保存跨任务仍然有效的信息，例如用户偏好、项目约束、稳定身份信息。

字段建议：

```json
{
  "memory_id": "mem_001",
  "user_id": "user_a",
  "scope": "global_profile",
  "content": "User prefers Chinese responses.",
  "source_task_id": "task_0001",
  "confidence": 0.95,
  "ttl": null
}
```

不能把单个数学题答案、临时工具状态、一次性约束放进长期记忆。

### 4. 工具状态层：`tool_state.jsonl`

只记录和工具调用有关的可延续状态，例如订单、文件、浏览器、任务队列。

字段建议：

```json
{
  "state_id": "state_001",
  "task_id": "travel_0002",
  "tool_name": "calendar",
  "state": {"event_id": "evt_123", "date": "..."},
  "valid_until": "...",
  "status": "active"
}
```

工具状态必须有作用域和有效期，避免旧订单、旧文件路径、旧浏览器页面污染新任务。

### 5. 决策轨迹层：`traces.jsonl`

保存每次上下文选择的判断过程。

字段建议：

```json
{
  "session_id": "session_a",
  "turn_id": "turn_000124",
  "policy": "task_scoped",
  "need_gate": "...",
  "boundary": "...",
  "selected_turn_ids": [],
  "selected_memory_ids": [],
  "suppressed_tools": [],
  "input_tokens_est": 123
}
```

这是实验论文里最重要的可解释性材料之一。

## 推荐检索流程

完整流程：

```text
Current message
  -> Need Gate：是否自足，是否需要历史
  -> Boundary Detector：新任务 / 继续任务 / 相关任务 / 模糊引用
  -> Scope Filter：只在候选 task / memory scope 内找
  -> Metadata Filter：benchmark、domain、tool、时间、状态过滤
  -> Sparse/Dense Retrieval：BM25 / embedding / hybrid
  -> Evidence Validator：候选证据是否真的回答当前缺失信息
  -> Prompt Assembly：只拼接被验证过的最小上下文
```

关键点：

1. Need Gate 放在所有检索之前。
2. metadata/task scope 过滤放在向量检索之前。
3. 向量检索只是候选召回，不是最终决策。
4. Evidence Validator 要能拒绝“相似但无关”的历史。
5. Prompt Assembly 要限制 token budget，并保留 trace。

## 后续可优化方向

### 方向 1：双层 Need Gate

先用廉价规则和小分类器判断：

```text
self-contained / explicit reference / ambiguous / tool-state / long-term-memory
```

只有低置信或高风险样本才调用大模型裁决。

价值：

- 降低每条消息都调用大模型 router 的成本。
- 避免普通独立任务触发历史检索。

### 方向 2：任务边界分类器

用公开 benchmark 包装出的 same-session 数据训练或评估：

```text
new_task
continue_task
related_task
ambiguous
```

特征可以包括：

- 显式指代词。
- 当前消息和最近 task summary 的相似度。
- 是否出现“上一题、刚才、继续、按之前”等引用。
- 是否存在工具状态引用。
- 是否存在实体延续。

### 方向 3：任务摘要优先检索

优先检索 `tasks.jsonl` 的摘要，而不是所有 raw turns。

只有当 task summary 命中且证据不足时，才展开该 task 的 raw turns。

好处：

- token 更低。
- 不容易把旧任务的细节噪声带进 prompt。
- 对长 session 更稳定。

### 方向 4：Hybrid Retrieval

后续可以做：

```text
BM25 sparse score
+ embedding dense score
+ recency score
+ task-status score
+ explicit-reference score
```

但必须在 scope filter 之后做，不能全库乱搜。

### 方向 5：反证式 Evidence Validator

验证候选上下文时，不只问“是否相关”，还要判断：

```text
如果把这段上下文加入 prompt，是否可能误导当前任务？
```

例如两道数学题同属 algebra，但题干完全不同，应判为高污染风险。

### 方向 6：Memory 写入门控

不是每条 assistant 输出都写 memory。

写入前要分类：

- `task_local`: 只留在 task summary。
- `global_profile`: 可以进长期记忆。
- `project_memory`: 可以跨 session 使用。
- `tool_state`: 写入工具状态层。
- `ephemeral`: 不写长期 memory。

### 方向 7：可撤销与过期机制

每条 memory / tool state 要有：

- source task。
- confidence。
- created_at / updated_at。
- ttl 或 valid_until。
- status。

避免旧偏好、旧订单、旧实验配置长期污染。

## 当前 Phase 3 的落地范围

短期不先实现向量库，先实现可验证闭环：

1. 用 raw history 模拟同一个 session。
2. 用 policy 决定传给 LightAgent 的 history 子集。
3. 保存每道题的 context decision trace。
4. 对比 `full_session`、`recent_n`、`task_scoped`。
5. 先在 MATH 小样本做 same-session stress，再扩展到 AgentIF / LongMemEval / MultiChallenge。

向量数据库、任务摘要生成、分类器训练放到 Phase 6。
