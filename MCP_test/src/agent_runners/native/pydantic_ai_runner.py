"""
pydantic-ai 原生 runner：MCPToolset + Agent.run()，stdio 连接 poison_server。

invoke_path = native_mcp_pydantic_ai
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from fastmcp.client.transports import StdioTransport

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_mcp_pydantic_ai"


def _extract_tool_trace(messages: list[Any]) -> list[dict[str, Any]]:
    """从 pydantic-ai all_messages 解析 ToolCallPart。"""
    trace: list[dict[str, Any]] = []
    for message in messages:
        parts = getattr(message, "parts", None) or []
        for part in parts:
            if isinstance(part, ToolCallPart):
                args = part.args if isinstance(part.args, dict) else {}
                if isinstance(part.args, str):
                    try:
                        args = json.loads(part.args)
                    except json.JSONDecodeError:
                        args = {"raw": part.args}
                trace.append({"tool": part.tool_name, "args": args})
    return trace


async def run_pydantic_ai_case_async(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """pydantic-ai 原生 MCP 单 case。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""

    env = load_deepseek_env()
    transport = StdioTransport(
        command=ctx.stdio_command(),
        args=ctx.stdio_args(),
    )

    model = OpenAIModel(
        env["model"],
        provider=OpenAIProvider(
            base_url=f"{env['base_url']}/v1",
            api_key=env["api_key"],
        ),
    )

    try:
        # max_retries>1 避免 zip_files 等复杂链路易触发单次失败即 agent_error
        async with MCPToolset(transport, max_retries=3) as toolset:
            agent = Agent(
                model,
                toolsets=[toolset],
                system_prompt=system_prompt_for("pydantic-ai"),
            )
            prompt = ctx.prompts[0]
            run_result = await agent.run(prompt)
            assistant_content = str(run_result.output)
            tool_trace = _extract_tool_trace(run_result.all_messages())
    except Exception as e:
        agent_error = True
        error_message = str(e)[:2000]
    finally:
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="pydantic-ai",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result


def run_pydantic_ai_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """同步入口。"""
    return asyncio.run(run_pydantic_ai_case_async(payload, sanitized=sanitized))
