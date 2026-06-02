# 新对话交接文档: Task-Scoped Context Isolation Agent

日期: 2026-06-02

这份文档的目标是: **之后新开对话时，任何 assistant 只要读这份文档，就能知道要实现什么、为什么做、从哪里开始、每一步该产出什么。**

## 1. 项目一句话

我们要实现一个 **任务级上下文隔离层**，用于解决普通用户在一个长聊天 session 中混杂多个任务时出现的上下文污染、错误记忆召回、错误工具/skill 路由问题。

主实现不再绑定 MiroFlow。新的主线是:

```text
LightAgent 或 LangGraph 轻量 agent runtime
  + Task-Scoped Context Isolation
  + AgentIF / MultiChallenge / BFCL / LongMemEval-LoCoMo 等公开 benchmark
```

MiroFlow 只保留为强系统参考和可选集成目标。

## 2. 为什么从 MiroFlow 调整

前期已经下载并测试过 MiroFlow。结论:

- MiroFlow 是 deep-research agent，适合展示强搜索/研究能力。
- 完整 baseline 需要搜索 API、网页读取 API、代码沙箱、reasoning LLM 等多种外部服务。
- 单题运行会触发多 worker、多轮 summary、大量工具调用，成本和时间很高。
- 这不利于验证本项目真正的创新: 当前消息是否需要历史、需要哪段历史、是否应过滤工具/skill。

因此:

```text
MiroFlow = paper-level strong reference / optional integration
LightAgent/LangGraph = main implementation baseline
```

## 3. 不要做什么

非常重要:

1. 不要再把 MiroFlow 作为主实现 baseline。
2. 不要自造 toy benchmark 作为主实验。
3. 不要把“同领域”直接当成“同任务”。
4. 不要每条消息都默认检索历史。
5. 不要每一步都调用大模型做 router。
6. 不要修改公开 benchmark 的答案和评分器。
7. 不要把 deep-research 工具链复现当成本项目的核心贡献。

## 4. 主 baseline

### Primary: LightAgent

用途:

- 主工程实现。
- 快速接入 history/memory/skill router。
- 低成本跑 ablation。

选择原因:

- 轻量，易改。
- 更贴近普通用户聊天式 agent。
- 比 MiroFlow 更适合研究“session 中多任务混杂”的问题。

### Secondary: LangGraph

用途:

- 如果 LightAgent 不够规范，用 LangGraph 构造固定 agent runtime。
- 适合状态机、memory、tool routing 的干净 prototype。

### Reference: MiroFlow

用途:

- 引用官方 reported scores。
- 说明强 deep-research agent 的工具链和成本问题。
- 最后有余力再做 optional integration。

## 5. 核心研究问题

普通聊天软件里的一个 chat session 往往包含多个任务:

- 生活咨询
- 数学题
- 代码问题
- 写作任务
- 搜索任务
- 工具调用
- 多个不同 skill 的调用

如果 agent 直接把整个 session 当上下文，会出现:

- 旧任务变量污染新任务。
- 旧 skill 指令影响新任务。
- 旧工具状态被误用。
- 语义相似但任务无关的历史被错误召回。
- token 成本随 session 增长不断升高。

本项目要验证:

> 显式 task-level context isolation 是否能减少污染、降低成本、提升或保持公开 agent benchmark 表现。

## 6. 核心方法

方法名称暂定:

```text
Task-Scoped Context Isolation
```

关键机制:

1. **自足性判断**  
   当前消息是否不看历史也能完成。

2. **历史依赖判断**  
   当前消息是否依赖“刚才/上一个/那个文件/之前的格式/工具状态”等。

3. **任务边界检测**  
   判断是新任务、继续任务、相关任务、还是歧义任务。

4. **上下文需求分类**  
   判断需要哪类上下文: no_context、task_local、related_summary、global_profile、project_memory、tool_state、clarification。

5. **范围受控检索**  
   只在允许的 task/memory/tool state 范围内检索。

6. **证据验证**  
   检索到的历史必须证明对当前任务有用，否则不能进入 prompt。

7. **工具/skill 候选过滤**  
   当前任务无关的 tool/skill 不进入 agent 可见候选集。

## 7. 关键设计原则

### 7.1 同领域不等于同任务

例子:

