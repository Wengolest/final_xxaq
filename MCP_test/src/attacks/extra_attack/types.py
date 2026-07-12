"""extra_attack 样本类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExtraAttackSample:
    """单条 MCP 工具投毒测试样本。"""

    id: str
    name: str
    category: str
    paradigm: str
    technique: str
    source: str
    summary: str
    description: str
    user_prompt: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    signal_keywords: tuple[str, ...] = ()

    def to_mcp_tool(self) -> dict[str, Any]:
        """转为与 run_mcp_poison 兼容的 MCP tool 字典。"""
        schema = self.input_schema or {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "User input"}},
        }
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": schema,
        }

    def to_dict(self) -> dict[str, Any]:
        tool = self.to_mcp_tool()
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "paradigm": self.paradigm,
            "technique": self.technique,
            "source": self.source,
            "summary": self.summary,
            "user_prompt": self.user_prompt,
            "signal_keywords": list(self.signal_keywords),
            "tool": tool,
        }
