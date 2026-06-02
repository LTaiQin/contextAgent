# 面向聊天式 Agent 的任务级上下文隔离研究方案

日期: 2026-06-01

## 0. 研究问题

普通用户把 agent 绑定到聊天软件后，生活、办公、学习、搜索、代码、工具调用、多个 skill 的任务会混在同一个长 session 中。现有 agent 往往把聊天 session 近似当成推理上下文，导致无关历史、旧任务变量、旧工具状态、旧 skill 指令进入当前任务。

本方案研究:

> 如何把一个聊天 session 拆成多个任务级推理上下文，并在每个任务范围内选择历史、记忆、摘要、工具和 skill 候选，从而减少上下文污染和错误路由。

## 1. 借鉴已有工作

| 已有方向 | 代表工作 | 时间 | 可借鉴技术 | 为什么不能直接照搬 |
| --- | --- | --- | --- | --- |
| 分层记忆 / 虚拟上下文 | MemGPT | 2023-10-12 arXiv | 快速/慢速记忆、显式记忆操作、外部存储思想 | 它主要解决上下文窗口和长期记忆，不专门处理同一聊天 session 内的多任务边界 |
| 动态上下文压缩 | Active Context Compression / context compression 类工作 | 2026-01 arXiv 相关工作 | 长历史压缩、摘要保持、压缩预算控制 | 压缩不是隔离；压缩后仍可能保留错误任务信息 |
| 记忆编排 / 意图驱动检索 | MemFlow / memory routing 类工作 | 2026-05 arXiv 相关工作 | 按意图选择记忆层、路由 agent、局部/全局记忆分层 | 重点是选择相关记忆，不一定显式建模任务生命周期 |
| 角色/上下文路由 | RCR-Router 类工作 | 2025-08 arXiv 相关工作 | 路由策略、结构化上下文、按角色分配上下文 | 多用于多 agent 角色记忆，不是单用户聊天窗口中的多任务 session |
| skill 作为记忆 | Acontext | 2025-2026 开源项目/文档 | skill 文件、session 存储、任务跟踪、可编辑知识沉淀 | 偏经验沉淀和 skill 学习，不直接评估任务隔离带来的污染降低 |
| agent 组件消融 | OAgents | 2025-06-23 arXiv | 标准化评测协议、组件消融、随机性控制 | 可借鉴实验严谨性，但它的核心不是任务级上下文隔离 |
| 多轮工具交互评测 | tau2/tau3 | tau2: 2025-06-09 arXiv；tau-bench: 2024-06-17 arXiv | Pass^k、user simulator、domain tools、final state check | 作为实验场景，不是方法 |
| 长 agentic instruction 评测 | AgentIF | 2025-05-22 arXiv | CSR/ISR、constraint type breakdown、tool spec constraints | 作为实验场景，不是方法 |
| 日常 agent 任务评测 | AgentIF-OneDay | 2026-01-30 arXiv | task-level daily scenarios、attachments、rubric score | 作为产品贴近度验证，不是方法 |

### 1.1 时间线

| 时间 | 工作 | 与本方案的关系 |
| --- | --- | --- |
| 2023-10 | MemGPT | 早期代表性分层记忆/虚拟上下文工作，证明 agent 需要显式记忆管理 |
| 2024-06 | tau-bench | 提出 user-agent-tool 交互式 benchmark 和 Pass^k 可靠性指标 |
| 2025-05 | AgentIF | 提出 agentic 场景长指令/工具约束遵循 benchmark，可直接评估 skill/tool instruction 污染 |
| 2025-06 | OAgents | 系统研究 agent 组件选择和复现实验协议，可借鉴消融设计 |
| 2025-06 | tau2-Bench | 扩展到 dual-control 对话环境，更贴近真实用户和工具共同改变状态的场景 |
| 2025-08 | RCR-Router 类工作 | 代表 context routing / memory routing 思路，但更偏多 agent 角色上下文 |
| 2025-2026 | Acontext | 代表 skill/memory 文件化和 task tracking 思路，可借鉴工程形态 |
| 2026-01 | AgentIF-OneDay | 面向普通用户日常任务、附件、文件产出的 task-level benchmark，最贴近本方案产品假设 |
| 2026-01 | Active Context Compression 类工作 | 代表动态上下文压缩方向，可作为 summarization/compression baseline |
| 2026-05 | MemFlow 类工作 | 代表意图驱动记忆编排方向，可作为 retrieval/memory routing baseline |

