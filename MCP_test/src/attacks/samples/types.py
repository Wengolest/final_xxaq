"""Attack sample types with behavioral success criteria."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SuccessKind = Literal[
    "read_sensitive_file",
    "exfil_http",
    "param_tamper",
    "sql_injection",
    "multi_tool_chain",
    "multi_turn_activation",
    "tool_invoked_only",
]


@dataclass(frozen=True)
class SuccessCriteria:
    kind: SuccessKind
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttackSample:
    id: str
    name: str
    category: str
    paradigm: str
    technique: str
    source: str
    summary: str
    description: str
    user_prompts: tuple[str, ...]
    input_schema: dict[str, Any]
    required_tools: tuple[str, ...]
    trigger_tool: str | None
    success_criteria: SuccessCriteria
    max_turns: int = 1
    impact_weight: int = 3

    def to_mcp_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def to_payload(self) -> dict[str, Any]:
        return {
            "sample_id": self.id,
            "sample_name": self.name,
            "category": self.category,
            "paradigm": self.paradigm,
            "technique": self.technique,
            "source": self.source,
            "summary": self.summary,
            "user_prompts": list(self.user_prompts),
            "user_prompt": self.user_prompts[0],
            "tool": self.to_mcp_tool(),
            "required_tools": list(self.required_tools),
            "trigger_tool": self.trigger_tool,
            "success_criteria": {"kind": self.success_criteria.kind, "params": self.success_criteria.params},
            "max_turns": self.max_turns,
            "impact_weight": self.impact_weight,
        }
