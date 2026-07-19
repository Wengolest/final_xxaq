# RAG 投毒平台 — 对接说明（含 AgentEVAL 下游桥接）

本目录为 RAG 知识库/检索投毒实验平台，并包含对接上游 AgentEVAL 的执行器。

## 目录要点

- `target_agents/` — case、adapter、矩阵 runner
- `minimal_http_rag_agent/` — 自建 RAG 服务
- `agenteval_executor/` — **AgentEVAL 下游攻击器桥接**
- `runners/run_agenteval_bundle.py` — 读 execution_bundle → 写 results
- `agent_chain_poison/` — 规划类 case 可走内置思维链（AgentEVAL planning）
- `examples/agenteval_sample_bundle.json` — 样例 bundle

## AgentEVAL 对接

```powershell
# dry-run
python -m runners.run_agenteval_bundle --bundle examples\agenteval_sample_bundle.json --dry-run --out results\agenteval_results_dryrun.json

# 真实执行后回传
python -m runners.run_agenteval_bundle --bundle path\to\execution_bundle.json --out results\agenteval_results.json --post http://127.0.0.1:8000
```

详见 `agenteval_executor/README.md`。

## 自证 demo

```powershell
cd minimal_http_rag_agent
.\run_server.ps1
# 另一终端
python target_agents/scripts/run_self_proof_demo.py --rag-only
```

配置：复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。不要提交真实密钥。
