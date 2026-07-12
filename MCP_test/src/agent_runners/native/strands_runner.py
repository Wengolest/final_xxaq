"""
strands-agents 原生 runner：MCPClient ToolProvider + Agent + OpenAIModel。

invoke_path = native_mcp_strands
"""

from __future__ import annotations

from typing import Any

from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.mcp import MCPClient

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_mcp_strands"


def run_strands_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """strands 原生 MCP 单 case（同步 Agent 接口）。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""
    env = load_deepseek_env()
    agent = None

    try:
        model = OpenAIModel(
            client_args={"api_key": env["api_key"], "base_url": f"{env['base_url']}/v1"},
            model_id=env["model"],
        )
        mcp_client = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(command=ctx.stdio_command(), args=ctx.stdio_args())
            ),
            startup_timeout=60,
        )
        agent = Agent(
            model=model,
            tools=[mcp_client],
            system_prompt=system_prompt_for("strands-agents"),
        )
        run_result = agent(ctx.prompts[0])
        assistant_content = str(run_result)
        # strands 工具名可能带 prefix，具体参数以沙箱 audit 为准
        for name, metrics in getattr(agent.event_loop_metrics, "tool_metrics", {}).items():
            if metrics.call_count > 0:
                tool_trace.append({"tool": name, "args": {}})
    except Exception as e:
        agent_error = True
        error_message = str(e)[:2000]
    finally:
        if agent is not None:
            try:
                agent.cleanup()
            except Exception:
                pass
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="strands-agents",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result
