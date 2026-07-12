# MCP 投毒实验用 Agent（本地完整仓库）

| 目录 | 用途 | 独立环境 |
|------|------|----------|
| `autogen/` | 多智能体 + MCP 扩展 | `autogen/venv` |
| `langroid/` | 工具型 Agent | `langroid/venv` |
| `pydantic-ai/` | PydanticAI + MCP | `pydantic-ai/venv` |
| `strands-agents/` | Strands SDK | `strands-agents/venv` |
| `swarm/` | OpenAI Swarm function calling | `swarm/venv` |
| `crewai/` | Crew 多角色 | `crewai/venv` |
| `browser-use/` | 浏览器工具 Agent | `browser-use/venv` |

安装全部环境（推荐 Python 脚本，避免 PowerShell 编码问题）：

```powershell
python scripts\setup_agent_envs.py
```

安装进度日志：`agents\_setup_log.txt`

投毒实验（原生各框架 SDK）：

```powershell
python run_eval_native.py
python run_eval_native.py --agents pydantic-ai autogen --samples base_exfil
```

统一 runner 已删除；仅保留 `run_eval_native.py`。

PoC 代码见 `src/mcp_lab/`、`src/attacks/samples/`。