## 2. 可主张的创新

### 创新 1: 聊天 session 和推理任务解耦

传统做法:

```text
聊天 session 历史 -> agent prompt
```

本方案:

```text
聊天消息流 -> 任务边界检测器 -> 任务上下文存储 -> 被选择的推理上下文
```

创新边界:

- 不是发明 memory。
- 是把传输层的聊天 session 与推理层的任务上下文分开。

### 创新 2: 任务范围内的工作记忆

每个 task 有独立的:

- 局部对话轮次
- 任务摘要
- 局部事实 / 变量
- 工具状态
- 候选 skills / tools
- 产物 / 文件
- 状态: 活跃、暂停、完成、归档

全局用户记忆只在经过 relevance gate 后进入。

### 创新 3: 先隔离上下文，再做工具和 skill 路由

现有 router 往往看到完整 session 或近邻 context，容易被旧 skill、旧 tool、旧任务状态影响。

本方案先隔离 context，再做 tool/skill routing:

```text
当前消息 -> 任务范围 -> 记忆选择 -> 工具/skill 候选过滤 -> agent 执行
```

### 创新 4: 基于公开 benchmark 的跨任务压力测试

不自造 toy benchmark，而是基于公开 benchmark 构造 stress setting:

- 从 GAIA / AgentIF / tau2 / LongMemEval / AgentIF-OneDay 取公开任务。
- 按同一用户 session 串联多个任务。
- 不改 benchmark 原答案和评分器。
- 只改变 agent 可见上下文策略。

这样能评估真实公开任务上的污染和隔离效果。

### 创新 5: 先判断“是否需要上下文”，再决定是否检索

现有很多 agent 默认把历史当作有用信息，或者每次都做检索。但在真实聊天中，很多消息本身是自足的，即使它和之前属于同一大领域，也不一定需要历史。

典型例子:

- 学生上一题问了一道数学题，现在又问另一道数学题。两者同属数学，但通常不相关。
- 用户昨天问过东京旅行，今天问大阪旅行。都是旅行，但不应默认复用东京计划。
- 用户之前用了论文写作 skill，现在问预算计算。旧 skill 不应影响当前回答。

因此本方案加入 **Context Need Gate**:

```text
当前消息
  -> 自足性判断
  -> 如果信息充足: 不检索历史，直接新建/独立处理
  -> 如果信息不足: 判断缺失信息类型
  -> 再决定检索 task-local / related-task / global memory / ask clarification
```

这可以把方法从“更好的检索”升级为“是否应该检索”的决策问题。

### 创新 6: 多阶段上下文决策，而不是单步检索

本方案把上下文选择拆成多阶段决策:

1. **Self-Sufficiency Check**: 当前消息是否已经足够完成任务。
2. **Dependency Detection**: 当前消息是否显式或隐式依赖历史。
3. **Task Boundary Decision**: 是新任务、继续任务、相关任务，还是歧义任务。
4. **Context Need Classification**: 需要哪类上下文。
5. **Scoped Retrieval**: 只在允许范围内检索。
6. **Evidence Validation**: 检索到的上下文是否真的对当前任务有证据价值。
7. **Context Assembly**: 组装最终 prompt，并记录为什么选择这些上下文。

这样可以避免“同领域但不相关”的错误召回。

### 创新 7: 级联式上下文需求路由器，而不是大量人工规则

多阶段决策不应该实现成大量人工 if-else，也不应该每步都调用大模型。更合理的是:

```text
少量高精度规则早退
  -> 轻量上下文需求分类器
  -> 小 LLM / 主 LLM 只处理歧义样本
  -> 低置信度时向用户澄清
```

规则层只做“明显情况”的判断，不负责完整语义理解。例如:

