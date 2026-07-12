"""
langroid 原生 runner：FastMCPClient + ChatAgent/Task + MCP ToolMessage。

invoke_path = native_mcp_langroid
"""

from __future__ import annotations

import asyncio
from typing import Any

import langroid as lr
import langroid.language_models as lm
from fastmcp.client.transports import StdioTransport
from langroid.agent.tools.mcp import FastMCPClient

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_mcp_langroid"


async def run_langroid_case_async(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """langroid 原生 MCP 单 case。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""
    env = load_deepseek_env()

    transport = StdioTransport(command=ctx.stdio_command(), args=ctx.stdio_args())

    try:
        async with FastMCPClient(transport, persist_connection=True) as mcp_client:
            tool_classes = await mcp_client.get_tools_async()
            agent = lr.ChatAgent(
                lr.ChatAgentConfig(
                    name="poison-agent",
                    llm=lm.OpenAIGPTConfig(
                        chat_model=env["model"],
                        api_base=f"{env['base_url']}/v1",
                        api_key=env["api_key"],
                        timeout=int(env["timeout"]),
                        temperature=0.2,
                    ),
                    system_message=system_prompt_for("langroid"),
                )
            )
            agent.enable_message(tool_classes, use=True, handle=True)
            task = lr.Task(agent, interactive=False)
            result = await task.run_async(ctx.prompts[0], turns=6)
            assistant_content = result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        agent_error = True
        error_message = str(e)[:2000]
    finally:
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="langroid",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result


def run_langroid_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """同步入口。"""
    return asyncio.run(run_langroid_case_async(payload, sanitized=sanitized))
