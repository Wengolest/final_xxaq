"""
Self-proof demo: minimal HTTP RAG poison + agent chain (CoT) on same platform.

Usage (from rag_poison_platform):
  python target_agents/scripts/run_self_proof_demo.py
  python target_agents/scripts/run_self_proof_demo.py --rag-only
  python target_agents/scripts/run_self_proof_demo.py --chain-only --chain-limit 3
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from evaluators.answer_eval import evaluate_answer
from generators.template_generators import generate_content_poison
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from utils.corpus import load_clean_documents
from utils.env_bootstrap import require_llm_credentials
from utils.paths import RESULTS_DIR
from utils.targets import load_targets

DEFAULT_BASE_URL = "http://127.0.0.1:18100"
PROOF_TARGET_ID = "researchhelper_rag_risk"
PROOF_ATTACK = "content_poison"


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run_id(prefix: str) -> str:
    return f"{prefix}_{_stamp()}_{uuid.uuid4().hex[:8]}"


def run_rag_proof(base_url: str) -> Dict[str, Any]:
    require_llm_credentials()
    adapter = HttpRAGAgentAdapter(base_url=base_url)
    health = adapter.health()
    if not health["ok"]:
        raise RuntimeError(
            f"minimal_http_rag_agent not reachable at {base_url}. "
            "Start: minimal_http_rag_agent\\run_server.ps1"
        )

    targets = load_targets()
    target = next(t for t in targets if t.target_id == PROOF_TARGET_ID)
    clean_docs = load_clean_documents()
    poison_docs = generate_content_poison(target)
    run_id = _run_id("self_proof_rag")

    baseline_adapter = HttpRAGAgentAdapter(base_url=base_url)
    baseline_adapter.build_corpus(clean_docs, [], corpus_mode="clean")
    baseline = baseline_adapter.query(target.question)
    if not baseline["ok"]:
        raise RuntimeError(f"baseline query failed: {baseline['error']}")

    rows: List[Dict[str, Any]] = []
    for corpus_mode, with_poison in [("clean", False), ("mixed", True)]:
        cell = HttpRAGAgentAdapter(base_url=base_url)
        cell.build_corpus(
            clean_docs,
            poison_docs if with_poison else [],
            corpus_mode=corpus_mode,
        )
        result = cell.query(target.question, top_k=5)
        if not result["ok"]:
            raise RuntimeError(f"query failed ({corpus_mode}): {result['error']}")
        ev = evaluate_answer(
            target=target,
            answer=result["answer"],
            poison_retrieved=result["poison_retrieved"],
            poison_rank=result["poison_rank"],
            clean_baseline_answer=baseline["answer"],
        )
        rows.append(
            {
                "run_id": run_id,
                "experiment": "minimal_http_rag_poison",
                "agent_id": "minimal_http_rag_agent",
                "base_url": base_url,
                "target_id": target.target_id,
                "attack_id": PROOF_ATTACK,
                "corpus_mode": corpus_mode,
                "question": target.question,
                "answer_preview": (result["answer"] or "")[:200],
                "poison_retrieved": result["poison_retrieved"],
                "poison_rank": result["poison_rank"],
                "final_risk": ev.final_risk,
                "attack_success": ev.attack_success,
                "strict_attack_success": getattr(ev, "strict_attack_success", ev.attack_success),
            }
        )

    csv_path = RESULTS_DIR / "self_proof_rag_demo.csv"
    json_path = RESULTS_DIR / "self_proof_rag_demo.summary.json"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "run_id": run_id,
        "experiment": "minimal_http_rag_poison",
        "agent": "minimal_http_rag_agent",
        "base_url": base_url,
        "target_id": PROOF_TARGET_ID,
        "attack_id": PROOF_ATTACK,
        "rows": len(rows),
        "csv": str(csv_path),
        "health": health,
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[rag] Wrote {len(rows)} rows -> {csv_path}")
    print(f"[rag] Summary -> {json_path}")
    return summary


def run_chain_proof(limit: int, fast: bool) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "runners.run_agent_chain_poison",
        "--limit",
        str(limit),
        "--output-dir",
        "outputs/self_proof_chain",
    ]
    if fast:
        cmd.append("--fast")
    print("[chain] Running:", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(PLATFORM_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "agent chain proof failed\n"
            f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
        )
    print(proc.stdout[-2000:])
    out_dir = PLATFORM_ROOT / "outputs" / "self_proof_chain"
    csvs = sorted(out_dir.glob("agent_chain_poison_*.csv"), key=lambda p: p.stat().st_mtime)
    latest = csvs[-1] if csvs else None
    summary = {
        "experiment": "agent_chain_poison",
        "limit": limit,
        "fast": fast,
        "output_dir": str(out_dir),
        "latest_csv": str(latest) if latest else None,
    }
    manifest = RESULTS_DIR / "self_proof_chain_demo.summary.json"
    manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[chain] Manifest -> {manifest}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-proof RAG + chain demo")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--rag-only", action="store_true")
    parser.add_argument("--chain-only", action="store_true")
    parser.add_argument("--chain-limit", type=int, default=3)
    parser.add_argument("--no-fast", action="store_true", help="Use 6-call chain mode")
    args = parser.parse_args()

    do_rag = not args.chain_only
    do_chain = not args.rag_only
    manifest: Dict[str, Any] = {"generated_at": datetime.now().isoformat(), "steps": {}}

    if do_rag:
        manifest["steps"]["rag"] = run_rag_proof(args.base_url)
    if do_chain:
        manifest["steps"]["chain"] = run_chain_proof(args.chain_limit, fast=not args.no_fast)

    out = RESULTS_DIR / "self_proof_demo.manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[done] Self-proof manifest -> {out}")


if __name__ == "__main__":
    main()