- 明确指代词: “刚才/上一个/继续/照那个格式”
- 明确新任务标记: “另一个问题/新问题/换个话题”
- 明显完整题面模式: 数学题、代码报错、翻译句子、独立问答
- 明显工具状态词: “取消/修改/刚订的/那个日历/那份文件”

真正的“是否自足”主要由轻量分类器或蒸馏模型判断，而不是靠手写规则穷举。

## 3. 系统设计

### 3.1 模块

```text
聊天适配层
  -> 自足性判断器
  -> 历史依赖判断器
  -> 任务边界检测器
  -> 任务上下文存储
  -> 记忆相关性过滤器
  -> 上下文组装器
  -> 工具/Skill 候选过滤器
  -> 基础 Agent 运行时
  -> 轨迹日志记录器
```

### 3.2 总体决策流程

```text
User Message
  -> Step 1: Self-Sufficiency Check
       - sufficient: answer with minimal context
       - insufficient: continue
  -> Step 2: Dependency Detection
       - explicit dependency: locate referenced task/context
       - implicit dependency: classify missing information
       - no dependency: isolate as new/standalone task
  -> Step 3: Task Boundary Decision
       - new_task / continue_task / related_task / ambiguous
  -> Step 4: Context Need Classification
       - no_context / task_local / related_summary / global_profile / tool_state / clarification
  -> Step 5: Scoped Retrieval
       - retrieve only from allowed stores
  -> Step 6: Evidence Validation
       - keep only context that is necessary and non-conflicting
  -> Step 7: Agent Execution
```

关键原则:

- 默认不检索，除非当前消息需要历史才能正确完成。
- 同领域不等于同任务。
- 相似不等于相关。
- 旧上下文必须通过“证据价值”验证才能进入 prompt。
- 如果缺失信息无法从可信上下文确定，优先向用户澄清。

### 3.3 自足性判断器

自足性判断器先回答一个问题:

> 不看任何历史，仅凭当前消息，agent 是否已经可以给出正确且完整的回答？

输出:

```json
{
  "self_sufficient": true,
  "missing_info": [],
  "needs_history": false,
  "risk_if_using_history": "high | medium | low",
  "reason": "当前问题包含完整题面，不需要引用上一题。"
}
```

判断标准:

| 类型 | 是否需要历史 | 示例 |
| --- | --- | --- |
| 完整独立问题 | 否 | “解方程 x^2 - 5x + 6 = 0” |
| 明确引用前文 | 是 | “用刚才的方法再做一遍” |
| 缺少对象 | 是/澄清 | “把它改成正式一点” |
| 需要用户长期偏好 | 可能 | “给我推荐餐厅”可能需要过敏/预算/城市偏好 |
| 新实体新目标 | 通常否 | “再帮我比较北京和上海哪个适合 AI 工作” |
| 工具状态修改 | 是 | “把明天下午 3 点那个会议改到 4 点” |

这个模块是本方案区别于简单 retrieval 的关键。

实现上，自足性判断器分三档:

| 档位 | 决策者 | 作用 | 示例 |
| --- | --- | --- | --- |
| 高精度规则 | 少量人工规则 | 只处理极明显的自足/依赖样本 | “继续刚才那个”明显依赖；完整方程题明显自足 |
| 轻量分类器 | 小模型 / encoder / 蒸馏 LLM | 处理大多数普通消息 | 判断“帮我写一封邮件”是否缺少对象、收件人、语气等信息 |
| LLM judge / 澄清 | 小 LLM 或主 LLM | 只处理低置信度样本 | “按之前那个来”但候选任务多个 |

因此这里不是要求人工设计大量规则。规则只承担 early exit，覆盖率可以不高，但精度要高。

#### 为什么仅靠规则不够

仅靠规则不能可靠判断自足性，因为自足性依赖语义和任务要求:

- “帮我写一封邮件”是否自足，取决于是否需要收件人、主题、目的、语气。
- “这个方案再优化一下”需要知道“这个方案”是什么。
- “再来一个类似的”需要上一个任务。
- “解这个方程 x^2 - 5x + 6 = 0”虽然有“这个”，但题面完整，通常自足。

所以本方案不是“规则判断自足性”，而是:

```text
规则只判断少量确定样本；
轻量模型负责主要自足性分类；
LLM 只处理歧义样本；
低置信度时不盲检索，而是澄清。
```

