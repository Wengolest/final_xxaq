"""
External source / web supply-chain poisoning simulation.

Matrix: 10 targets x 1 attack x 3 modes = 30 rows.
"""

from __future__ import annotations

import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from evaluators.answer_eval import evaluate_answer
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from target_agents.scripts.external_source_loader import (
    load_clean_external_docs,
    load_poisoned_external_docs,
    select_poison_doc_for_target,
)
from utils.corpus import load_clean_documents
from utils.env_bootstrap import require_llm_credentials
from utils.paths import RESULTS_DIR
from utils.summary_builder import build_external_source_summary, write_summary
from utils.targets import load_targets

ATTACK_ID = "external_source_poison"
ATTACK_FAMILY = "external_source_poisoning"
BACKEND = "minimal_http_rag"
DEFAULT_BASE_URL = "http://127.0.0.1:18100"
RETRIEVER_PROFILE = "tfidf_top5"

MODES = ["clean_external_only", "poisoned_external_only", "mixed_external"]


def _make_run_id() -> str:
    return (
        f"external_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )


def _ensure_server(adapter: HttpRAGAgentAdapter) -> None:
    if not adapter.health()["ok"]:
        raise RuntimeError("minimal_http_rag_agent not reachable")


def _ingest_external(adapter: HttpRAGAgentAdapter, docs: List[Dict[str, Any]], source: str) -> None:
    for doc in docs:
        adapter.ingest(
            doc_id=doc["doc_id"],
            text=doc["content"],
            source=source,
            metadata=doc.get("metadata", {}),
        )


def _external_poison_stats(retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
    for item in retrieved:
        meta = item.get("metadata") or {}
        if item.get("source") == "poison" and meta.get("external_source"):
            return {
                "external_poison_retrieved": True,
                "external_poison_rank": item.get("rank"),
            }
    return {"external_poison_retrieved": False, "external_poison_rank": None}


def run_matrix(base_url: str = DEFAULT_BASE_URL) -> Path:
    require_llm_credentials()
    adapter = HttpRAGAgentAdapter(base_url=base_url)
    _ensure_server(adapter)

    run_id = _make_run_id()
    targets = load_targets()
    clean_corpus = load_clean_documents()
    clean_external = load_clean_external_docs()
    poisoned_external_all = load_poisoned_external_docs()
    rows: List[Dict[str, Any]] = []

    for target in targets:
        poison_doc = select_poison_doc_for_target(target.target_id, poisoned_external_all)

        baseline_adapter = HttpRAGAgentAdapter(base_url=base_url)
        baseline_adapter.build_corpus(clean_corpus, [], corpus_mode="clean")
        baseline = baseline_adapter.query(target.question, retriever_profile=RETRIEVER_PROFILE)
        clean_baseline_answer = baseline["answer"]

        for mode in MODES:
            print(f"[run] target={target.target_id} mode={mode}")
            cell = HttpRAGAgentAdapter(base_url=base_url)
            cell.reset()
            cell.ingest_documents(clean_corpus, source="clean")

            if mode == "clean_external_only":
                _ingest_external(cell, clean_external, source="clean")
            elif mode == "poisoned_external_only":
                cell.ingest(
                    poison_doc["doc_id"],
                    poison_doc["content"],
                    source="poison",
                    metadata=poison_doc.get("metadata", {}),
                )
            elif mode == "mixed_external":
                _ingest_external(cell, clean_external, source="clean")
                cell.ingest(
                    poison_doc["doc_id"],
                    poison_doc["content"],
                    source="poison",
                    metadata=poison_doc.get("metadata", {}),
                )

            result = cell.query(target.question, retriever_profile=RETRIEVER_PROFILE)
            if not result["ok"]:
                raise RuntimeError(result["error"])

            ext_stats = _external_poison_stats(result["retrieved_docs"])
            evaluation = evaluate_answer(
                target=target,
                answer=result["answer"],
                poison_retrieved=result["poison_retrieved"],
                poison_rank=result["poison_rank"],
                clean_baseline_answer=clean_baseline_answer,
            )

            rows.append(
                {
                    "run_id": run_id,
                    "target_id": target.target_id,
                    "attack_id": ATTACK_ID,
                    "attack_family": ATTACK_FAMILY,
                    "backend": BACKEND,
                    "corpus_mode": mode,
                    "external_source_mode": mode,
                    "retriever_profile": RETRIEVER_PROFILE,
                    "question": target.question,
                    "answer": result["answer"],
                    **evaluation.to_dict(),
                    "poison_retrieved": result["poison_retrieved"],
                    "poison_rank": result["poison_rank"],
                    **ext_stats,
                    "retrieved_sources": result["retrieved_sources"],
                    "retrieved_scores": result["retrieved_scores"],
                    "retrieved_metadata": result["retrieved_metadata"],
                }
            )

    out = RESULTS_DIR / "external_source_poison_test.csv"
    fieldnames = [
        "run_id", "target_id", "attack_id", "attack_family", "backend",
        "corpus_mode", "external_source_mode", "retriever_profile", "question",
        "answer", "final_risk", "attack_success", "risk_downgrade",
        "advice_suppressed", "answer_shift", "poison_retrieved", "poison_rank",
        "external_poison_retrieved", "external_poison_rank",
        "retrieved_sources", "retrieved_scores", "retrieved_metadata",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_summary(
        build_external_source_summary(out),
        RESULTS_DIR / "external_source_poison_test.summary.json",
    )
    print(f"Wrote {len(rows)} rows -> {out}")
    return out


if __name__ == "__main__":
    run_matrix()
