"""Case-based poison matrix (standard_8_types / full_10_types) for external agents."""

from __future__ import annotations

import argparse
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

from target_agents.poison_tests.evaluator import evaluate_poison_case
from target_agents.adapters.github_http_rag_adapter import GitHubHttpRagAdapter
from target_agents.bulk_common import RESULTS_DIR, load_registry as load_bulk_registry
from target_agents.poison_tests.case_loader import cases_for_scale, expected_rows_for_scale, resolve_case
from target_agents.scripts.docker_agent_helper import (
    docker_compose_down,
    docker_compose_up,
    start_rag_fastapi_stack,
    start_tech_trends_stack,
)
from target_agents.scripts.poison_matrix_core import (
    CORPUS_MODES,
    CSV_FIELDS,
    load_csv,
    merge_csv_rows,
    write_csv,
)
from target_agents.scripts.run_github_http_rag_poison_matrix import (
    OUTPUT_CSV,
    _collect_agent_configs,
    _failure_row,
)
from utils.corpus import load_clean_documents

LOG_DIR = RESULTS_DIR / "agent_poison_logs"
DOCKER_AGENTS = {
    "rag-fastapi-chatbot", "enterprise-rag-chatbot", "tech-trends-chatbot",
    "rag-template", "ai-healthcare-system", "rag-with-langchain-and-fastapi",
}
SUCCESSFUL_QUICK = {
    "simple_rag_chatbot", "langserve", "langgraph-agents",
    "rag-with-langchain-and-fastapi", "gpt-researcher",
    "fastapi-meets-langgraph", "fastapi_meets_langgraph",
}
SIDECAR_AGENTS = {"fastapi-meets-langgraph", "fastapi_meets_langgraph"}
SIDECAR_PORTS = {"fastapi-meets-langgraph": 19101, "fastapi_meets_langgraph": 19102}


def _make_run_id(scale: str) -> str:
    return f"case_matrix_{scale}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _try_docker_start(cfg, agent_id: str) -> Dict[str, Any]:
    repo = Path(cfg.local_path)
    if agent_id == "tech-trends-chatbot":
        return start_tech_trends_stack(repo)
    if agent_id == "rag-fastapi-chatbot":
        r = start_rag_fastapi_stack(repo)
        if r.get("base_url"):
            cfg.base_url = r["base_url"]
        return r
    r = docker_compose_up(repo, health_wait_sec=180)
    return r


