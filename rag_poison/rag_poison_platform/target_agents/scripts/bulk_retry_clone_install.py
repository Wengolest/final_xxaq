"""Retry clone + relaxed install for registry agents not yet install_success."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import load_registry, save_registry, write_csv, RESULTS_DIR, apply_api_dependency_fields, repo_path, agent_root, now_iso  # noqa: E402
from target_agents.scripts.bulk_crawl_github_agents import (  # noqa: E402
    TARGET_DEFAULT,
    _clone_agent,
    _count_install_success,
    _install_agent,
    _is_complete_agent,
    scan_repo_features,
)
from utils.deepseek_env import write_agent_env_file  # noqa: E402


def main() -> None:
    reg = load_registry()
    rows = []
    for agent in reg.get("agents", []):
        if agent.get("local_variant") or agent.get("id", "").startswith("local_"):
            continue
        if agent.get("install_success"):
            continue
        if agent.get("id") in {"langchain", "chroma", "dify", "open-webui", "langserve"}:
            continue
        url = agent.get("repo_url", "")
        if not url:
            continue

        ok, note = _clone_agent(agent)
        agent["clone_success"] = ok
        if not ok:
            rows.append({"agent_id": agent["id"], "status": "clone_failed", "notes": note})
            save_registry(reg)
            continue

        repo = repo_path(agent["id"])
        if not _is_complete_agent(agent, repo):
            rows.append({"agent_id": agent["id"], "status": "skipped", "notes": "not complete agent"})
            save_registry(reg)
            continue

        ok_i, err, note_i = _install_agent(agent)
        agent["install_attempted"] = True
        agent["install_success"] = ok_i
        agent["status"] = "installed" if ok_i else "install_failed"
        agent["error_type"] = err
        agent["tested_at"] = now_iso()
        if ok_i:
            apply_api_dependency_fields(agent, repo)
            write_agent_env_file(agent_root(agent["id"]), use_deepseek=True)
        rows.append({"agent_id": agent["id"], "status": agent["status"], "install_success": ok_i, "notes": note_i})
        save_registry(reg)
        print(f"[retry] {agent['id']} ok={ok_i} total={_count_install_success(reg)}", flush=True)

    write_csv(RESULTS_DIR / "bulk_retry_clone_install_report.csv", rows, fieldnames=["agent_id", "status", "install_success", "notes"])
    print(f"[retry] DONE install_success={_count_install_success(reg)}")


if __name__ == "__main__":
    main()