#### 轻量分类器怎么来

不需要一开始人工标很多数据，可以用三阶段:

1. **弱监督构造数据**: 从公开 benchmark 的任务字段、turn 结构、reference 词、artifact 依赖中自动生成标签。
2. **LLM 标注少量困难样本**: 用强模型给 sampled sessions 标注 self_sufficient / need_context / ambiguous。
3. **蒸馏小模型**: 训练或 few-shot 一个轻量分类器，输出 `context_need` 和置信度。

分类标签:

```text
no_context
task_local
related_summary
global_profile
project_memory
tool_state
clarification
```

训练/评估指标:

- self-sufficiency accuracy
- need-context recall
- unnecessary retrieval rate
- missed-context rate
- clarification precision
- downstream benchmark score

### 3.4 历史依赖判断器

如果当前消息不自足，进一步判断依赖类型:

| 依赖类型 | 说明 | 上下文来源 |
| --- | --- | --- |
| 显式指代依赖 | “这个/上一个/刚才/继续/照那个格式” | 最近活跃任务或需要澄清 |
| 产物依赖 | “修改这份表格/继续写刚才的文档” | task artifact store |
| 工具状态依赖 | “取消刚才订的票/改那个日历” | task-local tool state |
| 用户画像依赖 | “按我的口味推荐” | global profile memory |
| 领域知识依赖 | “根据我们项目之前的设定” | project memory / related task summary |
| 无依赖但信息不足 | “帮我规划一下”但没有城市/时间/预算 | ask clarification |

只有确定依赖类型后，才允许进入对应存储检索。

### 3.5 任务边界检测器

输入:

- 当前用户消息
- 活跃任务摘要
- 最近若干轮对话
- 可选: embedding、分类器、LLM 判别器

输出:

```json
{
  "decision": "continue_task | new_task | related_task | ambiguous",
  "task_id": "...",
  "confidence": 0.0,
  "reason": "...",
  "needs_clarification": false
}
```

判断策略:

1. 明确引用 “继续/刚才/上一个/基于这个” -> continue 或 related。
2. domain、entity、tool set 强变化 -> new_task。
3. 同一 domain 但 entity/goal 不同 -> new_task 或 related。
4. 指代不清 -> ambiguous，优先澄清。
5. 数学、代码、客服订单等局部变量密集任务默认隔离。

### 3.6 上下文选择策略

| 策略 | 可见上下文 |
| --- | --- |
| Full Session | 全部 session 历史 |
| Recent-N | 最近 N 轮 |
| Retrieval | 从全 session 检索 top-k 相似历史/记忆 |
| Task-Scoped | 当前任务历史 + 当前任务摘要 |
| Task+Related Summary | 当前任务 + 相关旧任务摘要 |
| Task+Global Memory Gate | 当前任务 + 相关全局用户记忆 |
| Task+Tool Filter | 当前任务 + 过滤后的 skill/tool 元数据 |

### 3.7 上下文需求分类

新增一个中间标签，避免“只要相似就检索”:

| Context Need | 含义 | 行为 |
| --- | --- | --- |
| no_context | 当前消息自足 | 不检索历史，只给最小系统上下文 |
| task_local | 明确继续当前任务 | 只取当前 task turns / artifacts / tool state |
| related_summary | 相关旧任务可提供背景，但不需要 raw turns | 只取摘要，不取完整历史 |
| global_profile | 需要长期用户偏好/事实 | 通过 relevance gate 取用户记忆 |
| project_memory | 需要项目长期背景 | 检索项目记忆 |
| tool_state | 需要修改或查询已有工具状态 | 读取 task-local 或 confirmed global tool state |
| clarification | 上下文不足且无法可靠确定 | 问用户澄清 |

### 3.8 Memory 分层

| 记忆类型 | 是否跨任务 | 示例 |
| --- | --- | --- |
| 任务局部工作记忆 | 否 | 当前数学题变量、订单号、临时文件路径 |
| 任务摘要 | 条件跨任务 | 已完成任务摘要、产物状态 |
| 用户画像记忆 | 是，但需相关性过滤 | 过敏、偏好、长期项目 |
| 工具状态记忆 | 通常任务局部 | 日历事件 ID、购物车状态 |
| Skill 记忆 | 跨任务，但只暴露元数据 | 已安装 skill 描述、触发条件 |

