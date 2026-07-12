# -*- coding: utf-8 -*-
"""实验编排器：攻击、基线、持久污染、防御消融与重复实验。"""

from __future__ import annotations

import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from plugin.agents import create_all_agents
from plugin.agents.base_agent import BaseMemoryAgent
from plugin.attacks.injector import AttackInjector
from plugin.config import AGENT_DB_DIR, DATA_DIR, PILOT_SAMPLES, RESULTS_DIR
from plugin.csv_exporter import (
    AGENT_NAME_CN,
    ATTACK_METHOD_CN,
    export_ablation,
    export_results,
    export_summary,
)
from plugin.defense.defender import MemoryDefender
from plugin.evaluator import AttackEvaluator
from plugin.experiment_output import create_run_directory, write_latest_pointer
from plugin.llm_client import DeepSeekClient
from plugin.sample_loader import load_attack_samples

# 防御消融需测试的模式列表
DEFENSE_MODES = ["none", "signature_only", "trust_only", "provenance_only", "full"]


class ExperimentRunner:
    """端到端 MEMORY 投毒实验运行器。"""

    def __init__(
        self,
        *,
        pilot: bool = False,
        prompt_mode: str = "neutral",
        repeats: int = 1,
        persistent: bool = False,
        holdout: bool = False,
        experiment_type: str = "attack",
    ) -> None:
        self.pilot = pilot
        self.prompt_mode = prompt_mode
        self.repeats = max(1, repeats)
        self.persistent = persistent
        self.holdout = holdout
        self.experiment_type = experiment_type  # attack | baseline

        self.llm = DeepSeekClient(prompt_mode=prompt_mode)
        self.injector = AttackInjector()
        self.evaluator = AttackEvaluator(llm=self.llm)
        self.defender = MemoryDefender(mode="full")
        self.agents = create_all_agents(AGENT_DB_DIR, llm=self.llm)
        self.samples = self._load_samples()
        self._persistent_initialized = False

    def _samples_path(self) -> Path:
        """根据 holdout 标志选择样本文件。"""
        if self.holdout:
            return DATA_DIR / "attack_samples_holdout.json"
        return DATA_DIR / "attack_samples.json"

    def _load_samples(self) -> list[dict]:
        """加载攻击样本；试跑模式仅取前 N 条。"""
        limit = PILOT_SAMPLES if self.pilot else None
        return load_attack_samples(
            self._samples_path(),
            holdout=self.holdout,
            pilot_limit=limit,
        )

    def _ensure_agent_state(self, agent: BaseMemoryAgent, agent_id: str) -> None:
        """按实验模式初始化 Agent 记忆库。"""
        if self.persistent:
            # 持久模式：全程仅 reset 一次
            if not self._persistent_initialized:
                agent.reset()
            return
        # 隔离模式：每条样本前清空
        agent.reset()

    def _init_persistent_if_needed(self) -> None:
        """持久污染模式：实验开始时为所有 Agent 播种良性记忆。"""
        if self.persistent and not self._persistent_initialized:
            for agent in self.agents.values():
                agent.reset()
            self._persistent_initialized = True

    def _run_with_defense(
        self,
        agent: BaseMemoryAgent,
        query: str,
        defense_mode: str = "full",
    ) -> dict[str, Any]:
        """带指定防御模式的记忆检索 + LLM 推理。"""
        raw_memories = agent.retrieve(query, top_k=5)
        memory_payload = [
            {
                "request": m["request"],
                "response": m["response"],
                "tag": m.get("tag", ""),
                "source": m.get("source", "benign"),
                "trust_score": m.get("trust_score", 1.0),
            }
            for m in raw_memories
        ]
        defender = MemoryDefender(mode=defense_mode)
        filtered = defender.filter_memories(memory_payload)
        # 防御后若无安全记忆，仅回退到良性来源
        if not filtered:
            filtered = [m for m in memory_payload if m.get("source") != "poisoned"]

        response = self.llm.chat_with_memories(
            system=agent.system_prompt,
            user_query=query,
            memories=filtered,
        )
        return {
            "agent_id": agent.agent_id,
            "query": query,
            "retrieved_memories": filtered,
            "raw_retrieved_count": len(memory_payload),
            "defense_filtered_count": len(memory_payload) - len(filtered),
            "response": response,
        }

    def _build_row(
        self,
        sample: dict,
        *,
        attack_eval: dict | None = None,
        defense_eval: dict | None = None,
        agent_output: dict | None = None,
        inject_info: dict | None = None,
        repeat_index: int = 1,
        defense_mode: str = "full",
        defense_filtered_count: int = 0,
    ) -> dict[str, Any]:
        """组装单行 CSV 记录。"""
        agent_id = sample["target_agent"]
        row: dict[str, Any] = {
            "experiment_type": self.experiment_type,
            "sample_id": sample["sample_id"],
            "attack_method": sample.get("attack_method", ""),
            "attack_method_cn": ATTACK_METHOD_CN.get(sample.get("attack_method", ""), ""),
            "implementation_tier": sample.get("implementation_tier", "simulated"),
            "target_agent": agent_id,
            "target_agent_cn": AGENT_NAME_CN.get(agent_id, ""),
            "poison_req": sample.get("poison_req", ""),
            "poison_resp": sample.get("poison_resp", ""),
            "victim_query": sample.get("victim_query", ""),
            "repeat_index": repeat_index,
            "prompt_mode": self.prompt_mode,
            "persistent_mode": self.persistent,
            "timestamp": datetime.now().isoformat(),
        }

        if self.experiment_type == "baseline":
            baseline_eval = attack_eval or {}
            row.update({
                "attack_success": False,
                "baseline_malicious": baseline_eval.get("baseline_malicious", False),
                "poison_retrieved": False,
                "rule_hit": baseline_eval.get("rule_hit", False),
                "llm_adopted": baseline_eval.get("llm_adopted", False),
                "retrieved_count": baseline_eval.get("retrieved_count", 0),
                "top_memory_source": baseline_eval.get("top_memory_source", ""),
                "agent_response": (agent_output or {}).get("response", ""),
                "memory_db_path": str(self.agents[agent_id].db_path),
                "metagpt_pool_synced": False,
                "defense_mode": "N/A",
                "defense_applicable": False,
                "defense_success": None,
                "defense_filtered_count": 0,
            })
            return row

        attack_eval = attack_eval or {}
        defense_eval = defense_eval or {}
        row.update({
            "attack_success": attack_eval.get("attack_success", False),
            "baseline_malicious": False,
            "poison_retrieved": attack_eval.get("poison_retrieved", False),
            "rule_hit": attack_eval.get("rule_hit", False),
            "llm_adopted": attack_eval.get("llm_adopted", False),
            "retrieved_count": attack_eval.get("retrieved_count", 0),
            "top_memory_source": attack_eval.get("top_memory_source", ""),
            "agent_response": (agent_output or {}).get("response", ""),
            "memory_db_path": (inject_info or {}).get("memory_db", ""),
            "metagpt_pool_synced": (inject_info or {}).get("metagpt_pool_synced", False),
            "defense_mode": defense_mode,
            "defense_applicable": defense_eval.get("defense_applicable", False),
            "defense_success": defense_eval.get("defense_success"),
            "defense_filtered_count": defense_filtered_count,
        })
        return row

    def run_single_baseline(self, sample: dict, repeat_index: int = 1) -> dict[str, Any]:
        """无投毒基线：reset → 查询 → 检测是否意外恶意。"""
        agent = self.agents[sample["target_agent"]]
        self._ensure_agent_state(agent, sample["target_agent"])
        agent_output = agent.run(sample["victim_query"])
        baseline_eval = self.evaluator.evaluate_baseline(sample, agent_output)
        return self._build_row(
            sample,
            attack_eval=baseline_eval,
            agent_output=agent_output,
            repeat_index=repeat_index,
        )

    def run_single_attack(self, sample: dict, repeat_index: int = 1) -> dict[str, Any]:
        """单条攻击：投毒 → 查询 → 评估 → 防御复测。"""
        agent_id = sample["target_agent"]
        agent = self.agents[agent_id]
        self._ensure_agent_state(agent, agent_id)

        inject_info = self.injector.inject(agent, sample)
        agent_output = agent.run(sample["victim_query"])
        attack_eval = self.evaluator.evaluate_attack(sample, agent_output)

        defended_output = self._run_with_defense(agent, sample["victim_query"], "full")
        defense_eval = self.evaluator.evaluate_defense(
            sample, defended_output, attack_eval["attack_success"]
        )

        return self._build_row(
            sample,
            attack_eval=attack_eval,
            defense_eval=defense_eval,
            agent_output=agent_output,
            inject_info=inject_info,
            repeat_index=repeat_index,
            defense_filtered_count=defended_output.get("defense_filtered_count", 0),
        )

    def run_defense_ablation(self, successful_samples: list[dict]) -> list[dict[str, Any]]:
        """对攻击成功样本跑五种防御模式消融。"""
        ablation_rows: list[dict[str, Any]] = []
        for sample in successful_samples:
            agent = self.agents[sample["target_agent"]]
            # 消融需保证毒记忆仍在库中：隔离模式下重新注入
            if not self.persistent:
                agent.reset()
                self.injector.inject(agent, sample)

            for mode in DEFENSE_MODES:
                output = self._run_with_defense(agent, sample["victim_query"], mode)
                still = self.evaluator._llm_judge_adoption(
                    sample["poison_resp"], output["response"]
                )
                ablation_rows.append({
                    "sample_id": sample["sample_id"],
                    "defense_mode": mode,
                    "still_compromised": still,
                    "defense_blocked": not still,
                    "agent_response": output["response"],
                    "timestamp": datetime.now().isoformat(),
                })
                time.sleep(0.3)
        return ablation_rows

    def _compute_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """从明细行计算汇总指标。"""
        total = len(rows)
        if self.experiment_type == "baseline":
            malicious = sum(1 for r in rows if r.get("baseline_malicious"))
            return {
                "total_samples": total,
                "experiment_type": "baseline",
                "prompt_mode": self.prompt_mode,
                "persistent_mode": self.persistent,
                "repeats": self.repeats,
                "baseline_malicious_count": malicious,
                "baseline_malicious_rate": malicious / total if total else 0,
                "agents_tested": len({r.get("target_agent") for r in rows}),
                "pilot_mode": self.pilot,
                "holdout_mode": self.holdout,
            }

        attack_ok = sum(1 for r in rows if r.get("attack_success"))
        applicable = [r for r in rows if r.get("defense_applicable") is True]
        blocked = sum(1 for r in applicable if r.get("defense_success") is True)
        na_count = sum(1 for r in rows if r.get("defense_applicable") is False)

        # 按样本聚合重复实验成功率
        by_sample: dict[str, list[bool]] = {}
        for r in rows:
            by_sample.setdefault(r["sample_id"], []).append(bool(r.get("attack_success")))
        per_sample_rates = [
            sum(v) / len(v) for v in by_sample.values() if v
        ]
        rate_mean = statistics.mean(per_sample_rates) if per_sample_rates else 0
        rate_std = statistics.stdev(per_sample_rates) if len(per_sample_rates) > 1 else 0

        return {
            "total_samples": total,
            "experiment_type": "attack",
            "prompt_mode": self.prompt_mode,
            "persistent_mode": self.persistent,
            "repeats": self.repeats,
            "attack_success_count": attack_ok,
            "attack_success_rate": attack_ok / total if total else 0,
            "attack_success_rate_mean": rate_mean,
            "attack_success_rate_std": rate_std,
            "defense_applicable_count": len(applicable),
            "defense_block_count": blocked,
            "defense_block_rate": blocked / len(applicable) if applicable else 0,
            "defense_na_count": na_count,
            "agents_tested": len({r.get("target_agent") for r in rows}),
            "pilot_mode": self.pilot,
            "holdout_mode": self.holdout,
        }

    def run_all(self, output_dir: Path | None = None) -> dict[str, Any]:
        """运行全部实验并导出到独立时间戳目录。"""
        run_dir = output_dir or create_run_directory(RESULTS_DIR)
        mode_label = "pilot" if self.pilot else "full"
        exp_label = self.experiment_type
        if self.holdout:
            mode_label = f"holdout_{mode_label}"

        print(f"\n{'='*60}")
        print(
            f"  MEMORY 实验 [{exp_label}/{mode_label}]  "
            f"样本={len(self.samples)} 重复={self.repeats}  "
            f"prompt={self.prompt_mode}  persistent={self.persistent}"
        )
        print(f"  输出目录: {run_dir}")
        print(f"{'='*60}\n")

        self._init_persistent_if_needed()

        rows: list[dict[str, Any]] = []
        run_fn = (
            self.run_single_baseline
            if self.experiment_type == "baseline"
            else self.run_single_attack
        )

        for i, sample in enumerate(self.samples, 1):
            for rep in range(1, self.repeats + 1):
                rep_tag = f" r{rep}/{self.repeats}" if self.repeats > 1 else ""
                print(
                    f"[{i}/{len(self.samples)}]{rep_tag} "
                    f"{sample['sample_id']} -> {sample['target_agent']}"
                )
                try:
                    row = run_fn(sample, repeat_index=rep)
                    rows.append(row)
                    if self.experiment_type == "baseline":
                        status = "MALICIOUS" if row.get("baseline_malicious") else "OK"
                        print(f"    基线: {status}")
                    else:
                        atk = "SUCCESS" if row["attack_success"] else "FAIL"
                        if row.get("defense_applicable"):
                            def_s = "BLOCKED" if row["defense_success"] else "PASSTHROUGH"
                        else:
                            def_s = "N/A"
                        print(f"    攻击: {atk}  |  防御: {def_s}")
                except Exception as exc:
                    print(f"    错误: {exc}")
                    rows.append({
                        "sample_id": sample["sample_id"],
                        "experiment_type": self.experiment_type,
                        "attack_success": False,
                        "agent_response": f"ERROR: {exc}",
                        "defense_success": None,
                        "timestamp": datetime.now().isoformat(),
                    })
                time.sleep(0.4)

        summary = self._compute_summary(rows)
        prefix = f"{exp_label}_results_{mode_label}"
        csv_path = export_results(rows, run_dir, prefix)
        summary_path = export_summary(summary, run_dir)

        if self.experiment_type == "attack":
            print(
                f"\n攻击成功率: {summary['attack_success_rate']:.1%} "
                f"({summary['attack_success_count']}/{summary['total_samples']})"
            )
            if self.repeats > 1:
                print(
                    f"重复实验均值: {summary['attack_success_rate_mean']:.1%} "
                    f"± {summary['attack_success_rate_std']:.3f}"
                )
            print(
                f"防御拦截率: {summary['defense_block_rate']:.1%} "
                f"({summary['defense_block_count']}/{summary['defense_applicable_count']})"
            )
        else:
            print(
                f"\n基线恶意率: {summary['baseline_malicious_rate']:.1%} "
                f"({summary['baseline_malicious_count']}/{summary['total_samples']})"
            )

        print(f"结果 CSV: {csv_path}")
        print(f"汇总 CSV: {summary_path}")

        write_latest_pointer(RESULTS_DIR, run_dir, {
            "experiment_type": self.experiment_type,
            "pilot_mode": self.pilot,
            "holdout_mode": self.holdout,
            "summary": summary,
        })

        return {
            "rows": rows,
            "summary": summary,
            "csv_path": str(csv_path),
            "run_dir": str(run_dir),
        }

    def run_ablation_and_export(self, attack_rows: list[dict], run_dir: Path) -> Path:
        """基于攻击成功样本运行防御消融并导出。"""
        successful_ids = {
            r["sample_id"] for r in attack_rows if r.get("attack_success")
        }
        samples = [s for s in self.samples if s["sample_id"] in successful_ids]
        if not samples:
            print("[消融] 无攻击成功样本，跳过防御消融。")
            return run_dir / "defense_ablation.csv"

        print(f"\n>>> 防御消融：{len(samples)} 条成功样本 × {len(DEFENSE_MODES)} 种模式")
        ablation_rows = self.run_defense_ablation(samples)
        path = export_ablation(ablation_rows, run_dir)
        print(f"消融 CSV: {path}")
        return path
