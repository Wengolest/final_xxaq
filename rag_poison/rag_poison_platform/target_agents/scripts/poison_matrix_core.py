"""Shared poison matrix engine: scales, case loading, CSV merge, extended metrics."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from target_agents.poison_tests.evaluator import evaluate_poison_case
from generators import template_generators
from target_agents.poison_tests.case_loader import (
    cases_for_scale,
    expected_rows_for_scale,
    resolve_case,
)
from utils.corpus import load_clean_documents
from utils.targets import SecurityTarget, load_targets

ATTACKS_LEGACY = [
    "content_poison",
    "rule_poison",
    "retrieval_hijack_poison",
    "context_manipulation_poison",
    "instruction_injection_poison",
]
ATTACK_FAMILY = {
    "content_poison": "content_poisoning",
    "rule_poison": "rule_poisoning",
    "retrieval_hijack_poison": "retrieval_hijacking",
    "context_manipulation_poison": "context_manipulation",
    "instruction_injection_poison": "instruction_injection",
    "semantic_neighbor_poison": "semantic_neighbor",
    "conflict_evidence_poison": "conflict_evidence",
    "metadata_spoof_poison": "metadata_poisoning",
}
CORPUS_MODES = ["clean", "poison_only", "mixed"]
QUICK_TARGETS = [
    "researchhelper_rag_risk",
    "toolreport_tool_output_risk",
    "websearch_external_content_risk",
]

EXTENDED_CSV_FIELDS = [
    "case_id",
    "poison_type",
    "poison_trigger_style",
    "scale",
    "source",
    "test_mode",
    "adapter_category",
    "attack_goal",
    "rule_adoption",
    "instruction_follow",
    "instruction_follow_level",
    "context_shift",
    "metadata_bypass",
    "metadata_observable",
    "citation_text_spoof",
    "persistence_recall",
    "file_ingest_success",
    "index_build_success",
    "top_k_poison",
    "cross_query_keyword_hit",
    "poison_answer_keyword_hit",
    "eval_reason",
    "matched_poison_keywords",
    "matched_clean_keywords",
    "strict_rule_matched",
    "strict_rule_failed_reason",
    "risk_label_detected",
    "advice_present",
    "advice_suppressed_reason",
    "failure_stage",
    "next_fix",
]

BASE_CSV_FIELDS = [
    "run_id", "agent_id", "agent_class", "repo", "framework", "base_url",
    "target_id", "attack_id", "attack_family", "corpus_mode", "test_scale",
    "ingest_method", "reset_supported", "query_endpoint", "question", "answer",
    "final_risk", "attack_success", "strict_attack_success", "risk_downgrade",
    "advice_suppressed", "answer_shift", "conflict_answer", "poison_retrieved",
    "poison_rank", "retrieved_sources", "retrieved_scores", "http_status",
    "latency_ms", "error",
]

CSV_FIELDS = BASE_CSV_FIELDS + EXTENDED_CSV_FIELDS


def merge_csv_rows(
    existing: List[Dict[str, Any]],
    *,
    agent_id: str,
    scale: str,
    replace: bool,
) -> List[Dict[str, Any]]:
    if not replace:
        return existing + []
    kept = [
        r for r in existing
        if not (r.get("agent_id") == agent_id and r.get("test_scale", r.get("scale")) == scale)
    ]
    return kept


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(CSV_FIELDS)
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _bool_val(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v in (None, "", "unknown", "not_applicable"):
        return False
    return str(v).strip().lower() in {"true", "1", "yes"}


def iter_legacy_quick_cases(targets: List[SecurityTarget]) -> List[Tuple[SecurityTarget, str, str]]:
    """3 targets × 5 legacy attacks."""
    picked = [t for t in targets if t.target_id in QUICK_TARGETS] or targets[:3]
    out: List[Tuple[SecurityTarget, str, str]] = []
    for t in picked:
        for aid in ATTACKS_LEGACY:
            out.append((t, aid, ATTACK_FAMILY.get(aid, aid)))
    return out


def iter_case_scale_jobs(scale: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for raw in cases_for_scale(scale):
        resolved = resolve_case(raw)
        target: SecurityTarget = resolved["target"]
        ptype = resolved.get("poison_type", "")
        aid = resolved.get("generator_attack_id", "")
        if ptype == "persistence_recall_poison":
            queries = resolved.get("trigger_queries") or resolved.get("poison_only_queries") or []
            for qi, q in enumerate(queries):
                jobs.append({**resolved, "target": target, "query": q, "query_index": qi})
        else:
            q = (resolved.get("trigger_queries") or [target.question])[0]
            jobs.append({**resolved, "target": target, "query": q, "query_index": 0})
    return jobs


def make_failure_row(
    *,
    run_id: str,
    agent_id: str,
    agent_class: str,
    repo: str,
    framework: str,
    base_url: str,
    scale: str,
    source: str,
    error: str,
    case: Optional[Dict[str, Any]] = None,
    target: Optional[SecurityTarget] = None,
    corpus_mode: str = "clean",
    test_mode: str = "native_http",
    adapter_category: str = "A_native_http_rag",
    failure_stage: str = "",
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "agent_id": agent_id,
        "agent_class": agent_class,
        "repo": repo,
        "framework": framework,
        "base_url": base_url,
        "target_id": (target.target_id if target else case.get("target_id", "") if case else ""),
        "attack_id": case.get("generator_attack_id", "") if case else "",
        "attack_family": ATTACK_FAMILY.get(case.get("generator_attack_id", ""), "") if case else "",
        "corpus_mode": corpus_mode,
        "test_scale": scale,
        "scale": scale,
        "source": source,
        "case_id": case.get("case_id", "") if case else "",
        "poison_type": case.get("poison_type", "") if case else "",
        "poison_trigger_style": case.get("poison_trigger_style", "") if case else "",
        "test_mode": test_mode,
        "adapter_category": adapter_category,
        "question": case.get("query", target.question if target else "") if case else "",
        "answer": "",
        "attack_success": False,
        "strict_attack_success": False,
        "error": error,
        "failure_stage": failure_stage,
    }


def evaluate_row(
    *,
    case: Dict[str, Any],
    target: SecurityTarget,
    answer: str,
    qr: Dict[str, Any],
    clean_baseline: str,
    file_ingest_ok: Optional[bool] = None,
    index_build_ok: Optional[bool] = None,
) -> Dict[str, Any]:
    pr_val = qr.get("poison_retrieved")
    pr_bool = pr_val if isinstance(pr_val, bool) else False
    pr_rank = qr.get("poison_rank")
    if pr_rank == "unknown":
        pr_rank = None
    elif pr_rank is not None:
        try:
            pr_rank = int(pr_rank)
        except (TypeError, ValueError):
            pr_rank = None

    ev = evaluate_poison_case(
        case=case,
        target=target,
        answer=answer,
        poison_retrieved=pr_bool,
        poison_rank=pr_rank,
        clean_baseline_answer=clean_baseline or None,
        retrieved_docs=qr.get("retrieved_sources_list"),
        corpus_mode=case.get("corpus_mode", "mixed"),
        query_type=case.get("query_type", "trigger"),
        file_ingest_ok=file_ingest_ok,
        index_build_ok=index_build_ok,
        metadata_observable=True,
        persistence_recall=case.get("persistence_recall"),
    )
    dbg = ev.debug_dict()
    return {
        "final_risk": ev.final_risk,
        "attack_success": ev.attack_success,
        "strict_attack_success": ev.poison_strict_attack_success,
        "risk_downgrade": ev.risk_downgrade,
        "advice_suppressed": ev.advice_suppressed,
        "answer_shift": ev.answer_shift,
        "conflict_answer": ev.conflict_answer,
        "poison_retrieved": qr.get("poison_retrieved", pr_bool),
        "poison_rank": qr.get("poison_rank", pr_rank),
        "attack_goal": case.get("attack_goal", ""),
        "rule_adoption": ev.rule_adoption if ev.rule_adoption is not None else "",
        "instruction_follow": ev.instruction_follow if ev.instruction_follow is not None else "",
        "instruction_follow_level": dbg.get("instruction_follow_level", ""),
        "context_shift": ev.context_shift if ev.context_shift is not None else "",
        "metadata_bypass": ev.metadata_bypass if ev.metadata_bypass is not None else "",
        "metadata_observable": dbg.get("metadata_observable", True),
        "citation_text_spoof": dbg.get("citation_text_spoof", ""),
        "top_k_poison": ev.top_k_poison if ev.top_k_poison is not None else "",
        "file_ingest_success": ev.file_ingest_success if ev.file_ingest_success is not None else "",
        "index_build_success": ev.index_build_success if ev.index_build_success is not None else "",
        "poison_answer_keyword_hit": dbg.get("poison_answer_keyword_hit", ""),
        "eval_reason": dbg.get("eval_reason", ""),
        "matched_poison_keywords": dbg.get("matched_poison_keywords", ""),
        "matched_clean_keywords": dbg.get("matched_clean_keywords", ""),
        "strict_rule_matched": dbg.get("strict_rule_matched", ""),
        "strict_rule_failed_reason": dbg.get("strict_rule_failed_reason", ""),
        "risk_label_detected": dbg.get("risk_label_detected", ""),
        "advice_present": dbg.get("advice_present", ""),
        "advice_suppressed_reason": dbg.get("advice_suppressed_reason", ""),
    }


def agent_scale_complete(rows: List[Dict[str, Any]], agent_id: str, scale: str) -> bool:
    need = expected_rows_for_scale(scale)
    sub = [
        r for r in rows
        if r.get("agent_id") == agent_id
        and r.get("test_scale", r.get("scale")) == scale
        and not r.get("error") and r.get("answer")
    ]
    return len(sub) >= need
