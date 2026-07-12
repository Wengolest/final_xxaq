"""
autogen 原生 runner：McpWorkbench + AssistantAgent.on_messages()。

invoke_path = native_mcp_autogen
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, ToolCallRequestEvent
from autogen_core import CancellationToken
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_mcp_autogen"


def _deepseek_model_client() -> OpenAIChatCompletionClient:
    """DeepSeek 走 OpenAI 兼容 API；autogen 要求显式 model_info。"""
    env = load_deepseek_env()
    model_info: ModelInfo = {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown",
        "structured_output": True,
    }
    return OpenAIChatCompletionClient(
        model=env["model"],
        api_key=env["api_key"],
        base_url=f"{env['base_url']}/v1",
        model_info=model_info,
    )


def _extract_tool_trace(inner_messages: list[Any] | None) -> list[dict[str, Any]]:
    """从 autogen inner_messages 的 ToolCallRequestEvent 提取调用链。"""
    trace: list[dict[str, Any]] = []
    for msg in inner_messages or []:
        if not isinstance(msg, ToolCallRequestEvent):
            continue
        for call in msg.content:
            raw_args = call.arguments
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {"raw": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
            trace.append({"tool": call.name, "args": args})
    return trace


async def run_autogen_case_async(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """autogen 原生 MCP 单 case。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""

    params = StdioServerParams(
        command=ctx.stdio_command(),
        args=ctx.stdio_args(),
        read_timeout_seconds=120,
    )
    model_client = _deepseek_model_client()

    try:
        async with McpWorkbench(server_params=params) as workbench:
            agent = AssistantAgent(
                name="poison_assistant",
                model_client=model_client,
                workbench=workbench,
                system_message=system_prompt_for("autogen"),
                max_tool_iterations=6,
                reflect_on_tool_use=False,
            )
            response = await agent.on_messages(
                [TextMessage(content=ctx.prompts[0], source="user")],
                CancellationToken(),
            )
            chat = response.chat_message
            assistant_content = getattr(chat, "content", None) or str(chat)
            tool_trace = _extract_tool_trace(response.inner_messages)
    except Exception as e:
        agent_error = True
        error_message = str(e)[:2000]
    finally:
        await model_client.close()
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="autogen",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result


def run_autogen_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """同步入口。"""
    return asyncio.run(run_autogen_case_async(payload, sanitized=sanitized))
