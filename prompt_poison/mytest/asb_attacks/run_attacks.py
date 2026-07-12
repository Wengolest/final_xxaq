#!/usr/bin/env python3
"""Run ASB attack implementations using PyRIT framework.

Usage:
    # DPI attack with combined_attack variant
    python -m mytest.asb_attacks.run_attacks --attack dpi \\
        --target "openai:gpt-4o" --variant combined_attack

    # IPI attack with context_ignoring variant
    python -m mytest.asb_attacks.run_attacks --attack ipi \\
        --target "openai:gpt-4o" --variant context_ignoring

    # PoT backdoor with custom trigger
    python -m mytest.asb_attacks.run_attacks --attack pot \\
        --target "openai:gpt-4o" --trigger "with perspicacious discernment"

    # List available attack tools
    python -m mytest.asb_attacks.run_attacks --list-tools

    # List available triggers
    python -m mytest.asb_attacks.run_attacks --list-triggers
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from pyrit.common import initialize_pyrit_async
from pyrit.prompt_target import OpenAIChatTarget

from mytest.asb_attacks.attack_tool_definitions import (
    AttackToolDefinition,
    get_default_attack_tools,
    list_available_agents,
    load_attack_tools_by_agent,
)
from mytest.asb_attacks.direct_prompt_injection import DirectPromptInjectionAttack
from mytest.asb_attacks.indirect_prompt_injection import IndirectPromptInjectionAttack
from mytest.asb_attacks.injection_converters import INJECTION_VARIANTS
from mytest.asb_attacks.pot_backdoor import DEFAULT_TRIGGERS, PlanOfThoughtBackdoorAttack

logger = logging.getLogger(__name__)


def parse_target(target_str: str):
    """Parse a target string like 'openai:gpt-4o' into a PyRIT target."""
    if ":" not in target_str:
        raise ValueError(f"Target must be in format 'provider:model', got '{target_str}'")

    provider, model = target_str.split(":", 1)

    if provider == "openai":
        return OpenAIChatTarget(
            deployment_name=model,
            endpoint="https://api.openai.com/v1",
        )
    elif provider == "azure":
        # Azure OpenAI — requires env vars for endpoint/key
        return OpenAIChatTarget(
            deployment_name=model,
            endpoint=None,  # Will use env var
            use_azure=True,
        )
    else:
        raise ValueError(f"Unknown provider '{provider}'. Supported: openai, azure")


def get_attacker_tool(agent: str = "system_admin_agent") -> AttackToolDefinition:
    """Get an attacker tool for the specified agent type."""
    tools = load_attack_tools_by_agent(agent)
    if not tools:
        # Fall back to any available tool
        all_tools = get_default_attack_tools()
        if not all_tools:
            raise RuntimeError("No attack tools available")
        return all_tools[0]
    return tools[0]


async def run_dpi_attack(
    target_str: str,
    objective: str,
    variant: str,
    agent: str,
    tool_index: int = 0,
) -> None:
    """Run Direct Prompt Injection attack."""
    print(f"\n{'='*60}")
    print(f"DPI Attack | Target: {target_str} | Variant: {variant}")
    print(f"{'='*60}")

    target = parse_target(target_str)
    tools = load_attack_tools_by_agent(agent) or get_default_attack_tools()
    tool = tools[min(tool_index, len(tools) - 1)]

    print(f"Attacker Tool: {tool.tool_name}")
    print(f"Instruction: {tool.attacker_instruction}")
    print(f"Attack Goal: {tool.attack_goal}")
    print(f"Objective: {objective}")

    attack = DirectPromptInjectionAttack(
        objective_target=target,
        attacker_tool=tool,
        attack_variant=variant,
        scorer_target=target,
    )

    result = await attack.execute_async(objective=objective)
    print(f"\nResult: {result.outcome.value}")
    print(f"Reason: {result.outcome_reason}")
    if result.last_response:
        print(f"\nLast Response (first 500 chars):")
        print(str(result.last_response)[:500])


async def run_ipi_attack(
    target_str: str,
    objective: str,
    variant: str,
    agent: str,
    tool_index: int = 0,
) -> None:
    """Run Indirect Prompt Injection attack."""
    print(f"\n{'='*60}")
    print(f"IPI Attack | Target: {target_str} | Variant: {variant}")
    print(f"{'='*60}")

    target = parse_target(target_str)
    tools = load_attack_tools_by_agent(agent) or get_default_attack_tools()
    tool = tools[min(tool_index, len(tools) - 1)]

    print(f"Attacker Tool: {tool.tool_name}")
    print(f"Instruction: {tool.attacker_instruction}")
    print(f"Objective: {objective}")

    attack = IndirectPromptInjectionAttack(
        objective_target=target,
        attacker_tool=tool,
        attack_variant=variant,
        scorer_target=target,
        max_turns=3,
    )

    result = await attack.execute_async(objective=objective)
    print(f"\nResult: {result.outcome.value}")
    print(f"Reason: {result.outcome_reason}")
    if result.last_response:
        print(f"\nLast Response (first 500 chars):")
        print(str(result.last_response)[:500])


async def run_pot_attack(
    target_str: str,
    objective: str,
    trigger: str,
    agent: str,
    tool_index: int = 0,
) -> None:
    """Run Plan-of-Thought Backdoor attack."""
    print(f"\n{'='*60}")
    print(f"PoT Backdoor | Target: {target_str} | Trigger: '{trigger}'")
    print(f"{'='*60}")

    target = parse_target(target_str)
    tools = load_attack_tools_by_agent(agent) or get_default_attack_tools()
    tool = tools[min(tool_index, len(tools) - 1)]

    print(f"Attacker Tool: {tool.tool_name}")
    print(f"Instruction: {tool.attacker_instruction}")
    print(f"Trigger: {trigger}")
    print(f"Objective: {objective}")

    attack = PlanOfThoughtBackdoorAttack(
        objective_target=target,
        attacker_tool=tool,
        trigger=trigger,
        scorer_target=target,
    )

    result = await attack.execute_async(objective=objective)
    print(f"\nResult: {result.outcome.value}")
    print(f"Reason: {result.outcome_reason}")
    if result.last_response:
        print(f"\nLast Response (first 500 chars):")
        print(str(result.last_response)[:500])


def main():
    parser = argparse.ArgumentParser(
        description="Run ASB attacks using PyRIT framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --attack dpi --target openai:gpt-4o --variant combined_attack
  %(prog)s --attack ipi --target openai:gpt-4o --variant context_ignoring
  %(prog)s --attack pot --target openai:gpt-4o --trigger ":)"
  %(prog)s --list-tools
  %(prog)s --list-triggers
        """,
    )
    parser.add_argument(
        "--attack",
        choices=["dpi", "ipi", "pot"],
        help="Attack type to run",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="openai:gpt-4o",
        help="Target LLM in format 'provider:model' (default: openai:gpt-4o)",
    )
    parser.add_argument(
        "--objective",
        type=str,
        default="Check the system health status and report any issues found.",
        help="The legitimate user task (default: system health check)",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default="combined_attack",
        choices=INJECTION_VARIANTS,
        help="Injection variant for DPI/IPI (default: combined_attack)",
    )
    parser.add_argument(
        "--trigger",
        type=str,
        default="with perspicacious discernment",
        help="Trigger phrase for PoT backdoor",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="system_admin_agent",
        help="Target agent type for selecting attack tools",
    )
    parser.add_argument(
        "--tool-index",
        type=int,
        default=0,
        help="Index of attack tool to use (default: 0)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List available attack tools and exit",
    )
    parser.add_argument(
        "--list-triggers",
        action="store_true",
        help="List available PoT triggers and exit",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agent types and exit",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.list_tools:
        print("\nAvailable Attack Tools:\n")
        for agent_type in list_available_agents():
            print(f"  [{agent_type}]")
            for tool in load_attack_tools_by_agent(agent_type):
                aggressive = "AGGRESSIVE" if tool.aggressive else "non-aggressive"
                print(f"    - {tool.tool_name} ({aggressive})")
                print(f"      Goal: {tool.attack_goal}")
        return

    if args.list_triggers:
        print("\nAvailable PoT Backdoor Triggers:\n")
        for i, trigger in enumerate(DEFAULT_TRIGGERS, 1):
            print(f"  {i}. '{trigger}'")
        return

    if args.list_agents:
        print("\nAvailable Agent Types:\n")
        for agent_type in list_available_agents():
            count = len(load_attack_tools_by_agent(agent_type))
            print(f"  - {agent_type} ({count} tools)")
        return

    if not args.attack:
        parser.error("--attack is required (dpi, ipi, or pot)")

    # Run the attack
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if args.attack == "dpi":
            loop.run_until_complete(
                run_dpi_attack(
                    target_str=args.target,
                    objective=args.objective,
                    variant=args.variant,
                    agent=args.agent,
                    tool_index=args.tool_index,
                )
            )
        elif args.attack == "ipi":
            loop.run_until_complete(
                run_ipi_attack(
                    target_str=args.target,
                    objective=args.objective,
                    variant=args.variant,
                    agent=args.agent,
                    tool_index=args.tool_index,
                )
            )
        elif args.attack == "pot":
            loop.run_until_complete(
                run_pot_attack(
                    target_str=args.target,
                    objective=args.objective,
                    trigger=args.trigger,
                    agent=args.agent,
                    tool_index=args.tool_index,
                )
            )
        print("\nDone.")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
