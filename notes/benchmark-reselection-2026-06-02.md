# Benchmark 重新选择决策记录

日期: 2026-06-02。

## 背景

最初计划围绕 MiroFlow 复现 HLE/GAIA/BrowseComp/xBench-DeepSearch 等 deep research benchmark。实际测试后发现该路线和当前研究问题不完全匹配:

1. MiroFlow 是深度研究型多 worker agent，工具链复杂。
2. 运行强依赖外部搜索、网页读取、代码 sandbox 等服务。
3. 单题 token 和耗时很高，不适合作为早期方法验证 baseline。
4. 当前研究核心不是搜索能力，而是聊天 session 中的上下文隔离、记忆检索门控和 skill/tool router。

因此决定更换 benchmark 主线。

## 新主线

实现 baseline:

- 主线: LightAgent。
- 备选: LangGraph。
- 参考: MiroFlow。

实验 benchmark:

| 层级 | Benchmark | 作用 |
| --- | --- | --- |
| P0 | AgentIF | 旧 instruction/constraint 污染 |
| P0 | MultiChallenge | 多轮聊天上下文漂移 |
| P0 | BFCL multi-turn | skill/tool routing |
| P0 | LongMemEval / LoCoMo | memory gate 和 task-scoped retrieval |
| P1 | tau-bench / tau2 | 端到端 user-agent-tool 状态任务 |
| P1 | ToolSandbox | 状态化工具执行污染 |
| P1 | STATE-Bench | 企业 workflow、memory、skills |
| P2 | GAIA/MiroFlow/HLE | 只做参考或 smoke |

## 为什么这些更适合

### AgentIF

它直接测试长指令、多约束和工具约束。如果前一个任务要求“输出 JSON”，后一个任务没有这个要求，full session 很容易误继承旧约束。task-scoped context 应该减少这种污染。

### MultiChallenge

它关注真实多轮对话中的 instruction retention、inference memory、self-coherence 和 version editing。它适合观察普通聊天 session 中什么时候应该保留前文，什么时候不应该保留。

### BFCL multi-turn

它是 function calling/tool calling 评测。用户担心 skill 多了 router 难做，BFCL 可以直接统计 wrong tool、wrong argument 和 irrelevant tool call。

### LongMemEval / LoCoMo

它们是长期记忆 benchmark，适合验证“当前消息是否自足”这个前置 gate。方法不应该每条消息都检索历史，因为自足问题检索旧记忆可能反而污染答案。

### tau2 / ToolSandbox / STATE-Bench

这些更接近真实 agent 环境，可作为 P1 证明，但接入和成本更高，所以不放在第一阶段。

## 不再主推的内容

### MiroFlow/HLE

保留为参考，不再作为主线。之前 smoke 已证明运行成本和外部依赖过高，且 HLE 更偏高难知识/推理，不直接测试上下文隔离。

### GAIA

GAIA 是通用 agent benchmark，但它的主要价值是综合工具能力，不是上下文边界。保留 text-only small 做参考即可。

### BrowseComp/xBench-DeepSearch

这些适合 deep search agent，不适合当前阶段。

## 之后执行顺序

1. 检查 LightAgent 代码结构，确定 history、memory、tool/skill 调用入口。
2. 实现 context policy wrapper。
3. 先做 AgentIF adapter。
4. 再做 BFCL multi-turn adapter。
5. 再做 LongMemEval/LoCoMo adapter。
6. 三个 P0 跑通后，再决定是否做 MultiChallenge。
7. P0 有效果后，再做 tau2 或 ToolSandbox 小样本。

## 成本控制

默认不全量跑。

第一轮每个 benchmark:

- 5 条数据加载和 scorer 调试。
- 20 条 smoke。
- 输出 token、耗时、错误类型。

只有 smoke 证明方法有价值，才扩大到 100 到 300 条小规模正式实验。

## 当前结论

这个 benchmark 选择更贴近论文要证明的核心:

- full session 会污染当前任务。
- recent-N 不能解决同领域无关任务混淆。
- always retrieval 会带来不必要历史和成本。
- task-scoped context 能降低污染。
- task-scoped tool filtering 能降低 skill/router 错误。
