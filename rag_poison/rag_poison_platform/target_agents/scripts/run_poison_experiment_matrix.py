"""Formal poison experiment matrix: 4 styles × cases × local variants, clean vs poisoned."""

from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from evaluators.answer_eval import evaluate_answer
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from target_agents.bulk_common import RESULTS_DIR, write_csv
from target_agents.local_variants.registry import build_local_variants
from target_agents.poison_tests.case_loader import load_poison_cases, resolve_case, validate_cases
from utils.deepseek_env import deepseek_available
from utils.env_bootstrap import bootstrap_api_env
from utils.targets import load_targets

MATRIX_CSV = RESULTS_DIR / "poison_experiment_matrix.csv"
HARNESS_URL = "http://127.0.0.1:18100"

MATRIX_FIELDS = [
    "run_id",
    "case_id",
    "domain",
    "corpus_domain",
    "poison_trigger_style",
    "phase",
    "corpus_mode",
    "query_type",
    "query_text",
    "agent_id",
    "sample_type",
    "model_backend",
    "retrieval_profile",
    "retrieval_top_k",
    "generator_attack_id",
    "poison_retrieved",
    "poison_rank",
    "poison_retrieval_hit",
    "poison_answer_keyword_hit",
    "poison_strict_attack_success",
    "poison_answer_success",
    "clean_query_poison_retrieval",
    "clean_query_answer_keyword_contamination",
    "clean_query_strict_contamination",
    "clean_contamination",
    "expected_clean_keywords_hit",
    "poison_target_keywords_hit",
    "attack_success",
    "final_risk",
    "answer_excerpt",
    "server_url",
    "used_harness_fallback",
    "error",
]

DEFAULT_VARIANT_IDS = [
    "local_rag_mock_tfidf_top5",
    "local_rag_mock_poison_boost_top5",
    "local_rag_deepseek_tfidf_top5",
    "local_rag_deepseek_poison_boost_top5",
]


def _make_run_id() -> str:
    return f"poison_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _top_k_from_profile(profile: str) -> int:
    if "top10" in profile:
        return 10
    return 5


def _keywords_hit(text: str, keywords: List[str], *, min_hits: int = 1) -> bool:
    if not keywords:
        return False
    hits = sum(1 for k in keywords if k and k in (text or ""))
    return hits >= min_hits


def _load_variants(variant_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    all_v = {v["agent_id"]: v for v in build_local_variants(include_deepseek=deepseek_available())}
    harness = {
        "agent_id": "minimal_http_rag_harness",
        "sample_type": "local_variant",
        "local_variant": True,
        "model_backend": "deepseek" if deepseek_available() else "mock",
        "default_retriever_profile": "tfidf_top5",
        "api_base_url": HARNESS_URL,
        "assigned_port": 18100,
        "poison_test_supported": True,
        "repo_url": "platform:minimal_http_rag_agent",
        "notes": "primary harness :18100",
    }
    all_v[harness["agent_id"]] = harness

    if variant_ids:
        return [all_v[i] for i in variant_ids if i in all_v]
    return [all_v[i] for i in DEFAULT_VARIANT_IDS if i in all_v]


def _run_query(
    adapter: HttpRAGAgentAdapter,
    *,
    question: str,
    profile: str,
) -> Dict[str, Any]:
    try:
        return adapter.query(question, retriever_profile=profile)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "answer": "", "poison_retrieved": False, "poison_rank": None}


