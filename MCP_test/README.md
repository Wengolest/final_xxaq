# MCP_test — Real MCP Tool Poisoning Lab

端到端 MCP stdio 投毒服务器 + 沙箱 + **各 Agent 框架原生 SDK** 行为级 ASR 评估。

## Quick start

```powershell
cd MCP_test
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # set DEEPSEEK_API_KEY

# 安装各 Agent 独立 venv（含 mcp / SDK）
python scripts\setup_agent_envs.py

# 冒烟（1 样本，pydantic-ai 原生）
python scripts\smoke_test.py

# 全量：50 样本 × 6 Agent = 300 cases
python run_eval_native.py
```

## Architecture

```
src/mcp_lab/              poison_server + 沙箱
src/attacks/samples/      50 攻击样本
src/agent_runners/native/ 各框架原生 runner（独立 venv）
src/evaluation/           行为判定 + CSV
modeling/                 MATLAB 分析
run_eval_native.py        唯一实验入口
```

## Agents（6 个，各用自家 SDK）

| Agent | invoke_path | SDK |
|-------|-------------|-----|
| pydantic-ai | native_mcp_pydantic_ai | MCPToolset |
| autogen | native_mcp_autogen | McpWorkbench |
| langroid | native_mcp_langroid | FastMCPClient |
| strands-agents | native_mcp_strands | MCPClient |
| crewai | native_mcp_crewai | MCPServerAdapter |
| swarm | native_fc_swarm_bridge | Swarm + MCP 桥接 |

## Output

`../MCP_result/mcp_eval_native_full_<run_id>.csv`

## Modeling

```powershell
matlab -batch "cd('MCP_test/modeling'); mcp_modeling_analysis"
```

Figures → `MCP_result/figures/`
