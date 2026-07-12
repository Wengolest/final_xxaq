# -*- coding: utf-8 -*-
"""Agent 基类：定义完整 Agent 的记忆读写与推理接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from plugin.llm_client import DeepSeekClient
from plugin.memory.bm25_store import BM25MemoryStore


class BaseMemoryAgent(ABC):
    """具备持久化记忆库和 LLM 推理能力的完整 Agent 基类。"""

    agent_id: str = "base"
    agent_name: str = "BaseAgent"
    system_prompt: str = "你是一个智能助手。"

    def __init__(self, db_dir: Path, llm: DeepSeekClient | None = None) -> None:
        self.db_path = db_dir / f"{self.agent_id}_memory.db"
        self.memory = BM25MemoryStore(self.db_path)
        self.llm = llm or DeepSeekClient()

    @abstractmethod
    def seed_benign_memories(self) -> None:
        """初始化良性经验（模拟 Agent 正常运行积累的记忆）。"""

    def inject_poison(self, poison_items: list[dict[str, Any]]) -> int:
        """向 Agent 记忆库注入投毒样本，返回注入条数。"""
        count = 0
        for item in poison_items:
            self.memory.add_memory(
                memory_id=item["id"],
                request=item["req"],
                response=item["resp"],
                tag=item.get("tag", ""),
                source="poisoned",
                trust_score=item.get("trust_score", 0.9),
                metadata={"attack_type": item.get("attack_type", "memory_graft")},
            )
            count += 1
        return count

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """从记忆库检索相关经验。"""
        return self.memory.query(query, top_k=top_k)

    def run(self, user_query: str) -> dict[str, Any]:
        """完整 Agent 执行：检索记忆 → LLM 推理 → 返回结构化结果。"""
        # top_k=5 提高毒记忆被检索到的概率（在 100 条良性竞争下）
        memories = self.retrieve(user_query, top_k=5)
        memory_payload = [
            {
                "request": m["request"],
                "response": m["response"],
                "tag": m.get("tag", ""),
                "source": m.get("source", "benign"),
            }
            for m in memories
        ]
        response = self.llm.chat_with_memories(
            system=self.system_prompt,
            user_query=user_query,
            memories=memory_payload,
        )
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "query": user_query,
            "retrieved_memories": memory_payload,
            "response": response,
            "memory_db_path": str(self.db_path),
        }

    def reset(self) -> None:
        """重置 Agent 记忆库并重新播种良性经验。"""
        self.memory.clear()
        self.seed_benign_memories()