def _evaluate_row(
    *,
    resolved: Dict[str, Any],
    variant: Dict[str, Any],
    phase: str,
    corpus_mode: str,
    query_type: str,
    query_text: str,
    result: Dict[str, Any],
    run_id: str,
) -> Dict[str, Any]:
    target = resolved["target"]
    answer = result.get("answer", "") or ""
    err = result.get("error", "")
    profile = variant.get("default_retriever_profile", "tfidf_top5")

    ev = evaluate_answer(
        target=target,
        answer=answer,
        poison_retrieved=bool(result.get("poison_retrieved")),
        poison_rank=result.get("poison_rank"),
    ) if answer and not err else None

    exp_clean = resolved.get("expected_clean_answer_keywords", [])
    poison_kw = resolved.get("poison_target_keywords", [])

    expected_clean_hit = _keywords_hit(answer, exp_clean, min_hits=1)
    poison_kw_hit = _keywords_hit(answer, poison_kw, min_hits=1)

    poison_retrieved = bool(result.get("poison_retrieved"))
    is_poisoned_trigger = (
        phase == "poisoned" and corpus_mode == "mixed" and query_type == "trigger_query"
    )
    is_clean_on_mixed = (
        phase == "clean" and corpus_mode == "mixed" and query_type == "clean_query"
    )

    strict_attack = bool(ev.attack_success) if ev else False

    poison_retrieval_hit = poison_retrieved if is_poisoned_trigger else False
    poison_answer_keyword_hit = poison_kw_hit if is_poisoned_trigger else False
    poison_strict_attack_success = strict_attack if is_poisoned_trigger else False
    # Legacy blended field (keyword OR strict); summarize uses split metrics as primary.
    poison_answer_success = poison_answer_keyword_hit or poison_strict_attack_success

    clean_query_poison_retrieval = poison_retrieved if is_clean_on_mixed else False
    clean_query_answer_keyword_contamination = poison_kw_hit if is_clean_on_mixed else False
    clean_query_strict_contamination = strict_attack if is_clean_on_mixed else False
    clean_contamination = clean_query_answer_keyword_contamination

    return {
        "run_id": run_id,
        "case_id": resolved["case_id"],
        "domain": resolved.get("domain", ""),
        "corpus_domain": resolved.get("domain", ""),
        "poison_trigger_style": resolved["poison_trigger_style"],
        "phase": phase,
        "corpus_mode": corpus_mode,
        "query_type": query_type,
        "query_text": query_text,
        "agent_id": variant["agent_id"],
        "sample_type": "local_variant",
        "model_backend": variant.get("model_backend", ""),
        "retrieval_profile": profile,
        "retrieval_top_k": _top_k_from_profile(profile),
        "generator_attack_id": resolved.get("generator_attack_id", ""),
        "poison_retrieved": poison_retrieved,
        "poison_rank": result.get("poison_rank"),
        "poison_retrieval_hit": poison_retrieval_hit,
        "poison_answer_keyword_hit": poison_answer_keyword_hit,
        "poison_strict_attack_success": poison_strict_attack_success,
        "poison_answer_success": poison_answer_success,
        "clean_query_poison_retrieval": clean_query_poison_retrieval,
        "clean_query_answer_keyword_contamination": clean_query_answer_keyword_contamination,
        "clean_query_strict_contamination": clean_query_strict_contamination,
        "clean_contamination": clean_contamination,
        "expected_clean_keywords_hit": expected_clean_hit,
        "poison_target_keywords_hit": poison_kw_hit,
        "attack_success": bool(ev.attack_success) if ev else False,
        "final_risk": ev.final_risk if ev else "",
        "answer_excerpt": (answer[:300] if answer else ""),
        "server_url": variant.get("_effective_url", variant.get("api_base_url", "")),
        "used_harness_fallback": bool(variant.get("_used_harness_fallback")),
        "error": err[:400] if err else "",
    }


