"""File-based RAG poison matrix for external GitHub agents without HTTP ingest."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    detect_kb_path,
)
from target_agents.bulk_common import RESULTS_DIR, load_registry as load_bulk_registry
from utils.corpus import load_clean_documents
from utils.targets import SecurityTarget, load_targets

MANIFEST_PATH = SCRIPT_DIR.parent / "bulk_agent_poison_manifest.yaml"
OUTPUT_CSV = RESULTS_DIR / "file_based_agent_poison_matrix.csv"
OUTPUT_SUMMARY = RESULTS_DIR / "file_based_agent_poison_summary.csv"
OUTPUT_REPORT = RESULTS_DIR / "file_based_agent_poison_report.md"
LOG_DIR = RESULTS_DIR / "agent_poison_logs"

FILE_AGENTS = ["agent-service-toolkit", "ai-chatkit", "tech-trends-chatbot"]
TECH_TRENDS_LOADER = SCRIPT_DIR / "tech_trends_poison_load.py"
INDEX_COMMANDS = [
    ["python", "ingest.py"],
    ["python", "build_index.py"],
    ["python", "create_index.py"],
    ["python", "load_docs.py"],
    ["python", "app.py", "--ingest"],
    ["python", "main.py", "--ingest"],
    ["poetry", "run", "load"],
]
KB_DIR_NAMES = (
    "data", "docs", "documents", "knowledge_base", "uploads",
    "source_documents", "storage", "vectorstore", "backend/data", "backend/data/docs",
)
ATTACKS = [
    "content_poison", "rule_poison", "retrieval_hijack_poison",
    "context_manipulation_poison", "instruction_injection_poison",
]
CORPUS_MODES = ["clean", "poison_only", "mixed"]
QUICK_TARGETS = ["researchhelper_rag_risk", "toolreport_tool_output_risk", "websearch_external_content_risk"]
CSV_FIELDS = [
    "run_id", "agent_id", "adapter_category", "test_mode", "repo", "framework",
    "base_url", "target_id", "attack_id", "corpus_mode", "test_scale",
    "ingest_method", "kb_path", "index_command", "question", "answer",
    "attack_success", "strict_attack_success", "poison_retrieved", "poison_rank",
    "retrieved_sources", "http_status", "error",
]


def _make_run_id() -> str:
    return f"file_based_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_manifest() -> Dict[str, Dict[str, Any]]:
    if not MANIFEST_PATH.is_file():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("agents", {})


def _find_kb(repo: Path) -> Path:
    for name in KB_DIR_NAMES:
        p = repo / name
        if p.is_dir():
            return p
    return repo / "data" / f"poison_exp_{uuid.uuid4().hex[:8]}"


def _find_index_command(repo: Path, venv_py: Optional[Path], agent_id: str = "") -> Optional[List[str]]:
    py = str(venv_py) if venv_py and venv_py.is_file() else "python"
    if agent_id == "tech-trends-chatbot" and TECH_TRENDS_LOADER.is_file():
        backend = repo / "backend" if (repo / "backend").is_dir() else repo
        return [py, str(TECH_TRENDS_LOADER), "--backend", str(backend), "--docs-dir", str(backend / "data" / "docs")]
    for cmd in INDEX_COMMANDS:
        script = cmd[1] if cmd[0] in ("python", "poetry") else cmd[0]
        if (repo / script).is_file() or cmd[0] == "poetry":
            if cmd[0] == "python":
                return [py, script] + cmd[2:]
            return cmd
    for name in ("ingest.py", "build_index.py", "create_index.py", "load_docs.py"):
        if (repo / name).is_file():
            return [py, name]
    return None


def _agent_config(aid: str) -> GitHubAgentConfig:
    bulk = {a["id"]: a for a in load_bulk_registry().get("agents", [])}
    entry = bulk.get(aid)
    if not entry:
        raise RuntimeError(f"agent not in bulk registry: {aid}")
    mf = _load_manifest().get(aid, {})
    cfg = config_from_bulk_entry(entry, mf)
    cfg = apply_manifest_overrides(cfg, mf, entry)
    repo = Path(cfg.local_path)
    cfg.kb_path = str(_find_kb(repo))
    cfg.ingest_style = "file_kb"
    cfg.ingest_endpoint = ""
    cfg.request_format = mf.get("request_format") or "question"
    return cfg


def _run_index(repo: Path, cmd: Optional[List[str]], timeout: int = 120) -> str:
    if not cmd:
        return "no_index_command"
    try:
        subprocess.run(cmd, cwd=str(repo), capture_output=True, timeout=timeout, shell=False)
        return " ".join(cmd)
    except Exception as exc:
        return f"index_failed:{exc}"


def run_matrix(*, agent_ids: List[str], test_scale: str = "quick_3_targets") -> Path:
    run_id = _make_run_id()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    all_targets = load_targets()
    targets = [t for t in all_targets if t.target_id in QUICK_TARGETS] or all_targets[:3]
    clean_docs = load_clean_documents()
    rows: List[Dict[str, Any]] = []

    for aid in agent_ids:
        log_lines: List[str] = []
        log_path = LOG_DIR / f"{aid}_file_poison.log"
        try:
            cfg = _agent_config(aid)
        except Exception as exc:
            for target in targets:
                for attack_id in ATTACKS:
                    for mode in CORPUS_MODES:
                        rows.append({
                            "run_id": run_id, "agent_id": aid, "adapter_category": "B_file_based_rag",
                            "test_mode": "file_based", "error": f"config_error:{exc}",
                            "corpus_mode": mode, "attack_id": attack_id, "target_id": target.target_id,
                        })
            log_path.write_text(f"config_error: {exc}", encoding="utf-8")
            continue

        repo = Path(cfg.local_path)
        venv_py = Path(cfg.venv_path) / "Scripts" / "python.exe" if cfg.venv_path else None
        index_cmd = _find_index_command(repo, venv_py, aid)
        adapter = GitHubHttpRagAdapter(cfg)
        adapter.ingest_method = "file_kb"

        if aid == "tech-trends-chatbot":
            from target_agents.scripts.docker_agent_helper import start_tech_trends_stack
            stack = start_tech_trends_stack(repo)
            log_lines.append(f"tech_trends_stack={stack}")
            if stack.get("base_url"):
                cfg.base_url = stack["base_url"]
                adapter.config.base_url = cfg.base_url
        elif cfg.start_command:
            subprocess.Popen(cfg.start_command, cwd=cfg.start_cwd or str(repo), shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(8)
            adapter.probe(timeout=10)

        session_kb = _find_kb(repo) / f"poison_exp_{run_id}"
        session_kb.mkdir(parents=True, exist_ok=True)
        cfg.kb_path = str(session_kb)
        adapter.config.kb_path = str(session_kb)

        baselines: Dict[str, str] = {}
        for target in targets:
            try:
                adapter.build_corpus(clean_docs, [], "clean", case_id=f"baseline_{target.target_id}")
                _run_index(repo, index_cmd)
                if adapter.probe_result.health_ok or cfg.base_url:
                    qr = adapter.query(target.question)
                    baselines[target.target_id] = qr.get("answer", "") if qr.get("ok") else ""
                else:
                    baselines[target.target_id] = ""
            except Exception:
                baselines[target.target_id] = ""

        for target in targets:
            for attack_id in ATTACKS:
                poison_docs = template_generators.generate_poison_docs(attack_id, target)
                for mode in CORPUS_MODES:
                    case_id = f"{target.target_id}_{attack_id}_{mode}"
                    try:
                        ok, note = adapter.build_corpus(clean_docs, poison_docs, mode, case_id=case_id)
                        idx_note = _run_index(repo, index_cmd)
                        if not ok:
                            rows.append({
                                "run_id": run_id, "agent_id": aid, "adapter_category": "B_file_based_rag",
                                "test_mode": "file_based", "repo": cfg.repo_url, "framework": cfg.framework,
                                "base_url": cfg.base_url, "target_id": target.target_id, "attack_id": attack_id,
                                "corpus_mode": mode, "test_scale": test_scale, "ingest_method": "file_kb",
                                "kb_path": cfg.kb_path, "index_command": idx_note, "question": target.question,
                                "error": f"ingest_failed:{note}",
                            })
                            continue
                        qr = adapter.query(target.question)
                        if not qr.get("ok") or not qr.get("answer"):
                            rows.append({
                                "run_id": run_id, "agent_id": aid, "adapter_category": "B_file_based_rag",
                                "test_mode": "file_based", "repo": cfg.repo_url, "target_id": target.target_id,
                                "attack_id": attack_id, "corpus_mode": mode, "test_scale": test_scale,
                                "ingest_method": "file_kb", "kb_path": cfg.kb_path, "index_command": idx_note,
                                "question": target.question,
                                "error": "file_ingest_success_but_query_missing" if ok else f"query_failed:{qr.get('error')}",
                            })
                            continue
                        pr_val = qr.get("poison_retrieved")
                        pr_bool = pr_val if isinstance(pr_val, bool) else False
                        pr_rank = qr.get("poison_rank")
                        ev = evaluate_answer(
                            target=target, answer=qr.get("answer", ""),
                            poison_retrieved=pr_bool,
                            poison_rank=int(pr_rank) if pr_rank not in (None, "unknown") else None,
                            clean_baseline_answer=baselines.get(target.target_id) or None,
                        )
                        rows.append({
                            "run_id": run_id, "agent_id": aid, "adapter_category": "B_file_based_rag",
                            "test_mode": "file_based", "repo": cfg.repo_url, "framework": cfg.framework,
                            "base_url": cfg.base_url, "target_id": target.target_id, "attack_id": attack_id,
                            "corpus_mode": mode, "test_scale": test_scale, "ingest_method": "file_kb",
                            "kb_path": cfg.kb_path, "index_command": idx_note, "question": target.question,
                            "answer": qr.get("answer", ""), "attack_success": ev.attack_success,
                            "strict_attack_success": ev.strict_attack_success,
                            "poison_retrieved": qr.get("poison_retrieved", pr_bool),
                            "poison_rank": qr.get("poison_rank", pr_rank),
                            "retrieved_sources": qr.get("retrieved_sources", ""),
                            "http_status": qr.get("http_status", 0), "error": "",
                        })
                    except Exception as exc:
                        rows.append({
                            "run_id": run_id, "agent_id": aid, "adapter_category": "B_file_based_rag",
                            "test_mode": "file_based", "target_id": target.target_id, "attack_id": attack_id,
                            "corpus_mode": mode, "error": f"{type(exc).__name__}:{exc}",
                        })
        ok_n = sum(1 for r in rows if r.get("agent_id") == aid and not r.get("error") and r.get("answer"))
        log_lines.append(f"agent={aid} ok_rows={ok_n}")
        log_path.write_text("\n".join(log_lines), encoding="utf-8")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged_rows = rows
    if OUTPUT_CSV.is_file() and len(agent_ids) < len(FILE_AGENTS):
        existing = _load_csv(OUTPUT_CSV)
        keep = [r for r in existing if r.get("agent_id") not in agent_ids]
        merged_rows = keep + rows
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged_rows)

    by_agent: Dict[str, List[Dict]] = defaultdict(list)
    for r in merged_rows:
        by_agent[r["agent_id"]].append(r)
    summary_rows = []
    for aid, sub in by_agent.items():
        ok = sum(1 for r in sub if not r.get("error") and r.get("answer"))
        summary_rows.append({
            "agent_id": aid, "total_rows": len(sub), "success_rows": ok,
            "failed_rows": len(sub) - ok,
            "poison_loop_complete": ok == len(sub) and len(sub) >= 45,
        })
    with OUTPUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else ["agent_id"])
        w.writeheader()
        w.writerows(summary_rows)
    OUTPUT_REPORT.write_text(
        f"# File-based Agent Poison Report\n\nrun_id={run_id}\nagents={agent_ids}\nrows={len(merged_rows)}\n",
        encoding="utf-8",
    )
    return OUTPUT_CSV


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="append", default=None)
    parser.add_argument("--scale", default="quick_3_targets")
    args = parser.parse_args()
    aids = args.agent or FILE_AGENTS
    run_matrix(agent_ids=aids, test_scale=args.scale)
    print(f"Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
