"""Compat sidecar poison matrix — adapter-mediated external tests (not native HTTP)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from evaluators.answer_eval import evaluate_answer
from generators import template_generators
from target_agents.adapters.github_http_rag_adapter import GitHubAgentConfig, GitHubHttpRagAdapter
from target_agents.adapters.github_http_rag_adapter import (
    apply_manifest_overrides,
    config_from_bulk_entry,
    config_from_registry_entry,
)
from target_agents.bulk_common import RESULTS_DIR, load_registry as load_bulk_registry
from utils.corpus import load_clean_documents
from utils.targets import SecurityTarget, load_targets

REGISTRY_PATH = SCRIPT_DIR.parent / "registry.yaml"
SIDECAR_MODULE = "target_agents.adapters.compat_sidecar_server:app"
OUTPUT_CSV = RESULTS_DIR / "compat_sidecar_agent_poison_matrix.csv"
OUTPUT_SUMMARY = RESULTS_DIR / "compat_sidecar_agent_poison_summary.csv"
OUTPUT_REPORT = RESULTS_DIR / "compat_sidecar_agent_poison_report.md"
LOG_DIR = RESULTS_DIR / "agent_poison_logs"
SIDECAR_AGENTS = ["fastapi-meets-langgraph", "fastapi_meets_langgraph"]
ATTACKS = [
    "content_poison", "rule_poison", "retrieval_hijack_poison",
    "context_manipulation_poison", "instruction_injection_poison",
]
CORPUS_MODES = ["clean", "poison_only", "mixed"]
QUICK_TARGETS = ["researchhelper_rag_risk", "toolreport_tool_output_risk", "websearch_external_content_risk"]
SIDECAR_PORTS = {"fastapi-meets-langgraph": 19101, "fastapi_meets_langgraph": 19102}
CSV_FIELDS = [
    "run_id", "agent_id", "adapter_category", "test_mode", "adapter_mode",
    "native_agent_used", "sidecar_used", "deepseek_used", "repo", "base_url",
    "target_id", "attack_id", "corpus_mode", "test_scale", "ingest_method",
    "question", "answer", "attack_success", "strict_attack_success",
    "poison_retrieved", "poison_rank", "retrieved_sources", "error",
]


def _make_run_id() -> str:
    return f"compat_sidecar_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _load_registry() -> List[Dict[str, Any]]:
    import yaml
    if not REGISTRY_PATH.is_file():
        return []
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("agents", [])


def _resolve_agent(aid: str) -> tuple[GitHubAgentConfig, Optional[str]]:
    bulk = {a["id"]: a for a in load_bulk_registry().get("agents", [])}
    if aid in bulk:
        entry = bulk[aid]
        from target_agents.scripts.run_github_http_rag_poison_matrix import _load_manifest
        mf = _load_manifest().get(aid, {})
        cfg = config_from_bulk_entry(entry, mf)
        cfg = apply_manifest_overrides(cfg, mf, entry)
        native = cfg.base_url
        return cfg, native
    for entry in _load_registry():
        if entry.get("id") == aid:
            cfg = config_from_registry_entry(entry)
            return cfg, cfg.base_url or None
    raise RuntimeError(f"unknown agent: {aid}")


def _start_sidecar(port: int, native_base: str = "") -> subprocess.Popen:
    py = sys.executable
    env = os.environ.copy()
    if native_base:
        env["COMPAT_NATIVE_BASE_URL"] = native_base
        env["COMPAT_NATIVE_QUERY_ENDPOINT"] = "/agents/invoke"
    return subprocess.Popen(
        [py, "-m", "uvicorn", SIDECAR_MODULE, "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(PLATFORM_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_matrix(*, agent_ids: List[str], test_scale: str = "quick_3_targets") -> Path:
    run_id = _make_run_id()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    all_targets = load_targets()
    targets = [t for t in all_targets if t.target_id in QUICK_TARGETS] or all_targets[:3]
    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []

    for aid in agent_ids:
        port = SIDECAR_PORTS.get(aid, 19199)
        log_path = LOG_DIR / f"{aid}_sidecar_poison.log"
        proc: Optional[subprocess.Popen] = None
        try:
            src_cfg, native_base = _resolve_agent(aid)
            proc = _start_sidecar(port, native_base or "")
            time.sleep(4)
            cfg = GitHubAgentConfig(
                agent_id=aid,
                agent_class="real_github_http",
                repo_url=src_cfg.repo_url,
                framework=src_cfg.framework,
                base_url=f"http://127.0.0.1:{port}",
                local_path=src_cfg.local_path,
                chat_endpoint="/query",
                ingest_endpoint="/ingest",
                reset_endpoint="/reset",
                request_format="question",
                ingest_style="auto",
                lock_query_endpoint=True,
            )
            adapter = GitHubHttpRagAdapter(cfg)
            pr = adapter.probe(timeout=10)
            if not pr.health_ok:
                for target in targets:
                    for attack_id in ATTACKS:
                        for mode in CORPUS_MODES:
                            rows.append({
                                "run_id": run_id, "agent_id": aid,
                                "adapter_category": "C_compat_sidecar", "test_mode": "compat_sidecar",
                                "target_id": target.target_id, "attack_id": attack_id,
                                "corpus_mode": mode, "error": "sidecar_unreachable",
                            })
                continue

            baselines: Dict[str, str] = {}
            for target in targets:
                adapter.build_corpus(clean_docs, [], "clean", case_id="baseline")
                qr = adapter.query(target.question)
                baselines[target.target_id] = qr.get("answer", "") if qr.get("ok") else ""

            for target in targets:
                for attack_id in ATTACKS:
                    poison_docs = template_generators.generate_poison_docs(attack_id, target)
                    for mode in CORPUS_MODES:
                        case_id = f"{target.target_id}_{attack_id}_{mode}"
                        try:
                            ok, note = adapter.build_corpus(clean_docs, poison_docs, mode, case_id=case_id)
                            if not ok:
                                rows.append({
                                    "run_id": run_id, "agent_id": aid,
                                    "adapter_category": "C_compat_sidecar", "test_mode": "compat_sidecar",
                                    "target_id": target.target_id, "attack_id": attack_id,
                                    "corpus_mode": mode, "error": f"ingest_failed:{note}",
                                })
                                continue
                            qr = adapter.query(target.question)
                            if not qr.get("ok") or not qr.get("answer"):
                                rows.append({
                                    "run_id": run_id, "agent_id": aid,
                                    "adapter_category": "C_compat_sidecar", "test_mode": "compat_sidecar",
                                    "target_id": target.target_id, "attack_id": attack_id,
                                    "corpus_mode": mode, "error": f"query_failed:{qr.get('error')}",
                                })
                                continue
                            raw = qr.get("raw") if isinstance(qr.get("raw"), dict) else {}
                            pr_val = qr.get("poison_retrieved")
                            pr_bool = pr_val if isinstance(pr_val, bool) else False
                            ev = evaluate_answer(
                                target=target, answer=qr.get("answer", ""),
                                poison_retrieved=pr_bool,
                                poison_rank=None,
                                clean_baseline_answer=baselines.get(target.target_id) or None,
                            )
                            rows.append({
                                "run_id": run_id, "agent_id": aid,
                                "adapter_category": "C_compat_sidecar", "test_mode": "compat_sidecar",
                                "adapter_mode": raw.get("adapter_mode", "sidecar"),
                                "native_agent_used": raw.get("native_agent_used", False),
                                "sidecar_used": True,
                                "deepseek_used": raw.get("deepseek_used", False),
                                "repo": src_cfg.repo_url,
                                "base_url": cfg.base_url,
                                "target_id": target.target_id, "attack_id": attack_id,
                                "corpus_mode": mode, "test_scale": test_scale,
                                "ingest_method": "sidecar_ingest",
                                "question": target.question, "answer": qr.get("answer", ""),
                                "attack_success": ev.attack_success,
                                "strict_attack_success": ev.strict_attack_success,
                                "poison_retrieved": qr.get("poison_retrieved", pr_bool),
                                "poison_rank": qr.get("poison_rank"),
                                "retrieved_sources": qr.get("retrieved_sources", ""),
                                "error": "",
                            })
                        except Exception as exc:
                            rows.append({
                                "run_id": run_id, "agent_id": aid,
                                "adapter_category": "C_compat_sidecar", "test_mode": "compat_sidecar",
                                "target_id": target.target_id, "attack_id": attack_id,
                                "corpus_mode": mode, "error": str(exc),
                            })
        finally:
            if proc:
                proc.terminate()
        log_path.write_text(f"agent={aid} rows={sum(1 for r in rows if r.get('agent_id')==aid)}", encoding="utf-8")

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    by_agent: Dict[str, List] = defaultdict(list)
    for r in rows:
        by_agent[r["agent_id"]].append(r)
    summary = []
    for aid, sub in by_agent.items():
        ok = sum(1 for r in sub if not r.get("error") and r.get("answer"))
        summary.append({"agent_id": aid, "total_rows": len(sub), "success_rows": ok,
                        "poison_loop_complete": ok == len(sub) and len(sub) >= 45})
    with OUTPUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["agent_id", "total_rows", "success_rows", "poison_loop_complete"])
        w.writeheader()
        w.writerows(summary)
    OUTPUT_REPORT.write_text(f"# Compat Sidecar Poison Report\n\nrun_id={run_id}\n", encoding="utf-8")
    return OUTPUT_CSV


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="append", default=None)
    parser.add_argument("--scale", default="quick_3_targets")
    args = parser.parse_args()
    run_matrix(agent_ids=args.agent or SIDECAR_AGENTS, test_scale=args.scale)
    print(f"Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