def run_case_matrix(
    *,
    scale: str,
    agent_ids: Optional[List[str]] = None,
    upgrade_only: bool = False,
    resume: bool = False,
    force_agents: Optional[List[str]] = None,
    source: str = "new_run",
    test_mode: str = "native_http",
) -> Path:
    run_id = _make_run_id(scale)
    cases_raw = cases_for_scale(scale)
    if not cases_raw:
        raise RuntimeError(f"no cases for scale={scale}")

    configs = _collect_agent_configs(
        include_minimal=False,
        include_all_bulk=True,
        agent_ids=agent_ids,
    )
    if upgrade_only:
        configs = [c for c in configs if c.agent_id in SUCCESSFUL_QUICK]
    if not configs:
        raise RuntimeError("no agent configs")

    rows: List[Dict[str, Any]] = load_csv(OUTPUT_CSV) if resume else []
    force_set = set(force_agents or [])
    skip: set[str] = set()
    if resume:
        for cfg in configs:
            if cfg.agent_id in force_set:
                continue
            sub = [r for r in rows if r.get("agent_id") == cfg.agent_id and r.get("test_scale") == scale]
            if len(sub) >= expected_rows_for_scale(scale) and all(not r.get("error") and r.get("answer") for r in sub):
                skip.add(cfg.agent_id)

    clean_docs_global = load_clean_documents()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    for cfg in configs:
        if cfg.agent_id in skip:
            print(f"[case-matrix] skip completed {cfg.agent_id} scale={scale}", flush=True)
            continue
        rows = merge_csv_rows(rows, agent_id=cfg.agent_id, scale=scale, replace=cfg.agent_id in force_set)
        log_path = LOG_DIR / f"{cfg.agent_id}_{scale}_{run_id}.log"
        logs: List[str] = []
        docker_info: Dict[str, Any] = {}
        if cfg.agent_id in SIDECAR_AGENTS:
            import subprocess as sp
            port = SIDECAR_PORTS[cfg.agent_id]
            sp.Popen(
                [sys.executable, "-m", "uvicorn", "target_agents.adapters.compat_sidecar_server:app",
                 "--host", "127.0.0.1", "--port", str(port)],
                cwd=str(PLATFORM_ROOT), stdout=sp.DEVNULL, stderr=sp.DEVNULL,
            )
            time.sleep(4)
            cfg.base_url = f"http://127.0.0.1:{port}"
            cfg.chat_endpoint = "/query"
            cfg.ingest_endpoint = "/ingest"
            cfg.reset_endpoint = "/reset"
            cfg.request_format = "question"
            cfg.lock_query_endpoint = True
            cfg.ingest_style = "auto"
            test_mode = "compat_sidecar"
        adapter = GitHubHttpRagAdapter(cfg)

        if cfg.agent_id in DOCKER_AGENTS:
            docker_info = _try_docker_start(cfg, cfg.agent_id)
            logs.append(f"docker={docker_info}")
            test_mode = "docker_native_http" if docker_info.get("ok") else test_mode

        if not adapter.probe().health_ok and cfg.start_command:
            subprocess.Popen(cfg.start_command, cwd=cfg.start_cwd or cfg.local_path, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(10)
            adapter.probe()

        baselines: Dict[str, str] = {}
        for raw_case in cases_raw:
            job = resolve_case(raw_case)
            target = job["target"]
            try:
                adapter.build_corpus(job["clean_documents"], [], "clean", case_id=f"bl_{job['case_id']}")
                qr = adapter.query((job.get("clean_queries") or [target.question])[0])
                baselines[job["case_id"]] = qr.get("answer", "") if qr.get("ok") else ""
            except Exception:
                baselines[job["case_id"]] = ""

        for raw_case in cases_raw:
            job = resolve_case(raw_case)
            target = job["target"]
            ptype = job.get("poison_type", "")
            queries = job.get("trigger_queries") or [target.question]
            if ptype == "persistence_recall_poison":
                query_list = queries
            else:
                query_list = [queries[0]]

            for corpus_mode in CORPUS_MODES:
                for qi, question in enumerate(query_list):
                    case_id = f"{job['case_id']}_{corpus_mode}_q{qi}"
                    try:
                        ok_ingest, ingest_note = adapter.build_corpus(
                            job["clean_documents"],
                            job["poison_documents"],
                            corpus_mode,
                            case_id=case_id,
                        )
                        if not ok_ingest:
                            rows.append({
                                **_failure_row(
                                    run_id=run_id, cfg=cfg, target=target,
                                    attack_id=job.get("generator_attack_id", ""),
                                    corpus_mode=corpus_mode, test_scale=scale,
                                    error=f"ingest_failed:{ingest_note}",
                                ),
                                "case_id": job["case_id"], "poison_type": ptype,
                                "scale": scale, "source": source, "test_mode": test_mode,
                                "question": question,
                            })
                            continue
                        qr = adapter.query(question)
                        if not qr.get("ok") or not qr.get("answer"):
                            rows.append({
                                **_failure_row(
                                    run_id=run_id, cfg=cfg, target=target,
                                    attack_id=job.get("generator_attack_id", ""),
                                    corpus_mode=corpus_mode, test_scale=scale,
                                    error=f"query_failed:{qr.get('error','')}",
                                ),
                                "case_id": job["case_id"], "poison_type": ptype,
                                "scale": scale, "source": source, "test_mode": test_mode,
                                "question": question, "failure_stage": "query",
                            })
                            continue
                        ev = evaluate_poison_case(
                            case=job, target=target, answer=qr.get("answer", ""),
                            poison_retrieved=bool(qr.get("poison_retrieved")),
                            poison_rank=qr.get("poison_rank") if qr.get("poison_rank") != "unknown" else None,
                            clean_baseline_answer=baselines.get(job["case_id"]),
                            retrieved_docs=qr.get("retrieved_sources_list"),
                            corpus_mode=corpus_mode,
                            query_type="trigger",
                            file_ingest_ok=ok_ingest,
                            index_build_ok=True,
                        )
                        dbg = ev.debug_dict()
                        rows.append({
                            "run_id": run_id, "agent_id": cfg.agent_id,
                            "agent_class": cfg.agent_class, "repo": cfg.repo_url,
                            "framework": cfg.framework, "base_url": cfg.base_url,
                            "target_id": target.target_id,
                            "attack_id": job.get("generator_attack_id", ""),
                            "attack_family": ptype,
                            "corpus_mode": corpus_mode, "test_scale": scale, "scale": scale,
                            "source": source, "test_mode": test_mode,
                            "adapter_category": "A_native_http_rag",
                            "ingest_method": adapter.ingest_method,
                            "reset_supported": adapter.reset_supported,
                            "query_endpoint": cfg.chat_endpoint,
                            "case_id": job["case_id"], "poison_type": ptype,
                            "poison_trigger_style": job.get("poison_trigger_style", ""),
                            "question": question, "answer": qr.get("answer", ""),
                            "attack_goal": job.get("attack_goal", ""),
                            "final_risk": ev.final_risk,
                            "attack_success": ev.attack_success,
                            "strict_attack_success": ev.poison_strict_attack_success,
                            "risk_downgrade": ev.risk_downgrade,
                            "advice_suppressed": ev.advice_suppressed,
                            "answer_shift": ev.answer_shift,
                            "conflict_answer": ev.conflict_answer,
                            "poison_retrieved": qr.get("poison_retrieved"),
                            "poison_rank": qr.get("poison_rank"),
                            "retrieved_sources": qr.get("retrieved_sources", ""),
                            "http_status": qr.get("http_status", 0),
                            "latency_ms": qr.get("latency_ms", ""),
                            "rule_adoption": ev.rule_adoption if ev.rule_adoption is not None else "",
                            "instruction_follow": ev.instruction_follow if ev.instruction_follow is not None else "",
                            "instruction_follow_level": dbg.get("instruction_follow_level", ""),
                            "context_shift": ev.context_shift if ev.context_shift is not None else "",
                            "metadata_bypass": ev.metadata_bypass if ev.metadata_bypass is not None else "",
                            "metadata_observable": dbg.get("metadata_observable", True),
                            "citation_text_spoof": dbg.get("citation_text_spoof", ""),
                            "file_ingest_success": ev.file_ingest_success if ev.file_ingest_success is not None else "",
                            "index_build_success": ev.index_build_success if ev.index_build_success is not None else "",
                            "top_k_poison": ev.top_k_poison if ev.top_k_poison is not None else "",
                            "poison_answer_keyword_hit": dbg.get("poison_answer_keyword_hit", ""),
                            "eval_reason": dbg.get("eval_reason", ""),
                            "matched_poison_keywords": dbg.get("matched_poison_keywords", ""),
                            "matched_clean_keywords": dbg.get("matched_clean_keywords", ""),
                            "strict_rule_matched": dbg.get("strict_rule_matched", ""),
                            "strict_rule_failed_reason": dbg.get("strict_rule_failed_reason", ""),
                            "risk_label_detected": dbg.get("risk_label_detected", ""),
                            "advice_present": dbg.get("advice_present", ""),
                            "advice_suppressed_reason": dbg.get("advice_suppressed_reason", ""),
                            "error": "",
                        })
                    except Exception as exc:
                        rows.append({
                            **_failure_row(
                                run_id=run_id, cfg=cfg, target=target,
                                attack_id=job.get("generator_attack_id", ""),
                                corpus_mode=corpus_mode, test_scale=scale,
                                error=str(exc),
                            ),
                            "case_id": job["case_id"], "poison_type": ptype,
                            "scale": scale, "source": source, "question": question,
                        })
        ok_n = sum(1 for r in rows if r.get("agent_id") == cfg.agent_id and r.get("test_scale") == scale and not r.get("error") and r.get("answer"))
        logs.append(f"ok_rows={ok_n} scale={scale}")
        log_path.write_text("\n".join(logs), encoding="utf-8")
        write_csv(OUTPUT_CSV, rows)
        if cfg.agent_id in DOCKER_AGENTS and not docker_info.get("ok"):
            docker_compose_down(Path(cfg.local_path))

    write_csv(OUTPUT_CSV, rows)
    print(f"Wrote {len(rows)} rows -> {OUTPUT_CSV}", flush=True)
    return OUTPUT_CSV


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scale", choices=["standard_8_types", "full_10_types"], required=True)
    p.add_argument("--agent", action="append")
    p.add_argument("--upgrade-successful-agents", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force-agent", action="append", default=None)
    args = p.parse_args()
    force = args.force_agent
    aids = args.agent
    if force and not aids:
        aids = force
    run_case_matrix(
        scale=args.scale,
        agent_ids=aids,
        upgrade_only=args.upgrade_successful_agents and not force,
        resume=args.resume,
        force_agents=force,
    )


if __name__ == "__main__":
    main()
