# 面向多类型 Agent 集群的自动化评估与防御平台

## 一键演示（离线，无需 API Key）

```powershell
cd E:\final_xxaq
python platform\run_quick_eval.py --offline-only
```

## 全模块快速评估（需 DEEPSEEK_API_KEY）

```powershell
copy .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

python platform\run_quick_eval.py
```

## 启动 Web + 后端

```powershell
.\start.ps1
```

- 后端 API: http://localhost:8100/docs
- 前端: http://localhost:5173

## 模块说明

| 目录 | 类型 | 入口 |
|------|------|------|
| `prompt_poison` | Prompt 注入 (PyRIT/ASB) | `mytest/deepseek_direct_prompt_injection_experiment.py` |
| `chain_poison` | 推理链注入 | `chain_poison_platform/runners/run_agent_chain_poison.py` |
| `memory_poison` | 记忆投毒 | `run_experiment.py --pilot` |
| `rag_poison` | RAG 投毒 | `run_self_proof_demo.py --rag-only` |
| `MCP_test` | MCP 工具投毒 | `run_eval_native.py` / `scripts/smoke_test.py`（需先 `python scripts\setup_agent_envs.py` 安装各 Agent venv） |
| `multiagent_poison` | 多 Agent 投毒 | `run_benchmark.py --mode dry` |
| `defense_engine` | 五层防御 | `defense_engine/demo_end_to_end.py` |
| `front_web/web` | 前端界面 | `pnpm dev` |

## 平台编排 API

| 端点 | 说明 |
|------|------|
| `GET /api/poison/modules` | 列出投毒模块 |
| `POST /api/poison/run?module=multiagent` | 运行指定模块 |
| `GET /api/targets` | Agent 目标列表 |
| `GET /api/attacks/catalog` | 攻击族目录 |
