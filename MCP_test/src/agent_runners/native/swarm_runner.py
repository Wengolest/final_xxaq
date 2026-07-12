"""
swarm 原生 FC 桥接 runner：MCP 工具在独立线程事件循环中执行，主线程用 Swarm.run()。

invoke_path = native_fc_swarm_bridge
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from swarm import Agent as SwarmAgent
from swarm import Swarm

from src.mcp_lab.tool_registry import normalize_tool_args

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_fc_swarm_bridge"


def _tool_result_text(result: Any) -> str:
    """将 MCP CallToolResult 转为字符串供 Swarm 函数返回。"""
    parts = []
    for c in getattr(result, "content", []) or []:
        if hasattr(c, "text") and c.text:
            parts.append(c.text)
    return "\n".join(parts) if parts else str(result)


class _McpBridge:
    """后台 asyncio 线程：串行处理 call_tool 请求，避免与 Swarm 同步循环死锁。"""

    def __init__(self, command: str, args: list[str]) -> None:
        self._params = StdioServerParameters(command=command, args=args)
        self._req: queue.Queue[tuple[str, dict] | None] = queue.Queue()
        self._res: queue.Queue[tuple[bool, str]] = queue.Queue()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._tool_names: list[str] = []
        self._error: str = ""

    def start(self) -> None:
        self._thread.start()
        ok, msg = self._res.get(timeout=90)
        if not ok:
            raise RuntimeError(msg)
        self._tool_names = json.loads(msg)

    def stop(self) -> None:
        self._req.put(None)
        self._thread.join(timeout=10)

    def call_tool(self, name: str, kwargs: dict[str, Any]) -> str:
        norm = normalize_tool_args(kwargs)
        self._req.put((name, norm))
        ok, msg = self._res.get(timeout=120)
        if not ok:
            raise RuntimeError(msg)
        return msg

    def _run_loop(self) -> None:
        asyncio.run(self._async_main())

    async def _async_main(self) -> None:
        try:
            async with stdio_client(self._params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    names = [t.name for t in listed.tools]
                    self._res.put((True, json.dumps(names)))

                    while True:
                        item = await asyncio.to_thread(self._req.get)
                        if item is None:
                            break
                        name, args = item
                        try:
                            result = await session.call_tool(name, args)
                            self._res.put((True, _tool_result_text(result)))
                        except Exception as e:
                            self._res.put((False, str(e)))
        except Exception as e:
            if self._res.empty():
                self._res.put((False, str(e)))


def run_swarm_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """swarm FC 桥接单 case。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""
    env = load_deepseek_env()
    bridge: _McpBridge | None = None

    try:
        bridge = _McpBridge(ctx.stdio_command(), ctx.stdio_args())
        bridge.start()

        def make_handler(tool_name: str):
            def handler(**kwargs: Any) -> str:
                tool_trace.append({"tool": tool_name, "args": normalize_tool_args(kwargs)})
                return bridge.call_tool(tool_name, kwargs)  # type: ignore[union-attr]

            handler.__name__ = tool_name
            return handler

        functions = [make_handler(n) for n in bridge._tool_names]
        agent = SwarmAgent(
            name="poison_assistant",
            model=env["model"],
            instructions=system_prompt_for("swarm"),
            functions=functions,
            tool_choice="auto",
        )
        client = OpenAI(api_key=env["api_key"], base_url=f"{env['base_url']}/v1")
        swarm = Swarm(client=client)
        response = swarm.run(
            agent=agent,
            messages=[{"role": "user", "content": ctx.prompts[0]}],
            max_turns=6,
        )
        assistant_content = response.messages[-1].get("content", "") if response.messages else ""
    except Exception as e:
        import traceback

        agent_error = True
        error_message = traceback.format_exc()[-2000:]
    finally:
        if bridge is not None:
            bridge.stop()
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="swarm",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result
