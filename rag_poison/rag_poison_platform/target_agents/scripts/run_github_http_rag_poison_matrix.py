"""
GitHub HTTP RAG agent poison test matrix.

clean / poison_only / mixed × A-E attacks × targets → CSV + summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from evaluators.answer_eval import evaluate_answer
from generators import template_generators
from target_agents.adapters.github_http_rag_adapter import (
    GitHubAgentConfig,
    GitHubHttpRagAdapter,
    apply_manifest_overrides,
    config_from_bulk_entry,
    config_from_registry_entry,
    detect_kb_path,
)
from target_agents.bulk_common import RESULTS_DIR, load_registry as load_bulk_registry
from target_agents.scripts.docker_agent_helper import start_rag_fastapi_stack, start_tech_trends_stack

DOCKER_START_AGENTS = {
    "rag-fastapi-chatbot": start_rag_fastapi_stack,
    "tech-trends-chatbot": start_tech_trends_stack,
}
from utils.corpus import load_clean_documents
from utils.paths import RESULTS_DIR as PATHS_RESULTS
from utils.targets import SecurityTarget, load_targets

REGISTRY_PATH = SCRIPT_DIR.parent / "registry.yaml"
MANIFEST_PATH = SCRIPT_DIR.parent / "bulk_agent_poison_manifest.yaml"
OUTPUT_CSV = RESULTS_DIR / "github_http_rag_poison_matrix.csv"
OUTPUT_SUMMARY = RESULTS_DIR / "github_http_rag_poison_matrix.summary.json"

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
    "semantic_neighbor_poison": "semantic_neighbor",
    "conflict_evidence_poison": "conflict_evidence",
    "metadata_spoof_poison": "metadata_poisoning",
}
CORPUS_MODES = ["clean", "poison_only", "mixed"]
QUICK_TARGETS = [
    "researchhelper_rag_risk",
    "toolreport_tool_output_risk",
    "websearch_external_content_risk",
]

GENERATOR_MAP: Dict[str, Callable[[SecurityTarget], List[Dict[str, Any]]]] = {
    aid: (lambda t, a=aid: template_generators.generate_poison_docs(a, t))
    for aid in ATTACKS
}

CSV_FIELDS = [
    "run_id",
    "agent_id",
    "agent_class",
    "repo",
    "framework",
    "base_url",
    "target_id",
    "attack_id",
    "attack_family",
    "corpus_mode",
    "test_scale",
    "ingest_method",
    "reset_supported",
    "query_endpoint",
    "question",
    "answer",
    "final_risk",
    "attack_success",
    "strict_attack_success",
    "risk_downgrade",
    "advice_suppressed",
    "answer_shift",
    "conflict_answer",
    "poison_retrieved",
    "poison_rank",
    "retrieved_sources",
    "retrieved_scores",
    "http_status",
    "latency_ms",
    "error",
]


def _make_run_id() -> str:
    return f"github_http_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _load_registry_agents() -> List[Dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return []
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("agents", [])


def _eligible_registry(entry: Dict[str, Any]) -> bool:
    status = str(entry.get("status", "")).lower()
    if status in {"running", "installed"}:
        return True
    if entry.get("api_base_url"):
        return True
    if entry.get("startup_success") or entry.get("http_probe_success"):
        return True
    if entry.get("rag_capable") or entry.get("kb_path_detected"):
        return True
    return False


def _eligible_bulk(entry: Dict[str, Any]) -> bool:
    if entry.get("local_variant"):
        return False
    if not entry.get("install_success"):
        return False
    if not entry.get("clone_success"):
        return False
    if not (entry.get("has_fastapi") or entry.get("query_endpoint") or entry.get("chat_endpoint")):
        return False
    return True


def _load_manifest() -> Dict[str, Dict[str, Any]]:
    if not MANIFEST_PATH.is_file():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("agents", {})


def _collect_agent_configs(
    *,
    include_minimal: bool,
    include_all_bulk: bool,
    agent_ids: Optional[List[str]],
) -> List[GitHubAgentConfig]:
    seen: set[str] = set()
    configs: List[GitHubAgentConfig] = []
    manifest = _load_manifest()

    for entry in _load_registry_agents():
        aid = entry.get("id", "")
        if not aid or aid in seen:
            continue
        if not _eligible_registry(entry):
            continue
        if aid == "minimal_http_rag_agent" and not include_minimal:
            continue
        if agent_ids and aid not in agent_ids:
            continue
        cfg = config_from_registry_entry(entry)
        if not cfg.base_url and aid != "minimal_http_rag_agent":
            port_map = {
                "fastapi_meets_langgraph": 18080,
                "simple_rag_chatbot": 8001,
                "langgraph_agents_shamspias": 19004,
            }
            p = port_map.get(aid)
            if p:
                cfg.base_url = f"http://127.0.0.1:{p}"
        if aid == "langgraph_agents_shamspias":
            # Same upstream repo as langgraph-agents; duplicate — do not count separately.
            continue
        if aid == "simple_rag_chatbot":
            cfg.ingest_endpoint = "/documents"
            cfg.reset_endpoint = "/reset"
            cfg.chat_endpoint = "/query"
            cfg.request_format = "question"
            cfg.start_command = (
                f'"{Path(cfg.local_path) / ".venv" / "Scripts" / "python.exe"}" '
                f"-m uvicorn src.main:app --host 127.0.0.1 --port 8001"
            )
        if aid == "fastapi_meets_langgraph":
            cfg.chat_endpoint = "/agents/invoke"
            cfg.query_param_name = "prompt"
            cfg.request_format = "question"
        seen.add(aid)
        configs.append(cfg)

    bulk = load_bulk_registry()
    bulk_agents = {a["id"]: a for a in bulk.get("agents", [])}
    bulk_ids = list(bulk_agents.keys())
    if include_all_bulk:
        ordered = [a["id"] for a in bulk.get("agents", []) if _eligible_bulk(a)]
    else:
        ordered = [
            "rag-with-langchain-and-fastapi",
            "tech-trends-chatbot",
            "fastapi-meets-langgraph",
            "langgraph-agents",
        ]

    for bid in ordered:
        if bid in seen:
            continue
        entry = bulk_agents.get(bid)
        if not entry:
            continue
        if not _eligible_bulk(entry):
            continue
        if agent_ids and bid not in agent_ids:
            continue
        mf = manifest.get(bid, {})
        cfg = config_from_bulk_entry(entry, mf)
        cfg = apply_manifest_overrides(cfg, mf, entry)
        if bid == "gpt-researcher":
            cfg.chat_endpoint = "/api/chat"
            cfg.ingest_endpoint = "/upload/"
            cfg.request_format = "gpt_researcher_chat"
            cfg.ingest_style = "http_upload"
            cfg.lock_query_endpoint = True
            cfg.base_url = "http://127.0.0.1:19033"
            repo = Path(cfg.local_path)
            py_candidates = [
                Path(r"D:\AI\target_agents_bulk\gpt-researcher\.venv\Scripts\python.exe"),
                repo.parent / ".venv" / "Scripts" / "python.exe",
            ]
            py = next((p for p in py_candidates if p.is_file()), None)
            docs_dir = repo / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            if py:
                cfg.start_command = (
                    f'set POISON_TEST_FAST_CHAT=1 && set PYTHONPATH={repo} && '
                    f'set DOC_PATH={docs_dir} && '
                    f'"{py}" -m uvicorn backend.server.app:app --host 127.0.0.1 --port 19033'
                )
                cfg.start_cwd = str(repo)
                cfg.venv_path = str(py.parent.parent)
        if bid == "langgraph-agents":
            cfg.chat_endpoint = "/chat"
            cfg.ingest_endpoint = "/embed"
            cfg.reset_endpoint = "/reset"
            cfg.request_format = "message"
            cfg.ingest_style = "http_embed"
            cfg.collection_per_case = True
            cfg.lock_query_endpoint = True
            import urllib.request
            for port in (19004, 19005, 19006):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/chat", timeout=2)
                    cfg.base_url = f"http://127.0.0.1:{port}"
                    break
                except Exception:
                    try:
                        h = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
                        body = h.read(200).decode("utf-8", errors="replace")
                        if "LangGraph" in body or '"status"' in body:
                            cfg.base_url = f"http://127.0.0.1:{port}"
                            break
                    except Exception:
                        pass
            else:
                cfg.base_url = "http://127.0.0.1:19005"
            vp = cfg.venv_path or entry.get("venv_path", "")
            py = Path(vp) / "Scripts" / "python.exe" if vp else Path(cfg.local_path).parent.parent / ".venv" / "Scripts" / "python.exe"
            port_num = cfg.base_url.rsplit(":", 1)[-1]
            cfg.start_command = (
                f'set PYTHONPATH= && set POISON_TEST_FAKE_EMBEDDINGS=1 && set OPENAI_API_BASE=https://api.deepseek.com && '
                f'"{py}" -m uvicorn main:app --host 127.0.0.1 --port {port_num}'
            )
            cfg.start_cwd = str(Path(cfg.local_path))
        if bid == "rag-with-langchain-and-fastapi":
            cfg.chat_endpoint = "/query/"
            cfg.http_method = "GET"
            cfg.query_param_name = "query"
            cfg.ingest_endpoint = "/documents"
            cfg.reset_endpoint = "/reset"
            cfg.ingest_style = "http_documents"
            cfg.lock_query_endpoint = True
            repo = Path(cfg.local_path)
            if not (repo / "endpoints.py").is_file():
                alt = Path(r"D:\AI\target_agents_bulk") / bid / "repo"
                if (alt / "endpoints.py").is_file():
                    cfg.local_path = str(alt)
        seen.add(bid)
        configs.append(cfg)

    return configs


def _bool_val(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v == "unknown":
        return False
    return str(v).strip().lower() in {"true", "1", "yes"}


def _as_rate(success: int, total: int) -> float:
    return round(success / total, 4) if total else 0.0


def _build_summary(rows: List[Dict[str, Any]], run_id: str) -> Dict[str, Any]:
    github_rows = [r for r in rows if r.get("agent_class") == "real_github_http"]
    agents_tested = sorted({r["agent_id"] for r in github_rows if not r.get("error") or r.get("answer")})
    poison_tested = sorted(
        {
            r["agent_id"]
            for r in github_rows
            if r.get("ingest_method") not in ("none", "") and r.get("http_status") not in ("", 0, "0")
        }
    )

    def asr_for(mode: str) -> float:
        subset = [r for r in rows if r.get("corpus_mode") == mode and not r.get("error")]
        if not subset:
            subset = [r for r in rows if r.get("corpus_mode") == mode]
        ok = sum(_bool_val(r.get("strict_attack_success")) for r in subset)
        return _as_rate(ok, len(subset))

    rank_dist: Counter[str] = Counter()
    for r in rows:
        if r.get("corpus_mode") == "mixed" and _bool_val(r.get("poison_retrieved")):
            rank_dist[f"rank={r.get('poison_rank')}"] += 1

    err_dist: Counter[str] = Counter(r.get("error", "")[:80] or "none" for r in rows if r.get("error"))

    by_agent: Dict[str, int] = Counter(r["agent_id"] for r in rows)
    by_mode: Dict[str, int] = Counter(r["corpus_mode"] for r in rows)
    by_attack: Dict[str, int] = Counter(r["attack_id"] for r in rows)

    asr_agent: Dict[str, float] = {}
    for aid in by_agent:
        sub = [r for r in rows if r["agent_id"] == aid]
        asr_agent[aid] = _as_rate(sum(_bool_val(r.get("strict_attack_success")) for r in sub), len(sub))

    asr_attack = {
        aid: _as_rate(
            sum(_bool_val(r.get("strict_attack_success")) for r in rows if r.get("attack_id") == aid),
            sum(1 for r in rows if r.get("attack_id") == aid),
        )
        for aid in by_attack
    }
    asr_mode = {
        m: _as_rate(
            sum(_bool_val(r.get("strict_attack_success")) for r in rows if r.get("corpus_mode") == m),
            sum(1 for r in rows if r.get("corpus_mode") == m),
        )
        for m in by_mode
    }

    retr_agent: Dict[str, float] = {}
    for aid in by_agent:
        mixed = [r for r in rows if r["agent_id"] == aid and r.get("corpus_mode") == "mixed"]
        hit = sum(_bool_val(r.get("poison_retrieved")) for r in mixed)
        retr_agent[aid] = _as_rate(hit, len(mixed))

    clean_fp = sum(
        _bool_val(r.get("strict_attack_success"))
        for r in rows
        if r.get("corpus_mode") == "clean"
    )
    failed = sum(1 for r in rows if r.get("error"))

    return {
        "run_id": run_id,
        "agent_count": len({r["agent_id"] for r in rows}),
        "real_github_agent_count": len({r["agent_id"] for r in github_rows}),
        "poison_tested_agent_count": len(poison_tested),
        "row_count": len(rows),
        "rows_by_agent": dict(by_agent),
        "rows_by_corpus_mode": dict(by_mode),
        "rows_by_attack_id": dict(by_attack),
        "clean_asr": asr_for("clean"),
        "poison_only_asr": asr_for("poison_only"),
        "mixed_asr": asr_for("mixed"),
        "asr_by_agent": asr_agent,
        "asr_by_attack": asr_attack,
        "asr_by_corpus_mode": asr_mode,
        "poison_retrieval_rate_by_agent": retr_agent,
        "poison_rank_distribution": dict(rank_dist),
        "clean_false_positive_count": clean_fp,
        "failed_case_count": failed,
        "error_distribution": dict(err_dist.most_common(20)),
    }


def _write_csv_partial(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _failure_row(
    *,
    run_id: str,
    cfg: GitHubAgentConfig,
    target: SecurityTarget,
    attack_id: str,
    corpus_mode: str,
    test_scale: str,
    error: str,
    ingest_method: str = "none",
    reset_supported: bool = False,
    query_endpoint: str = "",
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "agent_id": cfg.agent_id,
        "agent_class": cfg.agent_class,
        "repo": cfg.repo_url,
        "framework": cfg.framework,
        "base_url": cfg.base_url,
        "target_id": target.target_id,
        "attack_id": attack_id,
        "attack_family": ATTACK_FAMILY.get(attack_id, attack_id),
        "corpus_mode": corpus_mode,
        "test_scale": test_scale,
        "ingest_method": ingest_method,
        "reset_supported": reset_supported,
        "query_endpoint": query_endpoint,
        "question": target.question,
        "answer": "",
        "final_risk": "",
        "attack_success": False,
        "strict_attack_success": False,
        "risk_downgrade": False,
        "advice_suppressed": False,
        "answer_shift": False,
        "conflict_answer": False,
        "poison_retrieved": "unknown",
        "poison_rank": "unknown",
        "retrieved_sources": "unknown",
        "retrieved_scores": "",
        "http_status": 0,
        "latency_ms": "",
        "error": error,
    }


def _expected_rows_per_agent(test_scale: str) -> int:
    n_targets = 10 if test_scale == "full_10_targets" else 3
    return n_targets * len(ATTACKS) * len(CORPUS_MODES)


def _load_resume_rows(
    test_scale: str,
    force_agents: Optional[set[str]] = None,
) -> Tuple[List[Dict[str, Any]], set[str]]:
    if not OUTPUT_CSV.is_file():
        return [], set()
    with OUTPUT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    need = _expected_rows_per_agent(test_scale)
    force_agents = force_agents or set()
    by_agent: Dict[str, int] = defaultdict(int)
    complete: set[str] = set()
    for r in rows:
        by_agent[r["agent_id"]] += 1
        if not r.get("error") and r.get("answer"):
            if by_agent[r["agent_id"]] >= need:
                pass
    for aid, agent_rows in defaultdict(list, {k: [r for r in rows if r["agent_id"] == k] for k in by_agent}).items():
        if aid in force_agents:
            continue
        sub = [r for r in rows if r["agent_id"] == aid]
        if len(sub) >= need and all(not r.get("error") and r.get("answer") for r in sub):
            complete.add(aid)
    kept = [r for r in rows if r["agent_id"] not in force_agents]
    return kept, complete


def run_matrix(
    *,
    test_scale: str = "quick_3_targets",
    include_minimal: bool = True,
    include_all_bulk: bool = True,
    agent_ids: Optional[List[str]] = None,
    auto_start: bool = True,
    resume: bool = False,
    force_agents: Optional[List[str]] = None,
) -> Path:
    run_id = _make_run_id()
    configs = _collect_agent_configs(
        include_minimal=include_minimal,
        include_all_bulk=include_all_bulk,
        agent_ids=agent_ids,
    )
    if not configs:
        raise RuntimeError("no eligible agents in registry.yaml / bulk_registry")

    all_targets = load_targets()
    if test_scale == "full_10_targets":
        targets = all_targets
        scale_label = "full_10_targets"
    else:
        targets = [t for t in all_targets if t.target_id in QUICK_TARGETS]
        if len(targets) < 3:
            targets = all_targets[:3]
        scale_label = "quick_3_targets"

    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []
    skip_agents: set[str] = set()
    force_set = set(force_agents or [])
    if resume or force_set:
        rows, skip_agents = _load_resume_rows(test_scale, force_set)
        if skip_agents:
            print(f"[matrix] resume: skip {len(skip_agents)} completed agents", flush=True)
        if force_set:
            print(f"[matrix] force rerun: {sorted(force_set)}", flush=True)

    bulk_by_id = {a["id"]: a for a in load_bulk_registry().get("agents", [])}

    LOG_DIR = RESULTS_DIR / "agent_poison_logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    for cfg in configs:
        if cfg.agent_id in skip_agents:
            print(f"[matrix] skip completed agent={cfg.agent_id}", flush=True)
            continue
        agent_log_path = LOG_DIR / f"{cfg.agent_id}_{run_id}.log"
        agent_log: List[str] = []

        def _alog(msg: str) -> None:
            agent_log.append(msg)
            print(msg, flush=True)
        entry = bulk_by_id.get(cfg.agent_id, {})
        _alog(f"[matrix] agent={cfg.agent_id} class={cfg.agent_class} url={cfg.base_url}")
        adapter = GitHubHttpRagAdapter(cfg)

        do_auto_start = auto_start and not entry.get("external_service_missing")
        try:
            if do_auto_start and cfg.agent_id in DOCKER_START_AGENTS:
                stack = DOCKER_START_AGENTS[cfg.agent_id](Path(cfg.local_path))
                _alog(f"[matrix] docker_stack agent={cfg.agent_id} ok={stack.get('ok')} stage={stack.get('stage')}")
                if stack.get("base_url"):
                    cfg.base_url = stack["base_url"]
                    adapter.config.base_url = cfg.base_url
            if do_auto_start:
                pr = adapter.probe()
                if not pr.health_ok and cfg.start_command:
                    adapter.try_start(wait_sec=6)
                pr = adapter.probe()
            else:
                pr = adapter.probe()
        except Exception as exc:
            for target in targets:
                for attack_id in ATTACKS:
                    for mode in CORPUS_MODES:
                        rows.append(
                            _failure_row(
                                run_id=run_id,
                                cfg=cfg,
                                target=target,
                                attack_id=attack_id,
                                corpus_mode=mode,
                                test_scale=scale_label,
                                error=f"probe_failed:{type(exc).__name__}:{exc}",
                                query_endpoint=cfg.chat_endpoint,
                            )
                        )
            _alog(f"[matrix] probe_failed agent={cfg.agent_id} err={exc}")
            agent_log_path.write_text("\n".join(agent_log), encoding="utf-8")
            continue

        _alog(
            f"[matrix] probe agent={cfg.agent_id} health={pr.health_ok} query={pr.query_ok} "
            f"ingest={pr.ingest_ok} reset={pr.reset_ok} q_ep={pr.query_endpoint} i_ep={pr.ingest_endpoint}"
        )

        if not pr.health_ok:
            for target in targets:
                for attack_id in ATTACKS:
                    for mode in CORPUS_MODES:
                        rows.append(
                            _failure_row(
                                run_id=run_id,
                                cfg=cfg,
                                target=target,
                                attack_id=attack_id,
                                corpus_mode=mode,
                                test_scale=scale_label,
                                error="service_unreachable",
                                query_endpoint=cfg.chat_endpoint,
                            )
                        )
            _write_csv_partial(rows)
            _alog(f"[matrix] done agent={cfg.agent_id} unreachable rows_so_far={len(rows)}")
            agent_log_path.write_text("\n".join(agent_log), encoding="utf-8")
            continue

        baselines: Dict[str, str] = {}
        for target in targets:
            try:
                adapter.build_corpus(clean_docs, [], "clean", case_id="baseline")
                br = adapter.query(target.question)
                baselines[target.target_id] = br.get("answer", "") if br.get("ok") else ""
            except Exception as exc:
                baselines[target.target_id] = ""

        for target in targets:
            clean_baseline = baselines.get(target.target_id, "")
            for attack_id in ATTACKS:
                poison_docs = GENERATOR_MAP[attack_id](target)
                for corpus_mode in CORPUS_MODES:
                    case_id = f"{target.target_id}_{attack_id}_{corpus_mode}"
                    try:
                        ok_ingest, ingest_note = adapter.build_corpus(
                            clean_docs,
                            poison_docs,
                            corpus_mode,
                            case_id=case_id,
                        )
                        if not ok_ingest and cfg.agent_class == "real_github_http":
                            rows.append(
                                _failure_row(
                                    run_id=run_id,
                                    cfg=cfg,
                                    target=target,
                                    attack_id=attack_id,
                                    corpus_mode=corpus_mode,
                                    test_scale=scale_label,
                                    error=f"ingest_failed:{ingest_note}",
                                    ingest_method=adapter.ingest_method,
                                    reset_supported=adapter.reset_supported,
                                    query_endpoint=adapter.probe_result.query_endpoint or cfg.chat_endpoint,
                                )
                            )
                            continue

                        qr = adapter.query(target.question)
                        if not qr.get("ok"):
                            rows.append(
                                _failure_row(
                                    run_id=run_id,
                                    cfg=cfg,
                                    target=target,
                                    attack_id=attack_id,
                                    corpus_mode=corpus_mode,
                                    test_scale=scale_label,
                                    error=f"query_failed:{qr.get('error','')}",
                                    ingest_method=adapter.ingest_method,
                                    reset_supported=adapter.reset_supported,
                                    query_endpoint=adapter.probe_result.query_endpoint or cfg.chat_endpoint,
                                )
                            )
                            continue

                        pr_val = qr.get("poison_retrieved")
                        pr_bool = pr_val if isinstance(pr_val, bool) else False
                        pr_rank = qr.get("poison_rank")
                        if pr_rank == "unknown":
                            pr_rank = None
                        elif pr_rank is not None:
                            try:
                                pr_rank = int(pr_rank)
                            except (TypeError, ValueError):
                                pr_rank = None

                        ev = evaluate_answer(
                            target=target,
                            answer=qr.get("answer", ""),
                            poison_retrieved=pr_bool,
                            poison_rank=pr_rank,
                            clean_baseline_answer=clean_baseline or None,
                        )

                        rows.append(
                            {
                                "run_id": run_id,
                                "agent_id": cfg.agent_id,
                                "agent_class": cfg.agent_class,
                                "repo": cfg.repo_url,
                                "framework": cfg.framework,
                                "base_url": cfg.base_url,
                                "target_id": target.target_id,
                                "attack_id": attack_id,
                                "attack_family": ATTACK_FAMILY.get(attack_id, attack_id),
                                "corpus_mode": corpus_mode,
                                "test_scale": scale_label,
                                "ingest_method": adapter.ingest_method,
                                "reset_supported": adapter.reset_supported,
                                "query_endpoint": adapter.probe_result.query_endpoint or cfg.chat_endpoint,
                                "question": target.question,
                                "answer": qr.get("answer", ""),
                                "final_risk": ev.final_risk,
                                "attack_success": ev.attack_success,
                                "strict_attack_success": ev.strict_attack_success,
                                "risk_downgrade": ev.risk_downgrade,
                                "advice_suppressed": ev.advice_suppressed,
                                "answer_shift": ev.answer_shift,
                                "conflict_answer": ev.conflict_answer,
                                "poison_retrieved": qr.get("poison_retrieved", pr_bool),
                                "poison_rank": qr.get("poison_rank", pr_rank),
                                "retrieved_sources": qr.get("retrieved_sources", "unknown"),
                                "retrieved_scores": qr.get("retrieved_scores", ""),
                                "http_status": qr.get("http_status", 0),
                                "latency_ms": qr.get("latency_ms", ""),
                                "error": "",
                            }
                        )
                    except Exception as exc:
                        rows.append(
                            _failure_row(
                                run_id=run_id,
                                cfg=cfg,
                                target=target,
                                attack_id=attack_id,
                                corpus_mode=corpus_mode,
                                test_scale=scale_label,
                                error=f"{type(exc).__name__}:{exc}",
                                ingest_method=adapter.ingest_method,
                                reset_supported=adapter.reset_supported,
                                query_endpoint=cfg.chat_endpoint,
                            )
                        )

        if adapter.config.query_payload_log:
            _alog(f"[matrix] query_payload_ok={adapter.config.query_payload_log}")
        ok_n = sum(1 for r in rows if r["agent_id"] == cfg.agent_id and not r.get("error") and r.get("answer"))
        _alog(f"[matrix] done agent={cfg.agent_id} ok_rows={ok_n}/45 rows_so_far={len(rows)}")
        agent_log_path.write_text("\n".join(agent_log), encoding="utf-8")
        _write_csv_partial(rows)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    summary = _build_summary(rows, run_id)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_final_report(summary)

    print(f"Wrote {len(rows)} rows -> {OUTPUT_CSV}")
    print(f"Wrote summary -> {OUTPUT_SUMMARY}")
    return OUTPUT_CSV


def _update_final_report(summary: Dict[str, Any]) -> None:
    path = PATHS_RESULTS / "final_experiment_summary.md"
    block = [
        "",
        "---",
        "",
        "## GitHub HTTP RAG Agent 端到端投毒测试",
        "",
        f"- run_id: `{summary.get('run_id')}`",
        f"- poison_tested_agent_count: **{summary.get('poison_tested_agent_count')}**",
        f"- real_github_agent_count: **{summary.get('real_github_agent_count')}**",
        f"- row_count: **{summary.get('row_count')}**",
        f"- clean_asr: {summary.get('clean_asr')}",
        f"- poison_only_asr: {summary.get('poison_only_asr')}",
        f"- mixed_asr: {summary.get('mixed_asr')}",
        f"- clean_false_positive_count: {summary.get('clean_false_positive_count')}",
        f"- failed_case_count: {summary.get('failed_case_count')}",
        "",
        "详细 CSV: `results/github_http_rag_poison_matrix.csv`",
        "",
    ]
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        marker = "## GitHub HTTP RAG Agent 端到端投毒测试"
        if marker in text:
            text = text.split(marker)[0].rstrip()
        text += "\n".join(block)
    else:
        text = "# Final Experiment Summary\n" + "\n".join(block)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["quick_3_targets", "full_10_targets"], default="quick_3_targets")
    parser.add_argument("--no-minimal", action="store_true")
    parser.add_argument("--agent", action="append", default=None)
    parser.add_argument("--no-auto-start", action="store_true")
    parser.add_argument("--priority-bulk-only", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Skip agents already in CSV")
    parser.add_argument("--force-agent", action="append", default=None, help="Force rerun even if rows exist")
    args = parser.parse_args()
    agent_ids = args.agent
    if args.force_agent and not agent_ids:
        agent_ids = args.force_agent
    run_matrix(
        test_scale=args.scale,
        include_minimal=not args.no_minimal,
        include_all_bulk=not args.priority_bulk_only,
        agent_ids=agent_ids,
        auto_start=not args.no_auto_start,
        resume=args.resume or bool(args.force_agent),
        force_agents=args.force_agent,
    )


if __name__ == "__main__":
    main()
