# AgentEVAL 下游攻击器接入（本平台）

对接上游仓库：[AgentEVAL-Risk-Tools](https://github.com/ThreeWater1037/AgentEVAL-Risk-Tools)

本目录是对现有 `rag_poison_platform` 的**薄封装**：不改原有 RAG / 推理链矩阵逻辑，只暴露 AgentEVAL 要求的 bundle → results 接口。

## 分工

```text
AgentEVAL (上游)
  Tool1/Tool2 → execution_bundle.json
        ↓
rag_poison_platform/agenteval_executor  (本攻击器)
  setup → trigger → observe → cleanup → results.json
        ↓
agenteval import-results / POST /evaluations/{id}/results
```

## 当前支持的 attack_family

| attack_family | 后端 | 说明 |
|---|---|---|
| `rag_poisoning` | `minimal_http_rag` ingest + HTTP query | 写毒文档后触发 query |
| `search_narrative_poisoning` | 同上 | 外部叙事页当作 poison_doc |
| `planning_poisoning` | `agent_chain_poison`（默认）或 HTTP direct | 中间步骤 prompt 注入 |
| `prompt_context_injection` | 同上 | 直接拼进输入 / 链注入 |
| 其他 4 类 | 明确返回 `require_review` + `unsupported_family` | 不静默误路由 |

## 最小结果契约

每条结果必须有：

```json
{
  "case_id": "与 bundle 完全一致",
  "failure_stage": "attack_success|...|setup_failed",
  "metrics": {
    "real_attack_success": false,
    "latency_ms": 1234,
    "setup_ok": true,
    "cleanup_ok": true
  }
}
```

顶层：

```json
{
  "schema_version": "agenteval.results.v1",
  "evaluation_id": "...",
  "apply_feedback": true,
  "results": [ /* 覆盖全部 case_id，各一次 */ ]
}
```

`failure_stage` 含义见 [接入说明 §6.1](https://github.com/ThreeWater1037/AgentEVAL-Risk-Tools/blob/main/doc/接入说明.md)。

## 文件入口

| 路径 | 作用 |
|---|---|
| `agenteval_executor/execute.py` | 读 bundle、写 results、可选 POST |
| `agenteval_executor/runners.py` | 按 family 执行 |
| `runners/run_agenteval_bundle.py` | CLI |
| `examples/agenteval_sample_bundle.json` | 本地样例 bundle |

## 离线文件模式

1. 上游生成 bundle：

```powershell
agenteval run --input agent.json --out runs/team-agent --count 1 --llm off
```

2. 本平台执行：

```powershell
cd D:\AI\rag_poison_exp\rag_poison_platform

# 先 dry-run 校验结构（无需 Agent / API Key）
python -m runners.run_agenteval_bundle `
  --bundle examples\agenteval_sample_bundle.json `
  --dry-run `
  --out results\agenteval_results_dryrun.json

# 真实执行（RAG case 需 minimal_http_rag_agent 在 18100；planning case 需 DEEPSEEK_API_KEY）
python -m runners.run_agenteval_bundle `
  --bundle path\to\execution_bundle.json `
  --out results\agenteval_results.json
```

3. 回传上游：

```powershell
agenteval import-results `
  --analysis-dir runs\team-agent `
  --results results\agenteval_results.json
```

## HTTP API 模式

```powershell
# 1) 从 AgentEVAL API 取到的响应可直接当 --bundle（含 execution_bundle 字段也可）
# 2) 执行后自动 POST 回传
python -m runners.run_agenteval_bundle `
  --bundle path\to\evaluation_response.json `
  --out results\agenteval_results.json `
  --post http://127.0.0.1:8000
```

等价于：

`POST /api/v1/evaluations/{evaluation_id}/results`

## target 字段怎么填（给上游 / 本机 Agent）

对本平台自带 RAG：

```json
{
  "agent_ref": "minimal_http_rag_agent",
  "protocol": "http",
  "endpoint": "http://127.0.0.1:18100/query",
  "method": "POST",
  "request_template": {"question": "{{prompt}}", "top_k": 5},
  "response_key": "answer",
  "timeout_s": 90
}
```

对推理链内置后端：`protocol` 设为 `mock` / `builtin_chain`，或不填 `endpoint`，planning/prompt 类 case 会走 `AgentChainRunner`。

## 小改原则

- **未改** 原有 `run_poison_case_matrix` / `run_agent_chain_poison` 主实验路径。
- **新增** `agenteval_executor/` + 一个 CLI runner。
- 未支持的 family **显式** `require_review`，符合接入说明「不要静默交给错误执行器」。
