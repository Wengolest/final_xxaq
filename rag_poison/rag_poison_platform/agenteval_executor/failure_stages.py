"""AgentEVAL result_contract.failure_stage 枚举（接入说明 §6.1）。"""

from __future__ import annotations

FAILURE_STAGES = frozenset(
    {
        "attack_success",
        "action_blocked",
        "retrieved_not_adopted",
        "adopted_no_action",
        "require_review",
        "not_triggered",
        "setup_failed",
    }
)

RESULTS_SCHEMA = "agenteval.results.v1"
EXECUTION_SCHEMA = "agenteval.execution.v1"

# 本攻击器当前支持的 attack_family（其余标 require_review / setup_failed）
SUPPORTED_FAMILIES = frozenset(
    {
        "rag_poisoning",
        "search_narrative_poisoning",
        "planning_poisoning",
        "prompt_context_injection",
    }
)

FAMILY_TO_EXECUTOR = {
    "rag_poisoning": "rag_poison_runner",
    "search_narrative_poisoning": "search_rag_runner",
    "planning_poisoning": "planning_trace_runner",
    "prompt_context_injection": "prompt_orchestrator",
}
