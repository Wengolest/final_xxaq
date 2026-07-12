"""Poison smoke test on poison_test_supported samples (local variants + harness)."""

from __future__ import annotations

import csv
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from evaluators.answer_eval import evaluate_answer
from generators.template_generators import generate_content_poison, generate_instruction_injection_poison
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from target_agents.bulk_common import RESULTS_DIR, load_registry, save_registry, write_csv, now_iso
from target_agents.local_variants.registry import build_local_variants
from utils.corpus import load_clean_documents
from utils.deepseek_env import deepseek_available
from utils.env_bootstrap import bootstrap_api_env
from utils.targets import load_targets

HARNESS_URL = "http://127.0.0.1:18100"
ATTACKS = ["content_poison", "instruction_injection_poison"]
TARGET_SAMPLE = ["researchhelper_rag_risk", "websearch_external_content_risk"]
POOL_CSV = RESULTS_DIR / "agent_sample_pool.csv"


def _make_run_id() -> str:
    return f"bulk_poison_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _load_pool_rows() -> List[Dict[str, Any]]:
    if POOL_CSV.is_file():
        with POOL_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    rows = []
    for v in build_local_variants(include_deepseek=deepseek_available()):
        rows.append(
            {
                "agent_id": v["agent_id"],
                "sample_type": "local_variant",
                "poison_test_supported": "True",
                "api_base_url": v["api_base_url"],
                "default_retriever_profile": v.get("default_retriever_profile", "tfidf_top5"),
                "model_backend": v["model_backend"],
            }
        )
    return [r for r in rows if str(r.get("poison_test_supported")).lower() == "true"]


def _run_harness_smoke(run_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    harness = HttpRAGAgentAdapter(HARNESS_URL)
    if not harness.health()["ok"]:
        return rows
    targets = [t for t in load_targets() if t.target_id in TARGET_SAMPLE]
    clean_docs = load_clean_documents()
    gens = {
        "content_poison": generate_content_poison,
        "instruction_injection_poison": generate_instruction_injection_poison,
    }
    for target in targets:
        for attack_id, gen in gens.items():
            poison = gen(target)[0]
            for phase, with_poison in [("clean", False), ("poison", True)]:
                adapter = HttpRAGAgentAdapter(HARNESS_URL)
                adapter.build_corpus(
                    clean_docs,
                    [poison] if with_poison else [],
                    corpus_mode="mixed" if with_poison else "clean",
                )
                result = adapter.query(target.question)
                ev = evaluate_answer(
                    target=target,
                    answer=result["answer"],
                    poison_retrieved=result["poison_retrieved"],
                    poison_rank=result["poison_rank"],
                )
                rows.append(
                    {
                        "run_id": run_id,
                        "agent_id": "minimal_http_rag_harness",
                        "sample_type": "local_variant",
                        "bulk_agent_ref": "harness_for_rag_capable_screening",
                        "target_id": target.target_id,
                        "attack_id": attack_id,
                        "phase": phase,
                        "attack_success": ev.attack_success,
                        "answer_shift": ev.answer_shift,
                        "poison_retrieved": result["poison_retrieved"],
                        "final_risk": ev.final_risk,
                        "not_poisonable": False,
                        "notes": "controlled harness E2E",
                    }
                )
    return rows


def _run_variant_smoke(sample: Dict[str, Any], run_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    base = sample.get("api_base_url", "")
    profile = sample.get("default_retriever_profile") or "tfidf_top5"
    aid = sample["agent_id"]
    adapter = HttpRAGAgentAdapter(base)
    if not adapter.health()["ok"]:
        rows.append(
            {
                "run_id": run_id,
                "agent_id": aid,
                "sample_type": sample.get("sample_type", "local_variant"),
                "not_poisonable": True,
                "notes": "variant server down",
            }
        )
        return rows

    targets = [t for t in load_targets() if t.target_id in TARGET_SAMPLE[:1]]
    clean_docs = load_clean_documents()
    poison = generate_content_poison(targets[0])[0]
    try:
        adapter.build_corpus(clean_docs, [poison], corpus_mode="mixed")
        result = adapter.query(
            targets[0].question,
            retriever_profile=profile,
        )
        ev = evaluate_answer(
            target=targets[0],
            answer=result["answer"],
            poison_retrieved=result.get("poison_retrieved", False),
            poison_rank=result.get("poison_rank"),
        )
        rows.append(
            {
                "run_id": run_id,
                "agent_id": aid,
                "sample_type": sample.get("sample_type", "local_variant"),
                "bulk_agent_ref": aid,
                "target_id": targets[0].target_id,
                "attack_id": "content_poison",
                "phase": "poison",
                "attack_success": ev.attack_success,
                "answer_shift": ev.answer_shift,
                "poison_retrieved": result.get("poison_retrieved", False),
                "final_risk": ev.final_risk,
                "not_poisonable": False,
                "notes": f"profile={profile} backend={sample.get('model_backend','')}",
            }
        )
    except Exception as exc:
        rows.append(
            {
                "run_id": run_id,
                "agent_id": aid,
                "sample_type": sample.get("sample_type", "local_variant"),
                "not_poisonable": True,
                "notes": f"smoke_error: {type(exc).__name__}",
            }
        )
    return rows


def main() -> None:
    bootstrap_api_env()
    reg = load_registry()
    rows: List[Dict[str, Any]] = []
    run_id = _make_run_id()

    rows.extend(_run_harness_smoke(run_id))

    pool = _load_pool_rows()
    local_samples = [
        s
        for s in pool
        if s.get("sample_type") == "local_variant"
        and str(s.get("poison_test_supported")).lower() == "true"
    ][:8]

    for sample in local_samples:
        rows.extend(_run_variant_smoke(sample, run_id))

    tested_ids = {r["agent_id"] for r in rows if not r.get("not_poisonable")}
    for a in reg.get("agents", []):
        if a.get("external_service_missing"):
            a["poison_test_supported"] = False
            continue
        if a["id"] in tested_ids:
            a["poison_tested"] = True
            a["status"] = "poison_tested"
        elif a.get("rag_capable") and a.get("http_api_success") and not a.get("external_service_missing"):
            rows.append(
                {
                    "run_id": run_id,
                    "agent_id": a["id"],
                    "sample_type": "external_github_agent",
                    "bulk_agent_ref": a["id"],
                    "not_poisonable": True,
                    "notes": "external agent lacks standard ingest; harness used for pool",
                }
            )

    if any(r.get("agent_id") == "minimal_http_rag_harness" for r in rows):
        entry = {
            "id": "minimal_http_rag_harness",
            "repo_url": "platform:minimal_http_rag_agent",
            "sample_type": "local_variant",
            "local_variant": True,
            "rag_capable": True,
            "poison_tested": True,
            "poison_test_supported": True,
            "http_api_success": True,
            "grade": "A",
            "status": "poison_tested",
            "tested_at": now_iso(),
        }
        if not any(x.get("id") == "minimal_http_rag_harness" for x in reg.get("agents", [])):
            reg["agents"].append(entry)
        else:
            for x in reg["agents"]:
                if x["id"] == "minimal_http_rag_harness":
                    x.update(entry)

    save_registry(reg)
    out = RESULTS_DIR / "bulk_agent_poison_smoke_test.csv"
    fieldnames = [
        "run_id",
        "agent_id",
        "sample_type",
        "bulk_agent_ref",
        "target_id",
        "attack_id",
        "phase",
        "attack_success",
        "answer_shift",
        "poison_retrieved",
        "final_risk",
        "not_poisonable",
        "notes",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Poison smoke rows: {len(rows)} -> {out}")


if __name__ == "__main__":
    main()
