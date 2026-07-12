"""
Retriever / index ranking manipulation experiment (mixed corpus only).

Matrix: 10 targets x 5 attacks x 5 profiles = 250 rows.
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
from utils.summary_builder import build_ranking_manipulation_summary, write_summary
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

PROFILES = [
    "tfidf_top5",
    "trusted_source_boost_top5",
    "poison_boost_top5",
    "clean_demotion_top5",
    "poison_top1_forced",
]

BACKEND = "minimal_http_rag"
DEFAULT_BASE_URL = "http://127.0.0.1:18100"
CORPUS_MODE = "mixed"

GENERATOR_MAP: Dict[str, Callable[[SecurityTarget], List[Dict[str, Any]]]] = {
    attack_id: (lambda t, aid=attack_id: template_generators.generate_poison_docs(aid, t))
    for attack_id in ATTACKS
}


def _make_run_id() -> str:
    return (
        f"ranking_manip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )


def _ensure_server(adapter: HttpRAGAgentAdapter) -> None:
    if not adapter.health()["ok"]:
        raise RuntimeError("minimal_http_rag_agent not reachable")


def run_matrix(base_url: str = DEFAULT_BASE_URL) -> Path:
    require_llm_credentials()
    adapter = HttpRAGAgentAdapter(base_url=base_url)
    _ensure_server(adapter)

    run_id = _make_run_id()
    targets = load_targets()
    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []

    for target in targets:
        baseline_adapter = HttpRAGAgentAdapter(base_url=base_url)
        baseline_adapter.build_corpus(clean_docs, [], corpus_mode="clean")
        baseline = baseline_adapter.query(target.question, retriever_profile="tfidf_top5")
        clean_baseline_answer = baseline["answer"]

        for attack_id in ATTACKS:
            poison_docs = GENERATOR_MAP[attack_id](target)
            for profile in PROFILES:
                print(
                    f"[run] target={target.target_id} attack={attack_id} profile={profile}"
                )
                cell = HttpRAGAgentAdapter(base_url=base_url)
                cell.build_corpus(clean_docs, poison_docs, corpus_mode=CORPUS_MODE)
                result = cell.query(target.question, retriever_profile=profile)
                if not result["ok"]:
                    raise RuntimeError(result["error"])

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
                        "corpus_mode": CORPUS_MODE,
                        "retriever_profile": profile,
                        "question": target.question,
                        "answer": result["answer"],
                        **evaluation.to_dict(),
                        "poison_retrieved": result["poison_retrieved"],
                        "poison_rank": result["poison_rank"],
                        "poison_original_score": result.get("poison_original_score"),
                        "poison_manipulated_score": result.get("poison_manipulated_score"),
                        "retrieved_sources": result["retrieved_sources"],
                        "retrieved_scores": result["retrieved_scores"],
                        "manipulation_reason": result.get("manipulation_reason", ""),
                    }
                )

    out = RESULTS_DIR / "ranking_manipulation_test.csv"
    fieldnames = [
        "run_id", "target_id", "attack_id", "attack_family", "backend",
        "corpus_mode", "retriever_profile", "question", "answer",
        "final_risk", "attack_success", "risk_downgrade", "advice_suppressed",
        "answer_shift", "poison_retrieved", "poison_rank",
        "poison_original_score", "poison_manipulated_score",
        "retrieved_sources", "retrieved_scores", "manipulation_reason",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_summary(
        build_ranking_manipulation_summary(out),
        RESULTS_DIR / "ranking_manipulation_test.summary.json",
    )
    print(f"Wrote {len(rows)} rows -> {out}")
    return out


if __name__ == "__main__":
    run_matrix()