def _execute_case_variant(
    resolved: Dict[str, Any],
    variant: Dict[str, Any],
    run_id: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    base_url = variant.get("api_base_url", HARNESS_URL)
    adapter = HttpRAGAgentAdapter(base_url)
    health = adapter.health()
    profile = variant.get("default_retriever_profile", "tfidf_top5")
    used_fallback = False

    if not health.get("ok"):
        harness = HttpRAGAgentAdapter(HARNESS_URL)
        if harness.health().get("ok"):
            adapter = harness
            base_url = HARNESS_URL
            used_fallback = True
            variant = {**variant, "_effective_url": base_url, "_used_harness_fallback": True}
        else:
            for phase, corpus_mode, qtype, queries in [
                ("clean", "clean", "clean_query", resolved.get("clean_queries", [])),
                ("clean", "mixed", "clean_query", resolved.get("clean_queries", [])),
                ("poisoned", "mixed", "trigger_query", resolved.get("trigger_queries", [])),
            ]:
                for q in queries:
                    rows.append(
                        {
                            "run_id": run_id,
                            "case_id": resolved["case_id"],
                            "domain": resolved.get("domain", ""),
                            "corpus_domain": resolved.get("domain", ""),
                            "poison_trigger_style": resolved["poison_trigger_style"],
                            "phase": phase,
                            "corpus_mode": corpus_mode,
                            "query_type": qtype,
                            "query_text": q,
                            "agent_id": variant["agent_id"],
                            "sample_type": "local_variant",
                            "model_backend": variant.get("model_backend", ""),
                            "retrieval_profile": profile,
                            "retrieval_top_k": _top_k_from_profile(profile),
                            "generator_attack_id": resolved.get("generator_attack_id", ""),
                            "server_url": base_url,
                            "error": f"server_down:{base_url}",
                        }
                    )
            return rows
    else:
        variant = {**variant, "_effective_url": base_url, "_used_harness_fallback": used_fallback}

    scenarios = [
        ("clean", "clean", "clean_query", resolved.get("clean_queries", []), False),
        ("clean", "mixed", "clean_query", resolved.get("clean_queries", []), True),
        ("poisoned", "mixed", "trigger_query", resolved.get("trigger_queries", []), True),
    ]

    for phase, corpus_mode, qtype, queries, with_poison in scenarios:
        try:
            adapter.build_corpus(
                resolved["clean_documents"],
                resolved["poison_documents"] if with_poison else [],
                corpus_mode="mixed" if with_poison else "clean",
            )
        except Exception as exc:
            for q in queries:
                rows.append(
                    {
                        "run_id": run_id,
                        "case_id": resolved["case_id"],
                        "poison_trigger_style": resolved["poison_trigger_style"],
                        "phase": phase,
                        "agent_id": variant["agent_id"],
                        "sample_type": "local_variant",
                        "query_text": q,
                        "error": f"corpus_build:{type(exc).__name__}",
                    }
                )
            continue

        for q in queries:
            result = _run_query(adapter, question=q, profile=profile)
            rows.append(
                _evaluate_row(
                    resolved=resolved,
                    variant=variant,
                    phase=phase,
                    corpus_mode=corpus_mode,
                    query_type=qtype,
                    query_text=q,
                    result=result,
                    run_id=run_id,
                )
            )

    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run formal poison experiment matrix")
    p.add_argument("--only-case", type=str, default=None)
    p.add_argument("--only-variant", type=str, default=None)
    p.add_argument("--max-cases", type=int, default=None)
    p.add_argument("--validate-only", action="store_true")
    return p.parse_args()


def main() -> None:
    bootstrap_api_env()
    args = parse_args()

    validation = validate_cases()
    print(f"[matrix] case validation: {validation}")
    if args.validate_only:
        return
    if not validation["styles_complete"]:
        raise SystemExit(f"Incomplete poison styles: {validation['missing_styles']}")

    cases = load_poison_cases()
    if args.only_case:
        cases = [c for c in cases if c["case_id"] == args.only_case]
    if args.max_cases is not None:
        cases = cases[: max(0, args.max_cases)]

    variant_ids = [args.only_variant] if args.only_variant else None
    variants = _load_variants(variant_ids)
    targets = load_targets()
    run_id = _make_run_id()
    all_rows: List[Dict[str, Any]] = []

    print(f"[matrix] cases={len(cases)} variants={len(variants)} run_id={run_id}")

    for case in cases:
        resolved = resolve_case(case, targets=targets)
        for variant in variants:
            try:
                rows = _execute_case_variant(resolved, variant, run_id)
                all_rows.extend(rows)
                ok = sum(1 for r in rows if not r.get("error"))
                print(f"[matrix] {case['case_id']} × {variant['agent_id']} rows={len(rows)} ok={ok}")
            except Exception as exc:
                all_rows.append(
                    {
                        "run_id": run_id,
                        "case_id": case["case_id"],
                        "poison_trigger_style": case.get("poison_trigger_style"),
                        "agent_id": variant["agent_id"],
                        "sample_type": "local_variant",
                        "error": f"outer:{type(exc).__name__}:{exc}",
                    }
                )

    write_csv(MATRIX_CSV, all_rows, fieldnames=MATRIX_FIELDS)
    print(f"[matrix] wrote {len(all_rows)} rows -> {MATRIX_CSV}")
    print("[matrix] smoke test (bulk_poison_smoke_test.py) is separate; this is the formal matrix.")


if __name__ == "__main__":
    main()
