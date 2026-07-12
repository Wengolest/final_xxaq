"""Long-run orchestrator for external GitHub agent RAG poison experiments."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
RESULTS = PLATFORM_ROOT / "results"
DIAG_CSV = RESULTS / "github_agent_failure_diagnosis.csv"
STATE_JSON = RESULTS / "external_agent_longrun_state.json"

DUPLICATE_AGENTS = {"langgraph_agents_shamspias": "langgraph-agents"}
DEFAULT_TIMEOUT = 900
DOCKER_TIMEOUT = 1500

DOCKER_PRIORITY = [
    "tech-trends-chatbot",
    "rag-fastapi-chatbot",
    "enterprise-rag-chatbot",
    "rag-template",
    "ai-healthcare-system",
]
NATIVE_PRIORITY = [
    "context-agent-rag",
    "enterprise-rag-chatbot",
    "ned-admission-llm-chatbot-fyp",
    "ai-healthcare-system",
    "rag-template",
    "gpt-researcher",
]
FILE_PRIORITY = ["tech-trends-chatbot", "agent-service-toolkit", "ai-chatkit"]
SIDECAR_PRIORITY = ["fastapi-meets-langgraph", "fastapi_meets_langgraph"]
SUCCESSFUL_QUICK = {
    "simple_rag_chatbot", "langserve", "langgraph-agents",
    "rag-with-langchain-and-fastapi", "gpt-researcher",
    "fastapi-meets-langgraph", "fastapi_meets_langgraph",
}


def _read_diag() -> List[Dict[str, str]]:
    if not DIAG_CSV.is_file():
        return []
    with DIAG_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_state() -> Dict[str, Any]:
    if STATE_JSON.is_file():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return {"completed": [], "failed": [], "skipped": [], "runs": []}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _completed_from_summaries() -> Set[str]:
    done: Set[str] = set()
    for path in (RESULTS / "github_external_agent_effective_summary.json",):
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            done.update(data.get("external_poison_loop_complete_agents", []))
    return done


def _run_cmd(cmd: List[str], timeout: int, dry_run: bool = False) -> int:
    print(f"[longrun] {' '.join(cmd)}", flush=True)
    if dry_run:
        return 0
    try:
        return subprocess.run(cmd, cwd=str(PLATFORM_ROOT), timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"[longrun] TIMEOUT after {timeout}s", flush=True)
        return 124


def _post_run() -> None:
    for script in ("build_github_effective_poison_summary.py", "bulk_generate_deployment_report.py"):
        p = SCRIPT_DIR / script
        if p.is_file():
            subprocess.run([sys.executable, str(p)], cwd=str(PLATFORM_ROOT), timeout=180)


def _runner_cmd(
    agent_id: str,
    category: str,
    scale: str,
    *,
    include_native: bool,
    include_docker: bool,
    include_file: bool,
    include_sidecar: bool,
    upgrade: bool,
    single_agent: Optional[str],
) -> Optional[List[str]]:
    py = sys.executable
    if agent_id in DUPLICATE_AGENTS:
        return None
    if single_agent and agent_id != single_agent:
        return None
    if upgrade and agent_id not in SUCCESSFUL_QUICK:
        return None

    if scale in ("standard_8_types", "full_10_types"):
        if category == "C_compat_sidecar" and include_sidecar:
            return None  # case matrix handles native; sidecar via separate for now
        if category in ("A_native_http_rag", "B_file_based_rag"):
            cmd = [py, str(SCRIPT_DIR / "run_poison_case_matrix.py"), "--scale", scale, "--resume"]
            if upgrade:
                cmd.append("--upgrade-successful-agents")
            if single_agent:
                cmd.extend(["--agent", single_agent])
            elif agent_id:
                cmd.extend(["--agent", agent_id])
            return cmd

    if category == "B_file_based_rag" and include_file:
        return [py, str(SCRIPT_DIR / "run_file_based_agent_poison_matrix.py"),
                "--agent", agent_id, "--scale", scale]
    if category == "C_compat_sidecar" and include_sidecar:
        return [py, str(SCRIPT_DIR / "run_compat_sidecar_agent_poison_matrix.py"),
                "--agent", agent_id, "--scale", scale]
    if category == "A_native_http_rag" and include_native:
        return [py, str(SCRIPT_DIR / "run_github_http_rag_poison_matrix.py"),
                "--scale", scale, "--no-minimal", "--force-agent", agent_id, "--resume"]
    return None


def _agent_queue(
    diag: List[Dict[str, str]],
    *,
    include_docker: bool,
    include_native: bool,
    include_file: bool,
    include_sidecar: bool,
    upgrade: bool,
) -> List[str]:
    by_id = {r["agent_id"]: r for r in diag}
    queue: List[str] = []
    if upgrade:
        return sorted(SUCCESSFUL_QUICK)
    if include_docker:
        queue.extend([a for a in DOCKER_PRIORITY if a in by_id])
    if include_native:
        queue.extend([a for a in NATIVE_PRIORITY if a in by_id and a not in queue])
    if include_file:
        queue.extend([a for a in FILE_PRIORITY if a in by_id and a not in queue])
    if include_sidecar:
        queue.extend([a for a in SIDECAR_PRIORITY if a in by_id and a not in queue])
    for r in diag:
        aid = r["agent_id"]
        if aid not in queue and r.get("adapter_category") != "D_not_suitable":
            if aid not in DUPLICATE_AGENTS:
                queue.append(aid)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-agents", type=int, default=8)
    parser.add_argument("--target-count", type=int, default=10)
    parser.add_argument("--scale", default="quick_3_targets",
                        choices=["quick_3_targets", "standard_8_types", "full_10_types"])
    parser.add_argument("--include-native", action="store_true")
    parser.add_argument("--include-docker", action="store_true")
    parser.add_argument("--include-file-based", action="store_true")
    parser.add_argument("--include-sidecar", action="store_true")
    parser.add_argument("--enable-poison-only", action="store_true")
    parser.add_argument("--timeout-per-agent", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--upgrade-successful-agents", action="store_true")
    parser.add_argument("--agent", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    include_native = args.include_native or args.upgrade_successful_agents
    include_docker = args.include_docker or args.upgrade_successful_agents
    include_file = args.include_file_based
    include_sidecar = args.include_sidecar or args.upgrade_successful_agents

    diag = _read_diag()
    state = _load_state()
    already = _completed_from_summaries() if args.resume and not args.upgrade_successful_agents else set()
    queue = _agent_queue(
        diag,
        include_docker=include_docker,
        include_native=include_native,
        include_file=include_file,
        include_sidecar=include_sidecar,
        upgrade=args.upgrade_successful_agents,
    )
    if args.agent:
        queue = [args.agent]

    ran = 0
    for aid in queue:
        if ran >= args.max_agents and not args.agent:
            break
        if aid in DUPLICATE_AGENTS:
            state.setdefault("skipped", []).append({"agent_id": aid, "reason": f"duplicate_of={DUPLICATE_AGENTS[aid]}"})
            _save_state(state)
            continue
        if args.resume and aid in already and args.scale == "quick_3_targets" and not args.upgrade_successful_agents:
            print(f"[longrun] skip completed quick {aid}", flush=True)
            continue
        row = next((r for r in diag if r["agent_id"] == aid), {})
        if row.get("adapter_category") == "D_not_suitable":
            continue
        cmd = _runner_cmd(
            aid, row.get("adapter_category", "A_native_http_rag"), args.scale,
            include_native=include_native, include_docker=include_docker,
            include_file=include_file, include_sidecar=include_sidecar,
            upgrade=args.upgrade_successful_agents, single_agent=args.agent,
        )
        if not cmd:
            continue
        timeout = DOCKER_TIMEOUT if row.get("requires_docker") == "True" or aid in DOCKER_PRIORITY else args.timeout_per_agent
        rc = _run_cmd(cmd, timeout, dry_run=args.dry_run)
        if not args.dry_run:
            _post_run()
            entry = {"agent_id": aid, "scale": args.scale, "rc": rc, "at": datetime.now().isoformat()}
            state.setdefault("runs", []).append(entry)
            if rc == 0:
                state.setdefault("completed", []).append(f"{aid}:{args.scale}")
            else:
                state.setdefault("failed", []).append(entry)
            _save_state(state)
        ran += 1
        done_count = len(_completed_from_summaries())
        print(f"[longrun] external_complete={done_count} target={args.target_count}", flush=True)
        if done_count >= args.target_count and args.scale == "quick_3_targets":
            break

    if not args.dry_run:
        _post_run()
    print(json.dumps({
        "ran": ran,
        "scale": args.scale,
        "completed_external": sorted(_completed_from_summaries()),
        "count": len(_completed_from_summaries()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
