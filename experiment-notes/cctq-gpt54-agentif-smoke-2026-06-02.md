# cctq gpt-5.4 + LightAgent + AgentIF 小样本 Smoke

日期: 2026-06-02。

## 配置

API:

```text
base_url: https://www.cctq.ai/v1
model: gpt-5.4
接口: /v1/chat/completions
```

说明:

- API key 只通过进程环境变量传入，没有写入配置文件。
- 使用已有 conda 环境 `miroflow-py312`。
- 没有调用 MiroFlow。
- 没有使用外部搜索、浏览器、E2B、Jina、Serper 等工具。

## API Smoke

脚本:

```text
/22liushoulong/agent/agent-context-isolation/implementation-notes/cctq_api_smoke.py
```

结果:

```text
content: OK
usage: prompt_tokens=21, completion_tokens=5, total_tokens=26
```

结论:

- `https://www.cctq.ai/v1` 的 OpenAI-compatible `chat.completions` 可用。
- `gpt-5.4` 可调用。

## AgentIF 小样本

数据:

```text
benchmark: AgentIF
source: THU-KEG/AgentIF
file: /22liushoulong/agent/agent-context-isolation/data/agentif/eval.json
样本数: 707
本次抽样: 3 条最短 prompt 样本
```

Runner:

```text
/22liushoulong/agent/agent-context-isolation/experiments/run_agentif_cctq_smoke.py
```

输出目录:

```text
/22liushoulong/agent/agent-context-isolation/experiments/runs/agentif_cctq_gpt54_smoke/
```

运行命令:

```bash
CCTQ_API_KEY=... CCTQ_BASE_URL=https://www.cctq.ai/v1 CCTQ_MODEL=gpt-5.4 \
conda run -n miroflow-py312 python \
/22liushoulong/agent/agent-context-isolation/experiments/run_agentif_cctq_smoke.py
```

## 结果

| idx | sample id | 约束数 | query chars | 输出 | 初步判断 |
| --- | --- | ---: | ---: | --- | --- |
| 619 | `agentif:2c339f16738ac3825cd5d9b6e6b0ac2f39f1091d` | 2 | 2289 | `finance` | 符合只能输出三选一的格式约束 |
| 512 | `agentif:63d5fe9b79641db44f8390fee20b79a2901be6f2` | 2 | 2309 | `products` | 符合只能输出三选一的格式约束 |
| 484 | `agentif:953b68e7a8836faea411c5665340585719eb0b52` | 2 | 2321 | `support` | 符合只能输出三选一的格式约束 |

运行无 API 错误。

## 重要限制

这次不是正式 benchmark 结果。

原因:

1. 只跑了 3 条短样本。
2. 还没有接 AgentIF 官方 CSR/ISR scorer。
3. 当前只是 LightAgent 原始 baseline smoke，没有接 `ContextPolicy`。
4. 当前没有构造 stress session，因此还没有测试上下文污染。
5. LightAgent 非流式路径暂未保存 token usage，只有 API smoke 的 usage 被记录。

## 当前结论

可以继续用这个 API 做后续小样本实验。

下一步应做:

1. Phase 1 实现 `ContextPolicy`。
2. Phase 3 接 LightAgent wrapper。
3. Phase 4 接 AgentIF 官方 scorer。
4. 对同一批 AgentIF 样本比较:
   - `full_session`
   - `recent_n`
   - `need_gated`
   - `task_scoped`
5. 再接 BFCL multi-turn 小样本，测试 tool/skill router。
