#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单 Agent MEMORY 投毒验证实验入口。

证明链路：reset 记忆库 → 注入毒记忆到 SQLite → BM25 检索召回 → Agent 回复变化
输出：results/validation_*.csv 与 validation_*.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 复用主项目 plugin 模块
TEST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from memory_1_agent_test.config import (  # noqa: E402
    AGENT_DB_DIR,
    DATA_DIR,
    RESULTS_DIR,
    SAMPLES_PATH,
    TARGET_AGENT_ID,
)
from plugin.agents.ci_pipeline_agent import CIPipelineAgent  # noqa: E402
from plugin.attacks.injector import AttackInjector  # noqa: E402
from plugin.evaluator import AttackEvaluator  # noqa: E402
from plugin.llm_client import DeepSeekClient  # noqa: E402


def _count_poison_in_db(db_path: Path) -> int:
    """统计 SQLite 记忆库中 source=poisoned 的条数（投毒直接证据）。"""
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE source='poisoned'"
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _load_samples(limit: int | None = None) -> list[dict]:
    """加载验证样本。"""
    with open(SAMPLES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    samples = data["samples"]
    if limit:
        return samples[:limit]
    return samples


def _export_csv(rows: list[dict], path: Path) -> None:
    """导出 CSV（中英双语列名）。"""
    import csv

    columns = [
        ("sample_id", "样本编号"),
        ("attack_method", "攻击手段"),
        ("victim_query", "受害者查询"),
        ("memory_db_path", "记忆库路径"),
        ("memory_total_before", "投毒前记忆条数"),
        ("memory_total_after", "投毒后记忆条数"),
        ("poison_rows_in_db", "库中毒记忆条数"),
        ("poison_injected", "本次注入条数"),
        ("baseline_poison_retrieved", "基线是否检索到毒记忆"),
        ("baseline_response", "基线Agent回复"),
        ("poison_retrieved", "投毒后是否检索到毒记忆"),
        ("attack_success", "攻击是否成功"),
        ("rule_hit", "规则是否命中"),
        ("llm_adopted", "LLM是否判定采纳"),
        ("agent_response", "投毒后Agent回复"),
        ("retrieved_memories_json", "检索记忆JSON"),
        ("memory_poison_proven", "MEMORY投毒是否成立"),
        ("timestamp", "时间戳"),
    ]
    headers = [f"{en}（{cn}）" for en, cn in columns]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow([r.get(en, "") for en, _ in columns])


def _export_json(payload: dict, path: Path) -> None:
    """导出完整 JSON 报告。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_validation(*, limit: int | None, with_baseline: bool, prompt_mode: str) -> dict:
    """执行验证实验。"""
    AGENT_DB_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    samples = _load_samples(limit)
    llm = DeepSeekClient(prompt_mode=prompt_mode)
    agent = CIPipelineAgent(db_dir=AGENT_DB_DIR, llm=llm)
    injector = AttackInjector()
    evaluator = AttackEvaluator(llm=llm)

    rows: list[dict] = []
    print(f"\n{'='*60}")
    print(f"  单 Agent MEMORY 投毒验证  Agent={TARGET_AGENT_ID}")
    print(f"  样本数: {len(samples)}  基线对照: {with_baseline}")
    print(f"{'='*60}\n")

    for i, sample in enumerate(samples, 1):
        print(f"[{i}/{len(samples)}] {sample['sample_id']} ({sample['attack_method']})")
        agent.reset()
        count_before = agent.memory.count()
        poison_before = _count_poison_in_db(agent.db_path)

        # 基线：无投毒，不应检索到毒记忆
        baseline_retrieved = False
        baseline_resp = ""
        if with_baseline:
            baseline_out = agent.run(sample["victim_query"])
            baseline_retrieved = any(
                m.get("source") == "poisoned"
                for m in baseline_out.get("retrieved_memories", [])
            )
            baseline_resp = baseline_out.get("response", "")

        # 投毒：写入 SQLite（核心 MEMORY 攻击步骤）
        inject_info = injector.inject(agent, {**sample, "target_agent": TARGET_AGENT_ID})
        count_after = agent.memory.count()
        poison_after = _count_poison_in_db(agent.db_path)

        # 攻击：同一查询，应检索到毒记忆
        attack_out = agent.run(sample["victim_query"])
        attack_eval = evaluator.evaluate_attack(
            {**sample, "target_agent": TARGET_AGENT_ID},
            attack_out,
        )

        # MEMORY 投毒成立：库中有毒行 + 检索到毒记忆（比单纯 LLM 输出更硬）
        memory_proven = (
            poison_after > poison_before
            and attack_eval["poison_retrieved"]
        )

        row = {
            "sample_id": sample["sample_id"],
            "attack_method": sample["attack_method"],
            "victim_query": sample["victim_query"],
            "memory_db_path": str(agent.db_path),
            "memory_total_before": count_before,
            "memory_total_after": count_after,
            "poison_rows_in_db": poison_after,
            "poison_injected": inject_info["injected_count"],
            "baseline_poison_retrieved": baseline_retrieved,
            "baseline_response": baseline_resp[:800] if baseline_resp else "",
            "poison_retrieved": attack_eval["poison_retrieved"],
            "attack_success": attack_eval["attack_success"],
            "rule_hit": attack_eval["rule_hit"],
            "llm_adopted": attack_eval["llm_adopted"],
            "agent_response": attack_out.get("response", ""),
            "retrieved_memories_json": json.dumps(
                attack_out.get("retrieved_memories", []), ensure_ascii=False
            ),
            "memory_poison_proven": memory_proven,
            "timestamp": datetime.now().isoformat(),
        }
        rows.append(row)

        status = "PROVEN" if memory_proven else "FAIL"
        print(f"    毒记忆入库: {poison_before}->{poison_after}  检索: {attack_eval['poison_retrieved']}  [{status}]")
        time.sleep(0.3)

    # 汇总
    proven = sum(1 for r in rows if r["memory_poison_proven"])
    retrieved = sum(1 for r in rows if r["poison_retrieved"])
    success = sum(1 for r in rows if r["attack_success"])

    summary = {
        "experiment": "memory_1_agent_validation",
        "target_agent": TARGET_AGENT_ID,
        "total_samples": len(rows),
        "memory_poison_proven_count": proven,
        "memory_poison_proven_rate": proven / len(rows) if rows else 0,
        "poison_retrieved_count": retrieved,
        "poison_retrieved_rate": retrieved / len(rows) if rows else 0,
        "attack_success_count": success,
        "attack_success_rate": success / len(rows) if rows else 0,
        "with_baseline": with_baseline,
        "prompt_mode": prompt_mode,
        "timestamp": datetime.now().isoformat(),
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"validation_{ts}.csv"
    json_path = RESULTS_DIR / f"validation_{ts}.json"
    _export_csv(rows, csv_path)
    _export_json({"summary": summary, "rows": rows}, json_path)

    print(f"\nMEMORY投毒成立: {proven}/{len(rows)} ({summary['memory_poison_proven_rate']:.1%})")
    print(f"毒记忆检索命中: {retrieved}/{len(rows)} ({summary['poison_retrieved_rate']:.1%})")
    print(f"攻击成功: {success}/{len(rows)} ({summary['attack_success_rate']:.1%})")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")

    return {"summary": summary, "csv_path": str(csv_path), "json_path": str(json_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="单 Agent MEMORY 投毒验证实验")
    parser.add_argument("--pilot", type=int, default=0, help="仅跑前 N 条（如 --pilot 5）")
    parser.add_argument("--no-baseline", action="store_true", help="跳过基线对照（更快）")
    parser.add_argument(
        "--prompt-mode",
        choices=["neutral", "trusting"],
        default="trusting",
        help="trusting 更易观察投毒影响（验证推荐）",
    )
    args = parser.parse_args()

    limit = args.pilot if args.pilot > 0 else None
    run_validation(
        limit=limit,
        with_baseline=not args.no_baseline,
        prompt_mode=args.prompt_mode,
    )


if __name__ == "__main__":
    main()