### 3.9 Skill/工具候选过滤器

输入:

- 任务类型
- 用户意图
- 任务摘要
- skill/tool 元数据

输出:

- 允许的工具
- 被抑制的工具
- 原因

规则:

1. 对高风险 tool 做更严格过滤。
2. 旧任务用过的工具不自动进入当前任务。
3. 当前任务无关 skill 不进入 system prompt。
4. 如果 router 置信度低，保留少量通用工具，而不是暴露全量工具。

### 3.10 证据验证器

检索到历史后，还要判断它能否进入最终 prompt。

验证问题:

1. 这段历史是否回答了当前缺失信息？
2. 这段历史是否和当前消息实体一致？
3. 这段历史是否来自同一 task 或被明确引用？
4. 如果它是用户偏好，是否是长期偏好而不是临时约束？
5. 如果它是工具状态，是否仍然有效？
6. 如果纳入它，是否可能改变当前独立问题的语义？

输出:

```json
{
  "context_id": "...",
  "admit": false,
  "reason": "同为数学问题，但变量和题面独立，旧题上下文无证据价值。",
  "conflict_risk": "high"
}
```

这样可以解决“同方向但不相关”的历史污染。

## 4. 技术策略表

| 策略 | 实现难度 | 预期收益 | 风险 | 优先级 |
| --- | --- | --- | --- | --- |
| 自足性判断器 | 低-中 | 避免不必要检索，降低污染和成本 | 误判自足会漏上下文 | P0 |
| 级联式上下文需求路由器 | 中 | 用低成本方式接近 LLM router 效果 | 需要校准置信度 | P0 |
| 历史依赖类型分类 | 中 | 精确选择检索范围 | 依赖类型边界需要定义 | P0 |
| 规则 + LLM 混合任务边界检测器 | 中 | 快速可用，解释性强 | LLM 判别成本 | P0 |
| 任务上下文存储 | 低 | 实验必需 | 数据结构设计要稳定 | P0 |
| 任务感知检索过滤 | 中 | 降低错误记忆召回 | 可能漏掉相关记忆 | P0 |
| 证据验证器 | 中 | 避免语义相似但任务错误的上下文进入 prompt | 多一次判别成本 | P0 |
| Skill/tool 候选过滤 | 中 | 降低错误 skill/tool 激活 | 可能误杀工具 | P0 |
| 任务摘要归档 | 中 | 降低 token 成本 | 摘要丢信息 | P1 |
| 歧义澄清机制 | 低 | 降低错误任务归属 | 可能增加轮数 | P1 |
| 学习式边界分类器 | 高 | 降低 LLM 成本 | 需要标注数据 | P2 |
| 基于反馈/RL 的记忆策略 | 高 | 长期优化 | 实验复杂 | P3 |

## 5. 实验总表

