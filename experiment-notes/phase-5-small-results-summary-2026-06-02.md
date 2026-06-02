# Phase 5 小样本实验汇总

生成日期: 2026-06-02。

这份表只汇总当前已经落盘的小样本/烟测结果，用于判断实验链路是否跑通，以及下一步应优先补哪类实验。它还不能代表论文级最终结论。

| Benchmark | Run | Policy | Mode/Template | N | Score | Input Tokens Est | Notes |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| AgentIF | `agentif_baseline_20_cctq_gpt54` | `-` | `-` | 20 | 20/20 (100.0%) | - | - |
| AgentIF | `agentif_same_session_full_session_3_cctq_gpt54_compare` | `full_session` | `-` | 3 | 3/3 (100.0%) | 0.0048M | - |
| AgentIF | `agentif_same_session_recent_n_3_cctq_gpt54_compare` | `recent_n` | `-` | 3 | 3/3 (100.0%) | 0.0046M | - |
| AgentIF | `agentif_same_session_task_scoped_3_cctq_gpt54_compare` | `task_scoped` | `-` | 3 | 3/3 (100.0%) | 0.0015M | - |
| MATH | `math_algebra_baseline_10_cctq_gpt54` | `-` | `-` | 10 | - | - | - |
| MATH | `math_same_session_full_session_3_cctq_gpt54_compare` | `full_session` | `-` | 3 | 3/3 (100.0%) | 0.0008M | - |
| MATH | `math_same_session_recent_n_3_cctq_gpt54_compare` | `recent_n` | `-` | 3 | 3/3 (100.0%) | 0.0008M | - |
| MATH | `math_same_session_task_scoped_3_cctq_gpt54_compare` | `task_scoped` | `-` | 3 | 3/3 (100.0%) | 0.0003M | - |
| Mixed Session | `mixed_old_constraint_full_session_5_filtered_cctq_gpt54_compare` | `full_session` | `old_constraint_conflict` | 5 | 4/4 (100.0%) | 0.0128M | unnecessary context 4; forbidden inclusion 4 |
| Mixed Session | `mixed_old_constraint_recent_n_5_filtered_cctq_gpt54_compare` | `recent_n` | `old_constraint_conflict` | 5 | 4/4 (100.0%) | 0.0111M | unnecessary context 4; forbidden inclusion 4 |
| Mixed Session | `mixed_old_constraint_task_scoped_5_filtered_cctq_gpt54_compare` | `task_scoped` | `old_constraint_conflict` | 5 | 4/4 (100.0%) | 0.0053M | unnecessary context 0; forbidden inclusion 0 |
| BFCL | `bfcl_scorer_smoke` | `-` | `-` | 6 | 6/6 (100.0%) | - | - |
| BFCL | `bfcl_tool_stress_full_session_dryrun_v3` | `full_session` | `bfcl_multi_turn_base_tool_stress` | 3 | 1/3 (33.3%) | 0.0010M | unnecessary context 2; forbidden inclusion 2 |
| BFCL | `bfcl_tool_stress_recent_n_dryrun_v3` | `recent_n` | `bfcl_multi_turn_base_tool_stress` | 3 | 1/3 (33.3%) | 0.0010M | unnecessary context 2; forbidden inclusion 2 |
| BFCL | `bfcl_tool_stress_task_scoped_dryrun_v4` | `task_scoped_tool_filter` | `bfcl_multi_turn_base_tool_stress` | 3 | 3/3 (100.0%) | 0.0006M | unnecessary context 0; forbidden inclusion 0 |
| LongMemEval | `longmemeval_retrieval_oracle_smoke` | `-` | `oracle` | 5 | - | - | answer session hit 5/5; compression 0.0098 |
| LongMemEval | `longmemeval_retrieval_lexical_smoke` | `-` | `lexical` | 5 | - | - | answer session hit 4/5; compression 0.0282 |
| LongMemEval | `longmemeval_qa_oracle_3_cctq_gpt54` | `-` | `oracle` | 3 | 1/3 (33.3%) | 0.0046M | answer session hit 3/3; compression 0.0107 |
| LongMemEval | `longmemeval_qa_oracle_ranked_3_cctq_gpt54` | `-` | `oracle` | 3 | 3/3 (100.0%) | 0.0056M | answer session hit 3/3; compression 0.0132 |
| LongMemEval | `longmemeval_qa_lexical_3_turn20_cctq_gpt54` | `-` | `lexical` | 3 | 1/3 (33.3%) | 0.0341M | answer session hit 2/3; compression 0.0799 |
| LongMemEval | `longmemeval_retrieval_lexical_turn_weighted_smoke20` | `-` | `lexical_turn` | 20 | - | - | answer session hit 20/20; compression 0.03 |
| LongMemEval | `longmemeval_retrieval_lexical_turn_weighted_smoke100` | `-` | `lexical_turn` | 100 | - | - | answer session hit 94/100; compression 0.0316 |
| LongMemEval | `longmemeval_retrieval_lexical_adaptive_weighted_smoke100` | `-` | `lexical_adaptive` | 100 | - | - | answer session hit 97/100; compression 0.0679 |
| LongMemEval | `longmemeval_qa_lexical_turn_weighted_3_cctq_gpt54` | `-` | `lexical_turn` | 3 | 2/3 (66.7%) | 0.0112M | answer session hit 3/3; compression 0.0262 |
| LongMemEval | `longmemeval_qa_lexical_turn_weighted_prompt_3_cctq_gpt54` | `-` | `lexical_turn` | 3 | 3/3 (100.0%) | 0.0112M | answer session hit 3/3; compression 0.0262 |

## 当前判断

1. AgentIF、MATH、Mixed Session 主要验证同一 session 中的上下文隔离接口、need gate 和 task boundary 是否能稳定工作。
2. BFCL 已接入官方 scorer 的直接 checker，说明工具调用类 benchmark 的评分链路可以复用公开标准。
3. LongMemEval 的关键发现是: 只选中正确 session 还不够，session 内部 turn ranking 明显影响答案和 token 成本。
4. 当前最需要补的是非 oracle 的 LongMemEval 检索策略，以及更系统的同一 session 混合任务大样本协议。

## 下一步

1. 改进 LongMemEval lexical 检索: 从整段 session overlap 改为 turn-level max/mean + role/date/answer-like boost。
2. 对改进检索先跑 dry-run，再用 3 到 5 条真实模型调用验证是否超过旧 lexical。
3. 把混合 session 验证从手工模板扩展为可配置的 benchmark mixer，以 task 为单位打乱但保留可控冲突规则。
