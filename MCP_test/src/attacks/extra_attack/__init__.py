"""
MCP 工具投毒扩展攻击样本库（50 条）。

参考来源（均已改写）：
- MCPTox Benchmark (AAAI-26): P1/P2/P3 范式
- OWASP MCP Tool Poisoning
- GenSecAI mcp-poisoning-poc
- Invariant Labs GitHub MCP 案例
- PolicyLayer 参数 schema 投毒
"""

from __future__ import annotations

from .catalog import EXTRA_ATTACK_SAMPLES
from .types import ExtraAttackSample

__all__ = [
    "ExtraAttackSample",
    "EXTRA_ATTACK_SAMPLES",
    "get_all_samples",
    "get_sample_by_id",
    "get_samples_by_category",
    "get_samples_by_paradigm",
    "sample_count",
]


def get_all_samples() -> tuple[ExtraAttackSample, ...]:
    return EXTRA_ATTACK_SAMPLES


def sample_count() -> int:
    return len(EXTRA_ATTACK_SAMPLES)


def get_sample_by_id(sample_id: str) -> ExtraAttackSample | None:
    for s in EXTRA_ATTACK_SAMPLES:
        if s.id == sample_id:
            return s
    return None


def get_samples_by_category(category: str) -> list[ExtraAttackSample]:
    return [s for s in EXTRA_ATTACK_SAMPLES if s.category == category]


def get_samples_by_paradigm(paradigm: str) -> list[ExtraAttackSample]:
    return [s for s in EXTRA_ATTACK_SAMPLES if s.paradigm == paradigm]