| 实验 | Benchmark | 数据规模 | 对照策略 | 指标 | 目标 |
| --- | --- | --- | --- | --- | --- |
| E1 通用 agent 能力 | GAIA-Val-Text / GAIA-Val | 103 / 完整验证集 | Full、Recent-N、Retrieval、Task-Scoped | accuracy、avg@3、成本、工具调用数 | 证明不损害主流 agent 能力 |
| E2 长 agentic instruction | AgentIF | 707 条指令 | Full、Recent-N、Task-Scoped、Task+Tool Filter | CSR、ISR、约束类型得分 | 证明工具规格/条件约束污染下降 |
| E3 多轮工具状态 | tau2/tau3 | retail/airline/telecom 子集 | Full、Recent-N、Task-Scoped | Pass^1、Pass^k、最终状态、错误工具率 | 证明状态型交互可靠性提升 |
| E4 长期记忆 | LongMemEval-S/M | 官方划分 | 全历史检索、embedding 检索、任务感知检索 | QA accuracy、recall@5/10、更新/时间/abstention | 证明不是简单丢历史 |
| E5 日常用户任务 | AgentIF-OneDay | 104 个任务，767 个评分点 | Full、Task-Scoped、Task+Summary | rubric score、评分点准确率 | 证明贴近日常用户价值 |
| E6 Router 压力测试 | BFCL + AgentIF 工具约束 + tau tools | 选择相关类别 | Full、Task+Tool Filter | 工具准确率、错误工具、错误参数、无需工具准确率 | 证明 skill/tool 路由隔离 |
| E7 泛化实验 | BrowseComp / xBench / WebArena | 子集 | baseline vs 最优方法 | accuracy / task success | 证明不是只对某类任务有效 |
| E8 上下文需求判断 | AgentIF + LongMemEval + GAIA 派生样本 | sampled | Always-Retrieve、Need-Gated、Oracle Need | need accuracy、unnecessary retrieval rate、missed-context rate | 证明不是每条消息都该检索 |
| E9 路由器成本实验 | 所有主 benchmark 的 sampled subset | sampled | Rule-only、Small Classifier、Always LLM Router、Cascaded Router | LLM 调用率、token、延迟、need accuracy、下游分数 | 证明不用大量规则和每步 LLM 也能有效 |

## 5.1 上下文需求分类器的数据来源

| 数据来源 | 如何产生标签 | 可标注内容 |
| --- | --- | --- |
| AgentIF | 每条 instruction 本身是完整任务；工具/条件约束可作为 need type | no_context、tool/spec dependency、clarification |
| LongMemEval | 问题有 answer location / memory evidence | global/profile memory、multi-session dependency、temporal dependency |
| tau2/tau3 | 每个任务有 domain state、tool state、user simulator turns | task_local、tool_state、clarification |
| GAIA | 独立任务默认 no_context；需要文件/网页/工具的任务可标注 tool/project evidence | no_context、tool evidence、artifact evidence |
| AgentIF-OneDay | 任务包含附件、迭代修改、latent instruction | artifact dependency、iterative refinement、latent rule |
| 跨任务组合样本 | 将公开 benchmark 任务按 session 串联，自动知道哪些前序任务无关 | no_context、unnecessary retrieval negative examples |
| 少量人工/LLM 标注 | 对歧义样本补标 | ambiguous、related_summary、clarification |

核心不是人工写大量规则，而是从公开 benchmark 中构造 `当前消息 -> 是否需要上下文 -> 需要哪类上下文` 的监督信号。

## 6. 消融实验

| 消融 | 说明 | 要回答的问题 |
| --- | --- | --- |
| Full Session | 全历史输入 | 聊天软件原始做法有多差 |
| Recent-N | 最近 N turns | 简单窗口是否足够 |
| Retrieval-Only | 全 session 检索 top-k | 检索是否会召回语义相似但任务错误的信息 |
| Boundary Only | 只做任务分割，不做 memory/tool filter | task 边界本身贡献 |
| Boundary + Retrieval | 只在 task 内或 related tasks 内检索 | task-aware retrieval 贡献 |
| Boundary + Summary | 用摘要替代旧 task raw turns | token 成本与精度权衡 |
| Boundary + Tool Filter | 加 tool/skill candidate filter | router 误激活是否下降 |
| Oracle Boundary | 用 benchmark/task id 作为边界 | 上界是多少，boundary detector 误差影响多大 |
| No Global Memory | 禁用用户长期记忆 | 证明长期记忆仍必要 |
| Global Memory Ungated | 全局记忆全进 | 证明 relevance gate 必要 |
| Always Retrieve | 每条消息都检索历史 | 证明无条件检索会带来污染和成本 |
| Need Gate Only | 只判断是否需要上下文，不做 task boundary | 自足性判断本身贡献 |
| Oracle Need | 人工/规则给定是否需要上下文 | 上下文需求判断上界 |
| No Evidence Validation | 检索后直接塞进 prompt | 证明证据验证器必要 |

## 7. 关键指标

### 公开 benchmark 原生指标

