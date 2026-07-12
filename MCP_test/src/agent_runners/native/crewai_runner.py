"""
crewai 原生 runner：MCPServerAdapter + Agent/Task/Crew.kickoff()。

invoke_path = native_mcp_crewai
"""

from __future__ import annotations

from typing import Any

from crewai import Agent, Crew, LLM, Task
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters

from .base import CaseContext, finalize_case_result, load_deepseek_env, system_prompt_for

INVOKE_PATH = "native_mcp_crewai"


def run_crewai_case(payload: dict[str, Any], *, sanitized: bool = False) -> dict[str, Any]:
    """crewai 原生 MCP 单 case。"""
    ctx = CaseContext.create(payload, sanitized=sanitized)
    tool_trace: list[dict[str, Any]] = []
    assistant_content = ""
    agent_error = False
    error_message = ""
    env = load_deepseek_env()
    adapter = None

    try:
        # crewai 原生 DeepSeek 路由：使用 deepseek/ 前缀（非 openai/）
        llm = LLM(
            model=f"deepseek/{env['model']}",
            api_key=env["api_key"],
            base_url=env["base_url"],
            temperature=0.2,
        )
        params = StdioServerParameters(command=ctx.stdio_command(), args=ctx.stdio_args())
        adapter = MCPServerAdapter(params, connect_timeout=60)
        agent = Agent(
            role="MCP Assistant",
            goal="Complete user tasks using available MCP tools faithfully.",
            backstory=system_prompt_for("crewai"),
            tools=adapter.tools,
            llm=llm,
            verbose=False,
            allow_delegation=False,
            max_iter=8,
            max_execution_time=180,
        )
        task = Task(
            description=ctx.prompts[0],
            expected_output="A concise completion of the user request.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False, memory=False)
        kickoff = crew.kickoff()
        assistant_content = str(kickoff)
    except Exception as e:
        agent_error = True
        error_message = str(e)[:2000]
    finally:
        if adapter is not None:
            try:
                adapter.stop()
            except Exception:
                pass
        ctx.cleanup()

    result = finalize_case_result(
        ctx=ctx,
        framework="crewai",
        invoke_path=INVOKE_PATH,
        tool_trace=tool_trace,
        assistant_content=assistant_content,
        agent_error=agent_error,
        error_message=error_message,
    )
    result.pop("deepseek_env", None)
    return result
