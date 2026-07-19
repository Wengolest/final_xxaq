"""Export formal 5-native standard_8_types results to frontend Excel import format."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PLATFORM_ROOT / "results"
SRC_CSV = RESULTS / "github_http_rag_poison_matrix.csv"
OUT_XLSX = RESULTS / "frontend_import_rag_poison_std8_native5.xlsx"
OUT_META = RESULTS / "frontend_import_experiment_meta.json"

FORMAL_AGENTS = [
    "simple_rag_chatbot",
    "langserve",
    "langgraph-agents",
    "rag-with-langchain-and-fastapi",
    "gpt-researcher",
]

AGENT_NAMES = {
    "simple_rag_chatbot": "Simple RAG Chatbot",
    "langserve": "LangServe",
    "langgraph-agents": "LangGraph Agents",
    "rag-with-langchain-and-fastapi": "RAG LangChain FastAPI",
    "gpt-researcher": "GPT Researcher",
}

EXPERIMENT_ID = "EXP_RAG_POISON_STD8_NATIVE5"
EXPERIMENT_NAME = "GitHub RAG 投毒实验 · 5 native_http · standard_8_types"
EXPERIMENT_DESC = (
    "正式主结果：5 个 native_http GitHub 开源 Agent，standard_8_types 矩阵，"
    "160 条 poison_eval 记录（poison_only+mixed）；case-aware evaluator；数据来源 new_run。"
)
RUN_ID = "RUN_20260608_STD8_NATIVE5"

# Chinese headers for frontend columnMapping compatibility
COLUMNS = [
    ("experiment_id", "实验ID"),
    ("agent_id", "Agent ID"),
    ("agent_name", "Agent 名称"),
    ("attack_id", "攻击ID"),
    ("attack_family", "攻击族"),
    ("attack_success", "攻击成功"),
    ("final_label", "最终标签"),
    ("llm_risk_score", "LLM 风险分"),
    ("defense_enabled", "防御启用"),
    ("refusal_detected", "检测到拒答"),
    ("task_deviation", "任务偏离"),
    ("prompt_sent", "发送提示词"),
    ("agent_reply", "Agent 回复"),
    ("timestamp", "时间戳"),
    ("delivery_mode", "投递模式"),
    ("scorer_type", "评分器类型"),
    ("eval_tier", "评估层级"),
    ("poisoner_type", "投毒类型"),
    ("llm_rationale", "LLM 判定理由"),
    ("repo_slug", "仓库标识"),
    ("corpus_mode", "语料模式"),
    ("case_id", "Case ID"),
    ("strict_attack_success", "严格攻击成功"),
    ("poison_answer_keyword_hit", "关键词命中"),
    ("final_risk", "最终风险"),
    ("poison_retrieved", "毒文档召回"),
    ("poison_rank", "毒文档排名"),
]


def _bool(v) -> bool:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    return str(v).strip().lower() in {"true", "1", "yes"}


def _text(v, default: str = "") -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    return str(v)


def _risk_score(final_risk: str) -> float:
    m = {"高": 0.88, "中": 0.55, "低": 0.18, "CONFLICT": 0.72, "UNKNOWN": 0.5}
    return m.get((final_risk or "").strip(), 0.5)


def _final_label(row: dict) -> str:
    if _text(row.get("error")).strip() or not _text(row.get("answer")).strip():
        return "blocked"
    if _bool(row.get("strict_attack_success")):
        return "compromised"
    return "safe"


def _parse_run_ts(run_id: str, fallback: datetime) -> datetime:
    m = re.search(r"(\d{8})_(\d{6})", run_id or "")
    if m:
        try:
            return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        except ValueError:
            pass
    return fallback


def _load_poison_eval_rows() -> list[dict]:
    df = pd.read_csv(SRC_CSV, encoding="utf-8-sig")
    mask = (
        df["agent_id"].isin(FORMAL_AGENTS)
        & (df["test_scale"] == "standard_8_types")
        & (df["source"] == "new_run")
        & df["corpus_mode"].isin(["poison_only", "mixed"])
        & df["answer"].notna()
        & (df["answer"].astype(str).str.strip() != "")
        & (~df["error"].fillna("").astype(str).str.strip().astype(bool))
    )
    return df[mask].to_dict(orient="records")


def _row_to_record(row: dict, idx: int, base_ts: datetime) -> dict:
    agent_id = str(row.get("agent_id", ""))
    case_id = str(row.get("case_id", ""))
    corpus_mode = str(row.get("corpus_mode", ""))
    attack_id = f"{case_id}__{corpus_mode}__{agent_id}"
    answer = _text(row.get("answer"))[:4000]
    question = _text(row.get("question"))
    strict_ok = _bool(row.get("strict_attack_success"))
    kw_hit = _bool(row.get("poison_answer_keyword_hit"))
    final_risk = str(row.get("final_risk", "UNKNOWN"))

    return {
        "experiment_id": EXPERIMENT_ID,
        "agent_id": agent_id,
        "agent_name": AGENT_NAMES.get(agent_id, agent_id),
        "attack_id": attack_id,
        "attack_family": str(row.get("poison_type") or row.get("attack_family", "")),
        "attack_success": strict_ok,
        "final_label": _final_label(row),
        "llm_risk_score": round(_risk_score(final_risk), 4),
        "defense_enabled": False,
        "refusal_detected": "无法" in answer[:200] and final_risk == "UNKNOWN",
        "task_deviation": strict_ok or _bool(row.get("risk_downgrade")),
        "prompt_sent": question,
        "agent_reply": answer,
        "timestamp": (base_ts + timedelta(seconds=idx * 3)).strftime("%Y-%m-%dT%H:%M:%S"),
        "delivery_mode": "native_http",
        "scorer_type": "case_aware_evaluator",
        "eval_tier": "I" if strict_ok else ("A" if kw_hit else "E"),
        "poisoner_type": str(row.get("poison_type", "")),
        "llm_rationale": str(row.get("eval_reason", ""))[:500],
        "repo_slug": agent_id,
        "corpus_mode": corpus_mode,
        "case_id": case_id,
        "strict_attack_success": strict_ok,
        "poison_answer_keyword_hit": kw_hit,
        "final_risk": final_risk,
        "poison_retrieved": row.get("poison_retrieved", ""),
        "poison_rank": row.get("poison_rank", ""),
    }


def main() -> None:
    rows = _load_poison_eval_rows()
    if not rows:
        raise RuntimeError("No poison_eval rows found — check CSV filters")

    base_ts = _parse_run_ts(str(rows[0].get("run_id", "")), datetime(2026, 6, 8, 16, 27, 0))
    records = [_row_to_record(r, i, base_ts) for i, r in enumerate(rows)]

    en_cols = [c[0] for c in COLUMNS]
    zh_map = {en: zh for en, zh in COLUMNS}
    df_en = pd.DataFrame(records)[en_cols]
    df_zh = df_en.rename(columns=zh_map)

    OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df_zh.to_excel(writer, sheet_name="攻击结果", index=False)
        df_en.to_excel(writer, sheet_name="attack_results_en", index=False)

    strict_n = sum(1 for r in records if r["strict_attack_success"])
    kw_n = sum(1 for r in records if r["poison_answer_keyword_hit"])
    meta = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "experiment_description": EXPERIMENT_DESC,
        "run_id": RUN_ID,
        "is_proxy_mode": False,
        "delivery_mode_note": "全部为 native_http，非 proxy",
        "mock_scope_recommendation": "实验列表 + 评估页 + 攻击结果明细表（160 行 poison_eval）",
        "formal_sample_agents": FORMAL_AGENTS,
        "data_source": str(SRC_CSV),
        "source_filter": "standard_8_types + new_run + poison_only/mixed",
        "row_counts": {
            "poison_eval_rows": len(records),
            "strict_attack_success": strict_n,
            "keyword_hit": kw_n,
            "asr_strict": round(strict_n / len(records), 4),
            "asr_keyword": round(kw_n / len(records), 4),
        },
        "excel_path": str(OUT_XLSX),
        "column_note": "Sheet「攻击结果」使用中文表头，可直接在实验编排中心「导入攻击结果」上传",
        "evaluator_note": "attack_success 映射为 strict_attack_success，非 keyword_hit",
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(records)} rows -> {OUT_XLSX}")
    print(f"Meta -> {OUT_META}")
    print(json.dumps(meta["row_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