- GAIA: accuracy, level-wise accuracy。
- AgentIF: CSR, ISR。
- tau2/tau3: Pass^1, Pass^k, final state correctness。
- LongMemEval: QA accuracy, recall@k, category accuracy。
- AgentIF-OneDay: 实例级 rubric 分数、评分点准确率。
- WebArena: task success rate。
- BFCL: overall accuracy, multi-turn accuracy, irrelevance detection, executable/AST checks。

### 本方法诊断指标

- 任务边界准确率。
- 自足性判断准确率。
- 上下文需求分类准确率。
- 不必要检索率。
- 必要上下文漏检率。
- 歧义澄清率。
- 上下文污染率。
- 错误记忆召回率。
- 相关记忆漏召回率。
- 错误 tool/skill 激活率。
- 工具参数错误率。
- 被选择上下文 token 数。
- 单任务成本。
- 多次运行方差。

## 8. 实验执行优先级

### P0: 两周内可跑通

1. LightAgent wrapper 冒烟测试。
2. AgentIF small subset。
3. LongMemEval-S small subset。
4. 实现统一日志和 context policy。

目标:

- 快速判断任务级上下文隔离是否有明显信号。

### P1: 主结果

1. MiroFlow + GAIA-Val-Text。
2. AgentIF full。
3. LongMemEval-S/M。
4. tau2 telecom subset。

目标:

- 形成可写论文的主表。

### P2: 强化结果

1. AgentIF-OneDay full。
2. tau2/tau3 full selected domains。
3. BrowseComp / xBench-DeepSearch subset。

目标:

- 增强普通用户场景和 deep research agent 场景说服力。

### P3: 泛化补充

1. WebArena。
2. SWE-Bench Lite。
3. MultiChallenge / Multi-IF。

目标:

- 如果投稿目标需要更广泛 agent 能力，再补。

## 9. 论文故事线

### 问题

通用 agent 越来越多地通过长期存在的聊天界面使用。但聊天 session 只是传输层容器，不等于任务级推理上下文。如果把整个 session 都当作上下文，就会引入任务污染、过时记忆和错误工具/skill 路由。

### 方法

任务级上下文隔离:

1. 检测任务边界。
2. 维护任务局部工作记忆。
3. 只检索任务相关记忆。
4. 按任务范围过滤 skill/tool 候选。
5. 将完成任务归档为摘要。

### 贡献

1. 提出聊天式通用 agent 的任务级上下文隔离问题定义。
2. 提出一个可插拔的上下文策略层，可接入 MiroFlow / LightAgent / OpenHands。
3. 基于公开 benchmark 构造跨任务压力测试，不修改 benchmark 答案和评分器。
4. 在 AgentIF、tau2/tau3、LongMemEval、GAIA、AgentIF-OneDay 上验证指令、工具、记忆、日常任务维度。

## 10. 可能被质疑的点与应对

| 质疑 | 应对 |
| --- | --- |
| 这不就是 retrieval/memory 吗 | 强调我们先做任务边界，再做 retrieval；对照 Retrieval-Only |
| 这不就是 summarization 吗 | 对照 Summary-Only，证明隔离比压缩更关键 |
| benchmark 原生不是跨任务 session | 明确为 benchmark-derived stress setting，答案和评分器不变 |
| boundary detector 错误会拖累系统 | 做 Oracle Boundary 上界和边界检测错误分析 |
| 会不会漏掉相关长期记忆 | 做 LongMemEval 和 Global Memory Gate 消融 |
| tool filter 会误杀工具 | 报告 false negative tool rate，设计 fallback |
| 成本会增加 | 报告 token/cost/latency，边界检测可用小模型或规则 |

## 11. 当前最需要优化的点

1. **任务边界检测定义要更严格**: 需要明确 new/continue/related/ambiguous 四类的标注标准。
2. **基于 benchmark 的跨任务压力测试要设计得可辩护**: 不能像自造 toy，需要从公开 benchmark 自动组合。
3. **选择一个主 baseline 不要摇摆**: 建议主线 MiroFlow，LightAgent 只做 prototype。
4. **先做 AgentIF + LongMemEval**: 这两个最直接验证 instruction pollution 和 memory pollution。
5. **尽早做 Oracle Boundary**: 如果 oracle 都没提升，方法不成立；如果 oracle 明显提升，说明 boundary detector 是关键工程问题。
