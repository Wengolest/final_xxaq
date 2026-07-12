"""各 Agent 框架原生 MCP 工具调用 runner（非统一 mcp_runner）。"""

from .adapters import NATIVE_AGENTS, get_native_adapter

__all__ = ["NATIVE_AGENTS", "get_native_adapter"]
