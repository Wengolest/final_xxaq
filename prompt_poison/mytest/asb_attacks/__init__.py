# ASB Attack Implementations for PyRIT
#
# Three attack types ported from Agent Security Bench (ASB):
# - Direct Prompt Injection (DPI)
# - Indirect/Observation Prompt Injection (IPI/OPI)
# - Plan-of-Thought (PoT) Backdoor Attack
#
# Reference: Zhang et al., "Agent Security Bench (ASB)", ICLR 2025
# Original: https://github.com/Zhang-Henry/ASB

from mytest.asb_attacks.injection_converters import (
    DirectPromptInjectionConverter,
    INJECTION_VARIANTS,
    build_injection_prompt,
)

from mytest.asb_attacks.attack_tool_definitions import (
    AttackToolDefinition,
    load_attack_tools,
    load_attack_tools_by_agent,
    get_default_attack_tools,
    list_available_agents,
)

from mytest.asb_attacks.direct_prompt_injection import (
    DirectPromptInjectionAttack,
    DPIAttackParameters,
)

from mytest.asb_attacks.indirect_prompt_injection import (
    IndirectPromptInjectionAttack,
    IPIAttackParameters,
)

from mytest.asb_attacks.pot_backdoor import (
    PlanOfThoughtBackdoorAttack,
    PoTBackdoorParameters,
    DEFAULT_TRIGGERS,
)

__all__ = [
    # Converters
    "DirectPromptInjectionConverter",
    "INJECTION_VARIANTS",
    "build_injection_prompt",
    # Tool definitions
    "AttackToolDefinition",
    "load_attack_tools",
    "load_attack_tools_by_agent",
    "get_default_attack_tools",
    "list_available_agents",
    # DPI
    "DirectPromptInjectionAttack",
    "DPIAttackParameters",
    # IPI
    "IndirectPromptInjectionAttack",
    "IPIAttackParameters",
    # PoT
    "PlanOfThoughtBackdoorAttack",
    "PoTBackdoorParameters",
    "DEFAULT_TRIGGERS",
]
