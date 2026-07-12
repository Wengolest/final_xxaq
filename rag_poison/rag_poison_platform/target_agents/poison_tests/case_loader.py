"""Load poison test cases and resolve documents / generators."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from generators.case_driven_generators import generate_poison_documents_for_case
from utils.corpus import load_clean_documents
from utils.targets import SecurityTarget, get_target_by_id

CASES_PATH = Path(__file__).resolve().parent / "poison_test_cases.yaml"

POISON_TYPE_GENERATORS = {
    "content_fact_poison": "content_poison",
    "rule_policy_poison": "rule_poison",
    "keyword_retrieval_hijack": "retrieval_hijack_poison",
    "semantic_neighbor_poison": "semantic_neighbor_poison",
    "citation_metadata_spoof": "metadata_spoof_poison",
    "conflict_evidence_poison": "conflict_evidence_poison",
    "context_boundary_poison": "context_manipulation_poison",
    "instruction_boundary_poison": "instruction_injection_poison",
    "file_corpus_poison": "content_poison",
    "persistence_recall_poison": "retrieval_hijack_poison",
}

STANDARD_8_TYPES = {
    "content_fact_poison",
    "rule_policy_poison",
    "keyword_retrieval_hijack",
    "semantic_neighbor_poison",
    "citation_metadata_spoof",
    "conflict_evidence_poison",
    "context_boundary_poison",
    "instruction_boundary_poison",
}

FULL_10_TYPES = set(POISON_TYPE_GENERATORS.keys())


def load_poison_cases(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    p = path or CASES_PATH
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("cases", []))


def cases_for_scale(scale: str) -> List[Dict[str, Any]]:
    all_cases = load_poison_cases()
    if scale == "standard_8_types":
        return [c for c in all_cases if c.get("poison_type") in STANDARD_8_TYPES]
    if scale == "full_10_types":
        return [c for c in all_cases if c.get("poison_type") in FULL_10_TYPES]
    return []


def expected_rows_for_scale(scale: str) -> int:
    if scale == "quick_3_targets":
        return 45
    cases = cases_for_scale(scale)
    modes = 3
    extra = 0
    for c in cases:
        if c.get("poison_type") == "persistence_recall_poison":
            nq = len(c.get("trigger_queries") or c.get("poison_only_queries") or [])
            extra += max(0, nq - 1) * modes
    return len(cases) * modes + extra


def _filter_clean_docs(all_docs: List[Dict[str, Any]], doc_ids: List[str]) -> List[Dict[str, Any]]:
    wanted = set(doc_ids)
    picked = [
        d for d in all_docs
        if d.get("doc_id") in wanted or d.get("rel_path", "").replace("/", "__") in wanted
    ]
    if not picked:
        return all_docs[: min(5, len(all_docs))]
    return picked


def _has_explicit_docs(docs: Any) -> bool:
    return isinstance(docs, list) and len(docs) > 0


def resolve_case(
    case: Dict[str, Any],
    *,
    targets: Optional[List[SecurityTarget]] = None,
) -> Dict[str, Any]:
    """Resolve clean/poison documents: explicit case docs win; else case-driven generation."""
    target = get_target_by_id(case["target_id"], targets)

    if _has_explicit_docs(case.get("clean_documents")):
        clean_docs = list(case["clean_documents"])
    else:
        all_clean = load_clean_documents()
        clean_docs = _filter_clean_docs(all_clean, case.get("clean_document_ids", []))

    if _has_explicit_docs(case.get("poison_documents")):
        poison_docs = list(case["poison_documents"])
    else:
        poison_docs = generate_poison_documents_for_case(case, target)

    attack_id = (
        case.get("generator_attack_id")
        or POISON_TYPE_GENERATORS.get(case.get("poison_type", ""), "content_poison")
    )

    return {
        **case,
        "target": target,
        "clean_documents": clean_docs,
        "poison_documents": poison_docs,
        "generator_attack_id": attack_id,
    }


REQUIRED_CASE_FIELDS = (
    "case_id",
    "poison_type",
    "domain",
    "attack_goal",
    "clean_documents",
    "poison_documents",
    "clean_queries",
    "trigger_queries",
    "poison_only_queries",
    "expected_clean_answer_keywords",
    "poison_target_keywords",
    "strict_attack_success_rule",
    "risk_label_clean",
    "risk_label_poison_target",
    "evaluation_flags",
    "metadata",
    "notes",
)


def _case_has_documents(case: Dict[str, Any]) -> bool:
    if _has_explicit_docs(case.get("clean_documents")) and _has_explicit_docs(case.get("poison_documents")):
        return True
    if _has_explicit_docs(case.get("clean_documents")) or _has_explicit_docs(case.get("poison_documents")):
        return bool(case.get("clean_document_ids")) or bool(case.get("poison_type"))
    return bool(case.get("clean_document_ids")) and bool(case.get("poison_type"))


def validate_cases(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    cases = cases or load_poison_cases()
    by_type: Dict[str, List[str]] = {}
    field_issues: List[str] = []

    for c in cases:
        ptype = c.get("poison_type", "")
        by_type.setdefault(ptype, []).append(c.get("case_id", ""))
        cid = c.get("case_id", "?")
        for f in REQUIRED_CASE_FIELDS:
            if f not in c or c[f] is None:
                field_issues.append(f"{cid}: missing {f}")
        if not c.get("attack_goal"):
            field_issues.append(f"{cid}: empty attack_goal")
        if not _case_has_documents(c):
            field_issues.append(f"{cid}: missing documents source")
        if not c.get("clean_queries"):
            field_issues.append(f"{cid}: clean_queries empty")
        if not c.get("trigger_queries"):
            field_issues.append(f"{cid}: trigger_queries empty")
        rule = c.get("strict_attack_success_rule")
        if not rule:
            field_issues.append(f"{cid}: missing strict_attack_success_rule")

    required_types = list(POISON_TYPE_GENERATORS.keys())
    missing_types = [t for t in required_types if len(by_type.get(t, [])) < 2]
    return {
        "total_cases": len(cases),
        "by_poison_type": {k: len(v) for k, v in by_type.items()},
        "types_complete": len(missing_types) == 0,
        "missing_types": missing_types,
        "fields_complete": len(field_issues) == 0,
        "field_issues": field_issues[:30],
    }
