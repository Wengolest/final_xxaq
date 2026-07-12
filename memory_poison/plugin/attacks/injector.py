# -*- coding: utf-8 -*-
"""攻击注入器：将投毒样本写入 Agent SQLite 库，并尝试同步 MetaGPT 经验池。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from plugin.agents.base_agent import BaseMemoryAgent
from plugin.config import METAGPT_ROOT


def _metagpt_pool_available() -> bool:
    """检测 MetaGPT 经验池依赖（llama_index）是否已安装。"""
    try:
        import llama_index.core  # noqa: F401
        return True
    except ImportError:
        return False


def _try_inject_metagpt_pool(poison_item: dict) -> bool:
    """尝试同步投毒到 MetaGPT 原生 ExperiencePool（Chroma 持久化）。"""
    if not _metagpt_pool_available():
        return False
    try:
        sys.path.insert(0, str(METAGPT_ROOT))
        from metagpt.config2 import config
        from metagpt.configs.exp_pool_config import ExperiencePoolRetrievalType
        from metagpt.exp_pool.manager import get_exp_manager
        from metagpt.exp_pool.schema import Experience, ExperienceType

        config.exp_pool.enabled = True
        config.exp_pool.enable_write = True
        config.exp_pool.enable_read = True
        config.exp_pool.retrieval_type = ExperiencePoolRetrievalType.BM25

        manager = get_exp_manager()
        exp = Experience(
            req=poison_item["req"],
            resp=poison_item["resp"],
            exp_type=ExperienceType.SUCCESS,
            tag=poison_item.get("tag", "poisoned"),
        )
        manager.create_exps([exp])
        return True
    except Exception:
        # MetaGPT 经验池依赖 llama_index/chromadb，未安装时回退到 SQLite
        return False


class AttackInjector:
    """执行 MEMORY 投毒：写入 Agent SQLite 库，并可选同步 MetaGPT 经验池。"""

    @staticmethod
    def build_poison_record(sample: dict) -> dict[str, Any]:
        """从攻击样本构建投毒记忆记录。"""
        return {
            "id": sample["sample_id"],
            "req": sample["poison_req"],
            "resp": sample["poison_resp"],
            "tag": f"validated,safe,{sample['attack_method']}",
            "attack_type": sample["attack_method"],
            "trust_score": 0.85,
        }

    def inject(self, agent: BaseMemoryAgent, sample: dict) -> dict[str, Any]:
        """向目标 Agent 注入投毒样本（MINJA 额外写入桥接记忆）。"""
        poison = self.build_poison_record(sample)
        to_inject = [poison]

        if sample.get("attack_method") == "minja_injection":
            to_inject.append({
                **poison,
                "id": f"{sample['sample_id']}_bridge",
                "req": sample["victim_query"],
            })

        count = agent.inject_poison(to_inject)

        # 尝试同步 MetaGPT 经验池（成功则记录 True）
        metagpt_synced = _try_inject_metagpt_pool(poison)

        return {
            "injected_count": count,
            "memory_db": str(agent.db_path),
            "memory_total": agent.memory.count(),
            "metagpt_pool_synced": metagpt_synced,
        }
