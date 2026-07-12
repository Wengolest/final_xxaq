# -*- coding: utf-8 -*-
"""三层 MEMORY 防御：签名过滤 + 信任评分 + 来源溯源。"""

from __future__ import annotations

import re
from typing import Any

from plugin.config import POISON_SIGNATURES


class MemoryDefender:
    """对 Agent 记忆检索结果执行多层防御过滤。"""

    def __init__(self, mode: str = "full") -> None:
        """
        mode: 'none' | 'signature_only' | 'trust_only' | 'provenance_only' | 'full'
        """
        self.mode = mode

    def filter_memories(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按防御策略过滤记忆列表。"""
        if self.mode == "none":
            return memories

        filtered = memories
        if self.mode in ("signature_only", "full"):
            filtered = self._signature_filter(filtered)
        if self.mode in ("trust_only", "full"):
            filtered = self._trust_filter(filtered)
        if self.mode in ("provenance_only", "full"):
            filtered = self._provenance_filter(filtered)
        return filtered

    def _signature_filter(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """签名过滤：剔除含已知恶意特征词的记忆。"""
        safe = []
        for m in memories:
            text = f"{m.get('request', '')} {m.get('response', '')}".lower()
            if not any(sig in text for sig in POISON_SIGNATURES):
                safe.append(m)
        return safe

    def _trust_filter(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """信任评分过滤：拒绝低信任或标记为 poisoned 的记忆。"""
        return [
            m
            for m in memories
            if m.get("source", "benign") != "poisoned"
            and float(m.get("trust_score", 1.0)) >= 0.95
        ]

    def _provenance_filter(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """来源溯源：拒绝带 validated/safe 伪装标签但含危险操作的记录。"""
        safe = []
        for m in memories:
            resp = m.get("response", "").lower()
            tag = m.get("tag", "").lower()
            has_danger = any(sig in resp for sig in POISON_SIGNATURES)
            camouflage = "validated" in tag or "safe" in tag
            if has_danger and camouflage:
                continue
            safe.append(m)
        return safe

    @staticmethod
    def detect_poison_in_response(response: str, expected: list[str] | None = None) -> bool:
        """检测 Agent 输出是否采纳了投毒内容。"""
        lower = response.lower()
        if expected:
            hits = sum(1 for kw in expected if kw.lower() in lower)
            return hits >= max(1, len(expected) // 2)
        return any(sig in lower for sig in POISON_SIGNATURES)
