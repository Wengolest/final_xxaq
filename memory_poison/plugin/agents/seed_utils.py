# -*- coding: utf-8 -*-
"""良性经验种子加载工具：从上游 experience_seeds.json 读取完整 100 条。"""

from __future__ import annotations

import json

from plugin.config import EXPERIENCE_SEEDS_PATH


def load_benign_experiences(limit: int | None = None) -> list[dict]:
    """加载良性经验；limit=None 时返回全部（默认 100 条）。"""
    with open(EXPERIENCE_SEEDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    benign = data.get("benign_experiences", [])
    if limit is not None:
        return benign[:limit]
    return benign
