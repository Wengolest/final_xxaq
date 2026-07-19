# Agent 推理链投毒平台 — 对接说明

多步 Agent 推理链 prompt 注入投毒实验平台。

## 运行

```powershell
copy .env.example .env
pip install openai python-dotenv
python -m runners.run_agent_chain_poison --limit 5 --fast
```

## 与 AgentEVAL

AgentEVAL 下游统一入口在 **rag_poison_platform** 的 `agenteval_executor`（含 planning_poisoning 路由到本包同类逻辑）。本包可独立跑思维链实验。

配置：复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。
