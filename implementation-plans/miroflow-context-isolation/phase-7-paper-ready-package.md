# Phase 7: 论文级交付包

## 目标

把代码、实验、表格、图、复现脚本整理成论文投稿或技术报告可用的形式。

## 代码交付

```text
src/context_isolation/
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

## 结果表

必须有:

1. 主结果表。
2. 消融表。
3. 成本表。
4. router 准确率表。
5. 错误类型分析表。
6. benchmark coverage 表。

## 图

建议:

1. 系统架构图。
2. 级联式上下文需求路由流程图。
3. 不同策略 token 成本对比。
4. 不同策略错误工具率对比。
5. Oracle vs learned router gap。
6. 随 session 长度变化的性能曲线。

## 论文贡献表述

建议贡献:

1. 提出聊天式通用 agent 的任务级上下文隔离问题。
2. 提出级联式上下文需求路由器，先判断是否需要历史，再做范围受控检索。
3. 提出 task-scoped working memory 和 tool/skill candidate filtering。
4. 基于公开 benchmark 构造 cross-task stress setting，不修改官方评分器。
5. 在 AgentIF、BFCL multi-turn、LongMemEval、tau-bench/tau2、ToolSandbox 上验证。

## 风险检查

| 风险 | 检查方式 |
| --- | --- |
| 方法只是 retrieval | 必须有 Retrieval-Only 对照 |
| 方法只是 summarization | 必须有 Summary-Only 对照 |
| 手工规则过多 | 报告规则覆盖率和 classifier/LLM fallback |
| LLM router 太贵 | 报告 LLM judge 调用率和成本 |
| benchmark setting 被质疑 | 明确 benchmark-derived stress setting，不改答案和评分器 |
| 任务边界检测错 | 报告 Oracle Boundary 上界 |
| 漏掉长期记忆 | LongMemEval + global memory gate 消融 |
| tool filter 误杀 | 报告 false negative tool rate |
| baseline 过重 | 主实现使用 LightAgent/LangGraph，MiroFlow 只作为强参考 |

## 最终验收

- 所有实验可通过一条命令复现。
- 每个结果表对应一个固定 run config。
- 每个 benchmark 有 README。
- 每个策略有配置文件。
- 所有失败样本可追踪到 context decision trace。
