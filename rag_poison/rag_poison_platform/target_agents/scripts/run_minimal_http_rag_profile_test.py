"""
Multi-retriever-profile poison test against minimal_http_rag_agent.

Matrix: 10 targets x 5 attacks x 2 corpus_mode x 3 retriever_profile = 300 rows.
"""

from __future__ import annotations

import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from evaluators.answer_eval import evaluate_answer
from generators import template_generators
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from utils.corpus import load_clean_documents
from utils.env_bootstrap import require_llm_credentials
from utils.paths import RESULTS_DIR
from utils.summary_builder import build_profile_summary, write_summary
from utils.targets import SecurityTarget, load_targets

ATTACKS = [
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
}

CORPUS_MODES = ["clean", "mixed"]
RETRIEVER_PROFILES = [
    "tfidf_top5",
    "tfidf_top10",
    "keyword_overlap_top5",
]

BACKEND = "minimal_http_rag"
DEFAULT_BASE_URL = "http://127.0.0.1:18100"

GENERATOR_MAP: Dict[str, Callable[[SecurityTarget], List[Dict[str, Any]]]] = {
    attack_id: (lambda t, aid=attack_id: template_generators.generate_poison_docs(aid, t))
    for attack_id in ATTACKS
}


def _make_run_id() -> str:
    return (
        f"minimal_http_rag_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        f"_{uuid.uuid4().hex[:8]}"
    )


def _ensure_server(adapter: HttpRAGAgentAdapter) -> None:
    health = adapter.health()
    if not health["ok"]:
        raise RuntimeError(
            "minimal_http_rag_agent not reachable. "
            f"Start server: minimal_http_rag_agent\\run_server.ps1 — {health['error']}"
        )


def run_matrix(
    base_url: str = DEFAULT_BASE_URL,
    output_path: Path | None = None,
) -> Path:
    require_llm_credentials()
    adapter = HttpRAGAgentAdapter(base_url=base_url)
    _ensure_server(adapter)

    run_id = _make_run_id()
    targets = load_targets()
    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []

    for retriever_profile in RETRIEVER_PROFILES:
        for target in targets:
            baseline_adapter = HttpRAGAgentAdapter(base_url=base_url)
            baseline_adapter.build_corpus(clean_docs, [], corpus_mode="clean")
            baseline = baseline_adapter.query(
                target.question,
                retriever_profile=retriever_profile,
            )
            if not baseline["ok"]:
                raise RuntimeError(f"baseline query failed: {baseline['error']}")
            clean_baseline_answer = baseline["answer"]

            for attack_id in ATTACKS:
                poison_docs = GENERATOR_MAP[attack_id](target)
                for corpus_mode in CORPUS_MODES:
                    print(
                        f"[run] profile={retriever_profile} "
                        f"target={target.target_id} attack={attack_id} mode={corpus_mode}"
                    )
                    cell_adapter = HttpRAGAgentAdapter(base_url=base_url)
                    cell_adapter.build_corpus(
                        clean_docs,
                        poison_docs if corpus_mode == "mixed" else [],
                        corpus_mode=corpus_mode,
                    )
                    result = cell_adapter.query(
                        target.question,
                        retriever_profile=retriever_profile,
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
                            "attack_id": attack_id,
                            "attack_family": ATTACK_FAMILY[attack_id],
                            "backend": BACKEND,
                            "corpus_mode": corpus_mode,
                            "retriever_profile": retriever_profile,
                            "poison_doc_count": (
                                len(poison_docs) if corpus_mode == "mixed" else 0
                            ),
                            "question": target.question,
                            "answer": result["answer"],
                            **evaluation.to_dict(),
                            "retrieved_sources": result["retrieved_sources"],
                            "retrieved_scores": result["retrieved_scores"],
                        }
                    )

    out = output_path or (RESULTS_DIR / "minimal_http_rag_profile_test.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "target_id",
        "attack_id",
        "attack_family",
        "backend",
        "corpus_mode",
        "retriever_profile",
        "poison_doc_count",
        "question",
        "answer",
        "final_risk",
        "attack_success",
        "risk_downgrade",
        "advice_suppressed",
        "answer_shift",
        "poison_retrieved",
        "poison_rank",
        "retrieved_sources",
        "retrieved_scores",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_path = RESULTS_DIR / "minimal_http_rag_profile_test.summary.json"
    write_summary(
        build_profile_summary(out),
        summary_path,
    )
    print(f"Wrote {len(rows)} rows -> {out}")
    print(f"Wrote summary -> {summary_path}")
    return out


if __name__ == "__main__":
    run_matrix()
