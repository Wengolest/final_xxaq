# -*- coding: utf-8 -*-
"""实验结果 CSV 导出：英文列名后附中文翻译，含完整审计字段。"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# 攻击/基线实验明细列
CSV_COLUMNS = [
    ("experiment_type", "实验类型"),
    ("sample_id", "样本编号"),
    ("attack_method", "攻击手段"),
    ("attack_method_cn", "攻击手段中文"),
    ("implementation_tier", "实现层级"),
    ("target_agent", "目标Agent"),
    ("target_agent_cn", "目标Agent中文"),
    ("poison_req", "投毒请求"),
    ("poison_resp", "投毒响应"),
    ("victim_query", "受害者查询"),
    ("attack_success", "攻击是否成功"),
    ("baseline_malicious", "基线是否恶意"),
    ("poison_retrieved", "是否检索到毒记忆"),
    ("rule_hit", "规则是否命中"),
    ("llm_adopted", "LLM是否判定采纳"),
    ("retrieved_count", "检索记忆条数"),
    ("top_memory_source", "Top1记忆来源"),
    ("agent_response", "Agent输出"),
    ("memory_db_path", "记忆库路径"),
    ("metagpt_pool_synced", "MetaGPT经验池同步"),
    ("defense_mode", "防御模式"),
    ("defense_applicable", "防御是否适用"),
    ("defense_success", "防御是否成功"),
    ("defense_filtered_count", "防御过滤条数"),
    ("repeat_index", "重复序号"),
    ("prompt_mode", "Prompt模式"),
    ("persistent_mode", "持久污染模式"),
    ("timestamp", "时间戳"),
]

# 防御消融专用列
ABLATION_COLUMNS = [
    ("sample_id", "样本编号"),
    ("defense_mode", "防御模式"),
    ("still_compromised", "防御后仍被攻陷"),
    ("defense_blocked", "防御是否拦截"),
    ("agent_response", "Agent输出"),
    ("timestamp", "时间戳"),
]

ATTACK_METHOD_CN = {
    "memory_graft": "经验池嫁接投毒",
    "rag_vector_drift": "RAG向量漂移投毒",
    "schema_spoof": "文档Schema伪造投毒",
    "minja_injection": "MINJA查询注入攻击",
}

AGENT_NAME_CN = {
    "metagpt_data_interpreter": "MetaGPT数据分析智能体",
    "metagpt_rag_analyst": "MetaGPT RAG分析智能体",
    "ci_pipeline_agent": "CI/CD流水线智能体",
    "customer_support_agent": "客服支持智能体",
    "code_review_agent": "代码审查智能体",
}


def _fmt_bool_or_na(value: Any) -> str:
    """将布尔或 None 格式化为 CSV 单元格。"""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return str(value)
    return str(value)


def export_results(
    rows: list[dict[str, Any]],
    output_dir: Path,
    prefix: str,
) -> Path:
    """导出实验结果到指定目录下的 CSV。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{prefix}.csv"
    headers = [f"{en}（{cn}）" for en, cn in CSV_COLUMNS]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            cells = []
            for en, _ in CSV_COLUMNS:
                val = row.get(en, "")
                if en in ("defense_success", "defense_applicable"):
                    cells.append(_fmt_bool_or_na(val))
                else:
                    cells.append(val)
            writer.writerow(cells)
    return filepath


def export_ablation(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    """导出防御消融实验 CSV。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "defense_ablation.csv"
    headers = [f"{en}（{cn}）" for en, cn in ABLATION_COLUMNS]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(en, "") for en, _ in ABLATION_COLUMNS])
    return filepath


def export_summary(summary: dict[str, Any], output_dir: Path) -> Path:
    """导出攻击/防御汇总统计 CSV。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "summary.csv"

    headers = ["metric（指标）", "value（数值）", "description（说明）"]

    def _pct(key: str) -> str:
        v = summary.get(key)
        if v is None:
            return "N/A"
        return f"{float(v):.1%}"

    rows = [
        ("total_samples", summary.get("total_samples", 0), "总样本数"),
        ("experiment_type", summary.get("experiment_type", "attack"), "实验类型"),
        ("prompt_mode", summary.get("prompt_mode", ""), "Prompt模式"),
        ("persistent_mode", summary.get("persistent_mode", False), "持久污染模式"),
        ("repeats", summary.get("repeats", 1), "每条样本重复次数"),
        ("attack_success_count", summary.get("attack_success_count", 0), "攻击成功次数"),
        ("attack_success_rate", _pct("attack_success_rate"), "攻击成功率"),
        ("attack_success_rate_mean", _pct("attack_success_rate_mean"), "攻击成功率均值(重复实验)"),
        ("attack_success_rate_std", f"{summary.get('attack_success_rate_std', 0):.3f}", "攻击成功率标准差"),
        ("baseline_malicious_count", summary.get("baseline_malicious_count", 0), "基线恶意回复次数"),
        ("baseline_malicious_rate", _pct("baseline_malicious_rate"), "基线恶意率"),
        ("defense_applicable_count", summary.get("defense_applicable_count", 0), "防御适用样本数(攻击已成功)"),
        ("defense_block_count", summary.get("defense_block_count", 0), "防御拦截次数"),
        ("defense_block_rate", _pct("defense_block_rate"), "防御拦截率(分母=攻击成功数)"),
        ("defense_na_count", summary.get("defense_na_count", 0), "防御不适用样本数"),
        ("agents_tested", summary.get("agents_tested", 0), "参与测试Agent数"),
        ("pilot_mode", summary.get("pilot_mode", False), "是否试跑模式"),
        ("holdout_mode", summary.get("holdout_mode", False), "是否Holdout集"),
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    # 同时写 JSON 方便程序读取
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return filepath
