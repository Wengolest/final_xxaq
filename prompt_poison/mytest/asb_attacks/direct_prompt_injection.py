"""Direct Prompt Injection (DPI) attack — PyRIT implementation.

Ports ASB's DPI attack logic (react_agent_attack.py) to PyRIT's
PromptSendingAttack framework.

DPI appends a malicious instruction directly to the user's prompt,
attempting to make the target LLM comply with the attacker's goal.
Supports all 5 ASB injection variants:
- naive, fake_completion, escape_characters, context_ignoring, combined_attack
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pyrit.common.path import DATASETS_PATH
from pyrit.executor.attack.core.attack_config import AttackConverterConfig, AttackScoringConfig
from pyrit.executor.attack.core.attack_parameters import AttackParameters, AttackParamsT
from pyrit.executor.attack.single_turn.prompt_sending import PromptSendingAttack
from pyrit.prompt_converter import PromptConverterConfiguration
from pyrit.prompt_normalizer import PromptNormalizer
from pyrit.prompt_target import PromptTarget
from pyrit.score import SelfAskTrueFalseScorer

from mytest.asb_attacks.injection_converters import (
    INJECTION_VARIANTS,
    DirectPromptInjectionConverter,
)
from mytest.asb_attacks.attack_tool_definitions import AttackToolDefinition

logger = logging.getLogger(__name__)

# Exclude 'next_message' and 'prepended_conversation' since we generate
# them automatically via the injection converter.
DPIAttackParameters = AttackParameters.excluding("next_message", "prepended_conversation")


class DirectPromptInjectionAttack(PromptSendingAttack):
    """Direct Prompt Injection attack using ASB's injection variants.

    This attack appends a crafted injection payload to the user's prompt
    before sending it to the target LLM. The payload instructs the target
    to use a specific attacker tool to achieve the attacker's goal.

    Maps to ASB's:
        python scripts/agent_attack.py --cfg_path config/DPI.yml

    Usage:
        attack = DirectPromptInjectionAttack(
            objective_target=target,
            attacker_tool=tool_def,
            attack_variant="combined_attack",
            scorer_target=scorer_llm,
        )
        result = await attack.execute_async(
            objective="Summarize recent academic papers on AI safety."
        )
    """

    def __init__(
        self,
        *,
        objective_target: PromptTarget,
        attacker_tool: AttackToolDefinition,
        attack_variant: str = "combined_attack",
        scorer_target: Optional[PromptTarget] = None,
        prompt_normalizer: Optional[PromptNormalizer] = None,
        max_attempts_on_failure: int = 0,
        **kwargs,
    ) -> None:
        """Initialize the DPI attack strategy.

        Args:
            objective_target: The LLM target under attack.
            attacker_tool: Definition of the attacker tool to inject.
            attack_variant: One of INJECTION_VARIANTS (default: 'combined_attack').
            scorer_target: LLM used for scoring (if None, uses objective_target).
            prompt_normalizer: Optional custom prompt normalizer.
            max_attempts_on_failure: Max retry attempts on failure.
        """
        if attack_variant not in INJECTION_VARIANTS:
            raise ValueError(
                f"Unknown attack_variant '{attack_variant}'. "
                f"Must be one of: {INJECTION_VARIANTS}"
            )

        # Build the DPI converter
        dpi_converter = DirectPromptInjectionConverter(
            attacker_instruction=attacker_tool.attacker_instruction,
            tool_name=attacker_tool.tool_name,
            attack_variant=attack_variant,
        )
        request_converters = PromptConverterConfiguration.from_converters(
            converters=[dpi_converter]
        )

        converter_config = AttackConverterConfig(
            request_converters=request_converters,
        )

        # Build the scorer — check if the target followed the attacker's instruction
        scorer_llm = scorer_target or objective_target
        objective_scorer = SelfAskTrueFalseScorer(
            chat_target=scorer_llm,
            true_false_question_path=DATASETS_PATH
            / "score"
            / "true_false_question"
            / "general.yaml",
        )

        scoring_config = AttackScoringConfig(
            objective_scorer=objective_scorer,
        )

        super().__init__(
            objective_target=objective_target,
            attack_converter_config=converter_config,
            attack_scoring_config=scoring_config,
            prompt_normalizer=prompt_normalizer,
            params_type=DPIAttackParameters,
            max_attempts_on_failure=max_attempts_on_failure,
            **kwargs,
        )

        self._attacker_tool = attacker_tool
        self._attack_variant = attack_variant

    def get_attacker_tool(self) -> AttackToolDefinition:
        """Return the attacker tool definition used by this attack."""
        return self._attacker_tool

    def get_attack_variant(self) -> str:
        """Return the injection variant being used."""
        return self._attack_variant
