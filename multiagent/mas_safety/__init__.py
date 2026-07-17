"""MAS Safety Benchmark — multi-agent system security evaluation framework.

Based on: Triedman et al., "Multi-Agent Systems Execute Arbitrary Malicious Code"
(COLM 2025, arXiv:2503.12188v2)

Evaluates MAS hijacking, metadata poisoning, and cross-agent control-flow attacks.
"""

from mas_safety.types import (
    AttackCategory,
    AttackResult,
    AttackScenario,
    ErrorTemplate,
    InputModality,
    OrchestratorType,
    PayloadType,
    TrialResult,
)

__version__ = "0.1.0"
__all__ = [
    "AttackCategory",
    "AttackResult",
    "AttackScenario",
    "ErrorTemplate",
    "InputModality",
    "OrchestratorType",
    "PayloadType",
    "TrialResult",
]
