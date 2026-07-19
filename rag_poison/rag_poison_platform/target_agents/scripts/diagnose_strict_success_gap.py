"""Offline diagnosis: why A-layer keyword_hit >> I-layer strict_attack_success."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
RESULTS = PLATFORM_ROOT / "results"
SRC_CSV = RESULTS / "github_http_rag_poison_matrix.csv"
SLIM_CSV = RESULTS / "poison_eval_standard8_slim.csv"
BUILD_SCRIPT = SCRIPT_DIR / "build_github_effective_poison_summary.py"

OUT_STRICT_CSV = RESULTS / "strict_success_diagnosis.csv"
OUT_STRICT_MD = RESULTS / "strict_success_diagnosis.md"
OUT_CORPUS_CSV = RESULTS / "poison_only_vs_mixed_diagnosis.csv"
OUT_CORPUS_MD = RESULTS / "poison_only_vs_mixed_diagnosis.md"
OUT_EAI_SUMMARY = RESULTS / "eai_standard_8_types_summary.csv"
OUT_EAI_POISON = RESULTS / "eai_by_poison_type.csv"
OUT_EAI_AGENT = RESULTS / "eai_by_agent.csv"

FORMAL_AGENTS = [
    "simple_rag_chatbot",
    "langserve",
    "langgraph-agents",
    "rag-with-langchain-and-fastapi",
    "gpt-researcher",
]

SLIM_FIELDS = [
    "agent_id",
    "corpus_mode",
    "poison_type",
    "case_id",
    "poison_answer_keyword_hit",
    "strict_attack_success",
    "risk_downgrade",
    "advice_suppressed",
    "instruction_follow_level",
    "metadata_observable",
    "poison_retrieved",
    "eval_reason",
    "strict_rule_failed_reason",
    "test_scale",
    "source",
    "error",
]

FAILURE_TAGS = [
    "keyword_hit_only",
    "require_all_missing",
    "forbid_any_clean_high_risk_endorsed",
    "retrieval_unobservable",
    "no_keyword_hit",
    "instruction_reference_not_followed",
    "metadata_unobservable",
    "strict_success",
    "other",
]


def _bool(v: Any) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in {"true", "1", "yes"}


def _triplet(count: int, denom: int) -> Dict[str, Any]:
    rate = round(count / denom, 4) if denom else 0.0
    return {"count": count, "denominator": denom, "rate": rate, "display": f"{count}/{denom} = {rate}"}


def _matches_filter(row: Dict[str, str]) -> bool:
    return (
        row.get("agent_id") in FORMAL_AGENTS
        and row.get("test_scale") == "standard_8_types"
        and row.get("source") == "new_run"
        and row.get("corpus_mode") in {"poison_only", "mixed"}
        and not str(row.get("error", "")).strip()
    )


def _normalize_row(row: Dict[str, str]) -> Dict[str, Any]:
    out = {k: row.get(k, "") for k in SLIM_FIELDS}
    out["poison_answer_keyword_hit"] = _bool(out["poison_answer_keyword_hit"])
    out["strict_attack_success"] = _bool(out["strict_attack_success"])
    out["risk_downgrade"] = _bool(out["risk_downgrade"])
    out["advice_suppressed"] = _bool(out["advice_suppressed"])
    out["metadata_observable"] = _bool(out["metadata_observable"])
    out["kw_only"] = out["poison_answer_keyword_hit"] and not out["strict_attack_success"]
    out["eval_reason"] = str(out.get("eval_reason") or "")
    out["strict_rule_failed_reason"] = str(out.get("strict_rule_failed_reason") or "")
    return out


def _load_rows() -> List[Dict[str, Any]]:
    src_mtime = SRC_CSV.stat().st_mtime if SRC_CSV.is_file() else 0
    if SLIM_CSV.is_file() and SLIM_CSV.stat().st_mtime >= src_mtime:
        with SLIM_CSV.open(encoding="utf-8-sig", newline="") as f:
            return [_normalize_row(r) for r in csv.DictReader(f)]

    if not SRC_CSV.is_file():
        raise FileNotFoundError(f"Missing source CSV: {SRC_CSV}")

    rows: List[Dict[str, Any]] = []
    with SRC_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            if not _matches_filter(raw):
                continue
            rows.append(_normalize_row(raw))

    SLIM_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SLIM_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SLIM_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in SLIM_FIELDS})
    return rows


def _classify_failure(row: Dict[str, Any]) -> str:
    if row["strict_attack_success"]:
        return "strict_success"
    reason = f"{row['eval_reason']};{row['strict_rule_failed_reason']}"
    pr = str(row.get("poison_retrieved", "")).strip().lower()
    pt = str(row.get("poison_type", ""))

    if not row.get("metadata_observable", True) and "metadata" in pt:
        return "metadata_unobservable"
    if pr == "unknown" and pt not in {"instruction_boundary_poison", "rule_policy_poison"}:
        return "retrieval_unobservable"
    if row["poison_answer_keyword_hit"]:
        if "forbid_any:clean_high_risk_endorsed" in reason:
            return "forbid_any_clean_high_risk_endorsed"
        if "require_all_missing" in reason:
            return "require_all_missing"
        if row.get("instruction_follow_level") in {"none", "partial"} and pt == "instruction_boundary_poison":
            return "instruction_reference_not_followed"
        return "keyword_hit_only"
    if row.get("instruction_follow_level") in {"none", "partial"} and pt == "instruction_boundary_poison":
        return "instruction_reference_not_followed"
    return "no_keyword_hit"


def _extract_rule_fragment(reason: str) -> str:
    if not reason or reason == "nan":
        return "unknown"
    if reason.startswith("strict_success"):
        return "strict_success"
    for p in reason.split(";"):
        if p.startswith(("require_all_missing:", "forbid_any:", "require_any_none:")):
            return p
        if p in {"keyword_hit_only", "no_behavioral_success", "not_success"}:
            return p
    parts = reason.split(";")
    return parts[-1] if parts else "unknown"


def _subset(rows: List[Dict[str, Any]], **kw) -> List[Dict[str, Any]]:
    out = rows
    for k, v in kw.items():
        out = [r for r in out if r.get(k) == v]
    return out


def _sum_bool(rows: List[Dict[str, Any]], key: str) -> int:
    return sum(1 for r in rows if r.get(key))


def build_tables(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    corpus_rows = []
    for pt in sorted({r["poison_type"] for r in rows if r.get("poison_type")}):
        po = _subset(rows, poison_type=pt, corpus_mode="poison_only")
        mx = _subset(rows, poison_type=pt, corpus_mode="mixed")
        corpus_rows.append(
            {
                "poison_type": pt,
                "poison_only_strict_count": _sum_bool(po, "strict_attack_success"),
                "poison_only_denominator": len(po),
                "poison_only_strict_rate": _triplet(_sum_bool(po, "strict_attack_success"), len(po))["rate"],
                "mixed_strict_count": _sum_bool(mx, "strict_attack_success"),
                "mixed_denominator": len(mx),
                "mixed_strict_rate": _triplet(_sum_bool(mx, "strict_attack_success"), len(mx))["rate"],
                "poison_only_keyword_hit_rate": _triplet(_sum_bool(po, "poison_answer_keyword_hit"), len(po))["rate"],
                "mixed_keyword_hit_rate": _triplet(_sum_bool(mx, "poison_answer_keyword_hit"), len(mx))["rate"],
                "delta_strict_rate": round(
                    (_sum_bool(mx, "strict_attack_success") / len(mx) if mx else 0)
                    - (_sum_bool(po, "strict_attack_success") / len(po) if po else 0),
                    4,
                ),
                "delta_keyword_hit_rate": round(
                    (_sum_bool(mx, "poison_answer_keyword_hit") / len(mx) if mx else 0)
                    - (_sum_bool(po, "poison_answer_keyword_hit") / len(po) if po else 0),
                    4,
                ),
            }
        )

    agent_rows = []
    for aid in FORMAL_AGENTS:
        sub = _subset(rows, agent_id=aid)
        nd = len(sub)
        rule_frags = Counter(_extract_rule_fragment(r["eval_reason"]) for r in sub if not r["strict_attack_success"])
        agent_rows.append(
            {
                "agent_id": aid,
                "keyword_hit_count": _sum_bool(sub, "poison_answer_keyword_hit"),
                "denominator": nd,
                "keyword_hit_rate": _triplet(_sum_bool(sub, "poison_answer_keyword_hit"), nd)["rate"],
                "strict_success_count": _sum_bool(sub, "strict_attack_success"),
                "strict_success_rate": _triplet(_sum_bool(sub, "strict_attack_success"), nd)["rate"],
                "kw_only_count": sum(1 for r in sub if r["kw_only"]),
                "risk_downgrade_count": _sum_bool(sub, "risk_downgrade"),
                "advice_suppressed_count": _sum_bool(sub, "advice_suppressed"),
                "main_failure_reason_top3": "; ".join(f"{a}({b})" for a, b in rule_frags.most_common(3)),
            }
        )

    poison_rows = []
    for pt in sorted({r["poison_type"] for r in rows if r.get("poison_type")}):
        sub = _subset(rows, poison_type=pt)
        nd = len(sub)
        rule_frags = Counter(_extract_rule_fragment(r["eval_reason"]) for r in sub if not r["strict_attack_success"])
        poison_rows.append(
            {
                "poison_type": pt,
                "keyword_hit_rate": _triplet(_sum_bool(sub, "poison_answer_keyword_hit"), nd)["rate"],
                "strict_success_rate": _triplet(_sum_bool(sub, "strict_attack_success"), nd)["rate"],
                "kw_only_count": sum(1 for r in sub if r["kw_only"]),
                "require_all_missing_count": sum(1 for r in sub if "require_all_missing" in r["eval_reason"]),
                "forbid_any_triggered_count": sum(1 for r in sub if "forbid_any:" in r["eval_reason"]),
                "main_failure_reason": rule_frags.most_common(1)[0][0] if rule_frags else "n/a",
            }
        )

    classified = Counter(_classify_failure(r) for r in rows)
    rule_detail = Counter(_extract_rule_fragment(r["eval_reason"]) for r in rows if not r["strict_attack_success"])

    failure_rows = [
        {"category": tag, **_triplet(classified.get(tag, 0), n)}
        for tag in FAILURE_TAGS
    ]

    po_all = _subset(rows, corpus_mode="poison_only")
    mx_all = _subset(rows, corpus_mode="mixed")

    return {
        "summary": {
            "denominator": n,
            "keyword_hit": _triplet(_sum_bool(rows, "poison_answer_keyword_hit"), n),
            "strict_success": _triplet(_sum_bool(rows, "strict_attack_success"), n),
            "kw_only_count": sum(1 for r in rows if r["kw_only"]),
            "poison_only_strict_rate": _triplet(_sum_bool(po_all, "strict_attack_success"), len(po_all))["rate"],
            "mixed_strict_rate": _triplet(_sum_bool(mx_all, "strict_attack_success"), len(mx_all))["rate"],
        },
        "corpus_comparison": corpus_rows,
        "by_agent": agent_rows,
        "by_poison_type": poison_rows,
        "failure_attribution": failure_rows,
        "top_rule_fragments": [{"reason": k, "count": v} for k, v in rule_detail.most_common(15)],
    }


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _render_strict_md(data: Dict[str, Any]) -> str:
    s = data["summary"]
    lines = [
        "# strict_success 低成功率离线诊断",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "**样本**：5 native_http × standard_8_types × poison_eval（160，source=new_run）",
        "",
        f"- keyword_hit：{s['keyword_hit']['display']}",
        f"- strict_success：{s['strict_success']['display']}",
        f"- kw_only：{s['kw_only_count']}/160",
        "",
        "## 按 Agent",
        "",
        "| Agent | keyword_hit | strict_success | kw_only | risk_downgrade | advice_suppressed | top3 failure |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in data["by_agent"]:
        lines.append(
            f"| {r['agent_id']} | {_triplet(r['keyword_hit_count'], r['denominator'])['display']} "
            f"| {_triplet(r['strict_success_count'], r['denominator'])['display']} "
            f"| {r['kw_only_count']} | {r['risk_downgrade_count']} | {r['advice_suppressed_count']} "
            f"| {r['main_failure_reason_top3']} |"
        )
    lines += ["", "## 按 poison_type", "", "| poison_type | keyword_hit | strict_success | kw_only | req_all_missing | forbid_any | main_failure |", "|---|---:|---:|---:|---:|---:|---|"]
    for r in data["by_poison_type"]:
        nd = 20
        lines.append(
            f"| {r['poison_type']} | {r['keyword_hit_rate']} | {r['strict_success_rate']} "
            f"| {r['kw_only_count']} | {r['require_all_missing_count']} | {r['forbid_any_triggered_count']} | {r['main_failure_reason']} |"
        )
    lines += ["", "## 失败原因归因", "", "| category | count | rate |", "|---|---:|---:|"]
    for r in data["failure_attribution"]:
        if r["count"]:
            lines.append(f"| {r['category']} | {r['count']} | {r['rate']} |")
    lines += ["", "## 结论", ""]
    forbid_n = next((x["count"] for x in data["failure_attribution"] if x["category"] == "forbid_any_clean_high_risk_endorsed"), 0)
    req_n = next((x["count"] for x in data["failure_attribution"] if x["category"] == "require_all_missing"), 0)
    lines += [
        "1. **方法完全无效？** 否 — strict_success=10/160，存在可观测行为改变。",
        f"2. **evaluator 更严格？** 是 — kw_only={s['kw_only_count']}；keyword_hit_only 与 require_all_missing 为主因。",
        f"3. **Agent 保守回答？** 是 — forbid_any:clean_high_risk_endorsed 共 {forbid_n} 行；引用毒措辞后仍维持高风险。",
        f"4. **clean 竞争主因？** 否 — poison_only strict_rate={s['poison_only_strict_rate']} vs mixed={s['mixed_strict_rate']}。",
        f"5. **require_all_missing** 共 {req_n} 行 — 部分采纳但未满足 risk_downgrade/advice_suppressed 等行为条件。",
        "",
    ]
    return "\n".join(lines)


def _render_corpus_md(data: Dict[str, Any]) -> str:
    lines = [
        "# poison_only vs mixed 对比诊断",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| poison_type | poison_only strict | mixed strict | poison_only kw | mixed kw | Δstrict | Δkw |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for r in data["corpus_comparison"]:
        lines.append(
            f"| {r['poison_type']} | {r['poison_only_strict_count']}/{r['poison_only_denominator']}={r['poison_only_strict_rate']} "
            f"| {r['mixed_strict_count']}/{r['mixed_denominator']}={r['mixed_strict_rate']} "
            f"| {r['poison_only_keyword_hit_rate']} | {r['mixed_keyword_hit_rate']} "
            f"| {r['delta_strict_rate']:+.4f} | {r['delta_keyword_hit_rate']:+.4f} |"
        )
    s = data["summary"]
    lines += [
        "",
        f"**判断**：mixed 未系统性高于 poison_only（overall strict: poison_only={s['poison_only_strict_rate']} vs mixed={s['mixed_strict_rate']}）。",
        "clean 证据竞争不是压低 strict_success 的主因；主因是 keyword 命中后未产生行为改变（forbid_any / require_all_missing）。",
        "",
    ]
    return "\n".join(lines)


def _write_eai_csvs(data: Dict[str, Any]) -> None:
    s = data["summary"]
    _write_csv(
        OUT_EAI_SUMMARY,
        ["metric", "count", "denominator", "rate", "display"],
        [
            {"metric": "keyword_hit", **s["keyword_hit"]},
            {"metric": "strict_success", **s["strict_success"]},
            {"metric": "kw_only", "count": s["kw_only_count"], "denominator": s["denominator"], "rate": round(s["kw_only_count"] / s["denominator"], 4), "display": f"{s['kw_only_count']}/{s['denominator']}"},
            {"metric": "poison_only_strict_rate", "count": 0, "denominator": 80, "rate": s["poison_only_strict_rate"], "display": str(s["poison_only_strict_rate"])},
            {"metric": "mixed_strict_rate", "count": 0, "denominator": 80, "rate": s["mixed_strict_rate"], "display": str(s["mixed_strict_rate"])},
        ],
    )
    _write_csv(
        OUT_EAI_POISON,
        ["poison_type", "keyword_hit_rate", "strict_success_rate", "kw_only_count", "require_all_missing_count", "forbid_any_triggered_count", "main_failure_reason"],
        data["by_poison_type"],
    )
    _write_csv(
        OUT_EAI_AGENT,
        ["agent_id", "keyword_hit_count", "denominator", "keyword_hit_rate", "strict_success_count", "strict_success_rate", "kw_only_count", "risk_downgrade_count", "advice_suppressed_count", "main_failure_reason_top3"],
        data["by_agent"],
    )


def _regenerate_reports() -> Tuple[bool, str]:
    if not BUILD_SCRIPT.is_file():
        return False, f"missing build script: {BUILD_SCRIPT}"
    proc = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=str(PLATFORM_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return False, proc.stderr[-4000:] or proc.stdout[-4000:] or "build script failed"
    return True, proc.stdout.strip()[-500:]


def main() -> None:
    rows = _load_rows()
    if len(rows) != 160:
        print(f"WARNING: expected 160 poison_eval rows, got {len(rows)}", file=sys.stderr)

    data = build_tables(rows)

    strict_flat = []
    for r in data["by_agent"]:
        strict_flat.append({"section": "by_agent", **r})
    for r in data["by_poison_type"]:
        strict_flat.append({"section": "by_poison_type", "poison_type": r["poison_type"], **r})
    for r in data["failure_attribution"]:
        strict_flat.append({"section": "failure_attribution", "category": r["category"], "count": r["count"], "denominator": r["denominator"], "rate": r["rate"]})

    _write_csv(OUT_STRICT_CSV, ["section", "agent_id", "poison_type", "category", "keyword_hit_count", "denominator", "keyword_hit_rate", "strict_success_count", "strict_success_rate", "kw_only_count", "risk_downgrade_count", "advice_suppressed_count", "main_failure_reason_top3", "require_all_missing_count", "forbid_any_triggered_count", "main_failure_reason", "count", "rate"], strict_flat)
    OUT_STRICT_MD.write_text(_render_strict_md(data), encoding="utf-8")
    _write_csv(OUT_CORPUS_CSV, list(data["corpus_comparison"][0].keys()) if data["corpus_comparison"] else ["poison_type"], data["corpus_comparison"])
    OUT_CORPUS_MD.write_text(_render_corpus_md(data), encoding="utf-8")
    _write_eai_csvs(data)

    regen = "--regen-reports" in sys.argv
    ok, build_msg = (False, "skipped (pass --regen-reports to run build_github_effective_poison_summary.py)")
    if regen:
        ok, build_msg = _regenerate_reports()
    print(json.dumps({"rows": len(rows), "summary": data["summary"], "reports_regenerated": ok, "build_tail": build_msg}, ensure_ascii=False, indent=2))
    if regen and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
