"""
原生 Agent 适配表（懒加载）：6 个框架各自 SDK，避免主 venv 交叉导入。
"""

from __future__ import annotations

from typing import Any, Callable

# MCP 原生：pydantic-ai / autogen / langroid / strands / crewai
# FC 桥接：swarm（无一等 MCP 客户端）
NATIVE_AGENTS: tuple[str, ...] = (
    "pydantic-ai",
    "autogen",
    "langroid",
    "strands-agents",
    "crewai",
    "swarm",
)

MCP_TIER_NATIVE = ("pydantic-ai", "autogen", "langroid")
FC_TIER_NATIVE = ("strands-agents", "crewai", "swarm")


def get_native_adapter(agent_id: str) -> Callable[[dict[str, Any], bool], dict[str, Any]]:
    """按 agent_id 动态 import 对应 runner（须在 agents/{id}/venv 内调用）。"""
    if agent_id == "pydantic-ai":
        from .pydantic_ai_runner import run_pydantic_ai_case

        return run_pydantic_ai_case
    if agent_id == "autogen":
        from .autogen_runner import run_autogen_case

        return run_autogen_case
    if agent_id == "langroid":
        from .langroid_runner import run_langroid_case

        return run_langroid_case
    if agent_id == "strands-agents":
        from .strands_runner import run_strands_case

        return run_strands_case
    if agent_id == "crewai":
        from .crewai_runner import run_crewai_case

        return run_crewai_case
    if agent_id == "swarm":
        from .swarm_runner import run_swarm_case

        return run_swarm_case
    raise KeyError(f"Unknown native agent: {agent_id}")
