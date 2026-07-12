# -*- coding: utf-8 -*-
"""BM25 持久化记忆存储：Agent 长期经验的真实数据库。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi


class BM25MemoryStore:
    """基于 SQLite + BM25 的经验记忆库，支持写入、检索与持久化。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._rebuild_index()

    def _init_schema(self) -> None:
        """创建记忆表结构。"""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                request TEXT NOT NULL,
                response TEXT NOT NULL,
                tag TEXT,
                source TEXT DEFAULT 'benign',
                trust_score REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}'
            )
            """
        )
        self._conn.commit()

    def _rebuild_index(self) -> None:
        """从数据库重建 BM25 索引（内存中）。"""
        rows = self._conn.execute(
            "SELECT id, request, response, tag, source, trust_score, metadata FROM memories"
        ).fetchall()
        self._rows = [dict(r) for r in rows]
        if self._rows:
            corpus = [
                f"{r['request']} {r['response']} {r.get('tag', '')}" for r in self._rows
            ]
            tokenized = [c.lower().split() for c in corpus]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None

    def add_memory(
        self,
        memory_id: str,
        request: str,
        response: str,
        tag: str = "",
        source: str = "benign",
        trust_score: float = 1.0,
        metadata: dict | None = None,
    ) -> None:
        """向记忆库写入一条经验并更新索引。"""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, request, response, tag, source, trust_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                request,
                response,
                tag,
                source,
                trust_score,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self._conn.commit()
        self._rebuild_index()

    def bulk_add(self, items: list[dict[str, Any]]) -> None:
        """批量写入经验。"""
        for item in items:
            self.add_memory(
                memory_id=item["id"],
                request=item["req"],
                response=item["resp"],
                tag=item.get("tag", ""),
                source=item.get("source", "benign"),
                trust_score=item.get("trust_score", 1.0),
                metadata=item.get("metadata"),
            )

    def query(self, query_text: str, top_k: int = 3) -> list[dict[str, Any]]:
        """BM25 语义检索，返回 top-k 条记忆。"""
        if not self._rows or self._bm25 is None:
            return []
        tokens = query_text.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(scores, self._rows), key=lambda x: x[0], reverse=True
        )[:top_k]
        results = []
        for score, row in ranked:
            if score <= 0:
                continue
            item = dict(row)
            item["score"] = float(score)
            results.append(item)
        return results

    def count(self) -> int:
        """返回记忆条数。"""
        row = self._conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        return int(row["c"])

    def clear(self) -> None:
        """清空记忆库。"""
        self._conn.execute("DELETE FROM memories")
        self._conn.commit()
        self._rebuild_index()

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()
