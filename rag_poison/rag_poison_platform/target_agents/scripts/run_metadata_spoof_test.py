"""
Metadata / trusted-source spoofing experiment on minimal_http_rag_agent.

Matrix: 10 targets x 1 attack x 4 modes = 40 rows.
"""

from __future__ import annotations

import csv
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from evaluators.answer_eval import evaluate_answer
from generators.template_generators import generate_metadata_spoof_poison
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from utils.corpus import load_clean_documents
from utils.env_bootstrap import require_llm_credentials
from utils.paths import RESULTS_DIR
from utils.summary_builder import build_metadata_spoof_summary, write_summary
from utils.targets import load_targets

ATTACK_ID = "metadata_spoof_poison"
ATTACK_FAMILY = "metadata_poisoning"
BACKEND = "minimal_http_rag"
DEFAULT_BASE_URL = "http://127.0.0.1:18100"
RETRIEVER_PROFILE = "tfidf_top5"

MODES = [
    ("clean_unfiltered", False, None),
    ("clean_official_filter", False, {"trust_level": "official"}),
    ("mixed_unfiltered", True, None),
    ("mixed_official_filter", True, {"trust_level": "official"}),
]


def _make_run_id() -> str:
    return (
        f"metadata_spoof_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )


def _ensure_server(adapter: HttpRAGAgentAdapter) -> None:
    health = adapter.health()
    if not health["ok"]:
        raise RuntimeError(
            "minimal_http_rag_agent not reachable. "
            f"Start: minimal_http_rag_agent\\run_server.ps1 — {health['error']}"
        )


def _metadata_filter_str(filt: Dict[str, Any] | None) -> str:
    return json.dumps(filt, ensure_ascii=False) if filt else ""


def run_matrix(base_url: str = DEFAULT_BASE_URL) -> Path:
    require_llm_credentials()
    adapter = HttpRAGAgentAdapter(base_url=base_url)
    _ensure_server(adapter)

    run_id = _make_run_id()
    targets = load_targets()
    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []

    for target in targets:
        poison_docs = generate_metadata_spoof_poison(target)
        poison_doc = poison_docs[0]

        baseline_adapter = HttpRAGAgentAdapter(base_url=base_url)
        baseline_adapter.build_corpus(clean_docs, [], corpus_mode="clean")
        baseline = baseline_adapter.query(target.question, retriever_profile=RETRIEVER_PROFILE)
        if not baseline["ok"]:
            raise RuntimeError(f"baseline failed: {baseline['error']}")
        clean_baseline_answer = baseline["answer"]

        for mode_name, include_poison, metadata_filter in MODES:
            print(f"[run] target={target.target_id} mode={mode_name}")
            cell = HttpRAGAgentAdapter(base_url=base_url)
            cell.reset()
            cell.ingest_documents(clean_docs, source="clean")
            if include_poison:
                cell.ingest(
                    doc_id=poison_doc["doc_id"],
                    text=poison_doc["content"],
                    source="poison",
                    metadata=poison_doc.get("metadata", {}),
                )

            result = cell.query(
                target.question,
                retriever_profile=RETRIEVER_PROFILE,
                metadata_filter=metadata_filter,
                allow_fallback=False,
            )
            if not result["ok"]:
                raise RuntimeError(f"query failed: {result['error']}")

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
                    "corpus_mode": mode_name,
                    "retriever_profile": RETRIEVER_PROFILE,
                    "metadata_filter": _metadata_filter_str(metadata_filter),
                    "poison_doc_count": 1 if include_poison else 0,
                    "question": target.question,
                    "answer": result["answer"],
                    **evaluation.to_dict(),
                    "poison_retrieved": result["poison_retrieved"],
                    "poison_rank": result["poison_rank"],
                    "retrieved_sources": result["retrieved_sources"],
                    "retrieved_scores": result["retrieved_scores"],
                    "retrieved_metadata": result["retrieved_metadata"],
                    "fallback_used": result.get("fallback_used", False),
                }
            )

    out = RESULTS_DIR / "metadata_spoof_test.csv"
    fieldnames = [
        "run_id", "target_id", "attack_id", "attack_family", "backend",
        "corpus_mode", "retriever_profile", "metadata_filter", "poison_doc_count",
        "question", "answer", "final_risk", "attack_success", "risk_downgrade",
        "advice_suppressed", "answer_shift", "poison_retrieved", "poison_rank",
        "retrieved_sources", "retrieved_scores", "retrieved_metadata", "fallback_used",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_summary(build_metadata_spoof_summary(out), RESULTS_DIR / "metadata_spoof_test.summary.json")
    print(f"Wrote {len(rows)} rows -> {out}")
    return out


if __name__ == "__main__":
    run_matrix()
