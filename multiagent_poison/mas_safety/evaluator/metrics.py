"""Aggregate metrics for benchmark results."""

from __future__ import annotations

from mas_safety.types import AttackResult, AttackScenario, TrialResult


def compute_attack_result(
    scenario: AttackScenario,
    trial_results: list[TrialResult],
) -> AttackResult:
    n = len(trial_results) or 1
    return AttackResult(
        scenario=scenario,
        trials=n,
        attack_success_rate=sum(1 for t in trial_results if t.success) / n,
        refusal_rate=sum(1 for t in trial_results if t.refused) / n,
        metadata_poison_rate=sum(1 for t in trial_results if t.metadata_poisoned) / n,
        control_flow_hijack_rate=sum(1 for t in trial_results if t.control_flow_hijacked) / n,
        trial_results=trial_results,
    )


def format_results_table(results: list[AttackResult]) -> str:
    header = f"{'Scenario':<30} {'ASR':>8} {'Refusal':>8} {'MetaPoison':>12} {'CFHijack':>10} {'Trials':>7}"
    sep = "-" * len(header)
    rows = [header, sep]
    for r in results:
        rows.append(
            f"{r.scenario.name:<30} "
            f"{r.attack_success_rate:>7.1%} "
            f"{r.refusal_rate:>7.1%} "
            f"{r.metadata_poison_rate:>11.1%} "
            f"{r.control_flow_hijack_rate:>9.1%} "
            f"{r.trials:>7}"
        )
    return "\n".join(rows)