```text
上一轮: 求解 2x + 3 = 11
当前轮: 求解 x^2 - 5x + 6 = 0
```

两者都属于数学，但当前题题面完整，默认不需要上一题上下文。

### 7.2 相似不等于相关

embedding 相似度高的历史不一定应该进入当前 prompt。进入 prompt 前要做证据验证。

### 7.3 默认不检索

流程应是:

```text
先判断是否需要上下文
如果不需要: 不检索
如果需要: 判断需要哪类上下文
再做范围受控检索
```

### 7.4 多阶段逻辑不等于多次大模型调用

不要每一步都调用 LLM。正确实现是级联式:

```text
少量高精度规则早退
  -> 轻量分类器
  -> LLM judge 只处理歧义样本
  -> 低置信度时向用户澄清
```

## 8. 目标代码结构

预计最终目录:

```text
agent-context-isolation/
  third_party/
    LightAgent/
    MiroFlow/
  src/
    context_isolation/
      __init__.py
      schema.py
      store.py
      gates.py
      boundary.py
      retrieval.py
      evidence.py
      tool_filter.py
      assembler.py
      policy.py
      trace.py
      wrappers/
        lightagent.py
        langgraph.py
        miroflow_optional.py
  experiments/
    agentif/
    bfcl/
    longmemeval/
    tau_bench/
    toolsandbox/
    gaia_optional/
  scripts/
    run_benchmark.py
    build_stress_sessions.py
    train_context_need_classifier.py
    analyze_errors.py
  configs/
    policies/
    benchmarks/
  runs/
  results/
```

## 9. 必须实现的核心接口

### 9.1 ContextPolicy

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

### 9.2 ContextDecision

```python
@dataclass
class ContextDecision:
    self_sufficient: bool
    need_type: str
    boundary: str
    task_id: str | None
    confidence: float
    selected_turn_ids: list[str]
    selected_memory_ids: list[str]
    selected_tools: list[str]
    suppressed_tools: list[str]
    reason: str
```

### 9.3 SelectedContext

```python
@dataclass
class SelectedContext:
    system_addendum: str
    messages: list[dict]
    memories: list[dict]
    tools: list[dict]
    trace: dict
```

## 10. 必须支持的策略

| 策略名 | 含义 | 用途 |
| --- | --- | --- |
| full_session | 全部聊天历史进入 agent | 原始聊天软件 baseline |
| recent_n | 最近 N 轮进入 agent | 简单工程 baseline |
| retrieval_only | 对全 session 检索 top-k | 常见 memory baseline |
| need_gated | 先判断是否需要上下文，再检索 | 验证“不是每条都检索” |
| task_scoped | 只给当前任务上下文 | 核心方法 |
| task_scoped_tool_filter | 任务上下文 + 工具/skill 候选过滤 | 完整方法 |
| oracle_boundary | 用真实 task id 边界 | 上界分析 |

## 11. 主 benchmark

优先使用:

1. AgentIF
2. MultiChallenge
3. BFCL multi-turn
4. LongMemEval / LoCoMo
5. tau-bench / tau2-bench
6. ToolSandbox

补充使用:

1. STATE-Bench 小样本
2. GAIA text-only 小样本
3. MiroFlow/HLE smoke
4. BrowseComp / xBench 预算充足且需要 deep-search 泛化时再做

## 12. 实施阶段总览

| 阶段 | 目标 | 主要产物 |
| --- | --- | --- |
| Phase 0 | baseline 决策与仓库准备 | LightAgent/LangGraph 主线，MiroFlow 降级为参考 |
| Phase 1 | 实现上下文隔离层基础结构 | `schema.py`, `store.py`, `policy.py` |
| Phase 2 | 实现自足性判断和级联 router | `gates.py`, `boundary.py`, `evidence.py` |
| Phase 3 | 接入轻量 agent runtime | `wrappers/lightagent.py`, `wrappers/langgraph.py` |
| Phase 4 | 接入公开 benchmark | AgentIF, MultiChallenge, BFCL, LongMemEval/LoCoMo adapters |
| Phase 5 | 跑主实验和消融 | result tables, trace logs |
| Phase 6 | 训练轻量分类器 | context need classifier |
| Phase 7 | 论文级整理 | tables, plots, reproducibility package |
