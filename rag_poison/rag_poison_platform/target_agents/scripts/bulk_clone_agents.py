"""Level 1a: Bulk git clone."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    agent_root,
    load_registry,
    repo_path,
    run_cmd,
    save_registry,
    write_csv,
    write_log,
    now_iso,
)


def main() -> None:
    reg = load_registry()
    rows = []
    for a in reg.get("agents", []):
        aid = a["id"]
        url = a["repo_url"]
        dest = repo_path(aid)
        agent_root(aid).mkdir(parents=True, exist_ok=True)
        if dest.is_dir() and any(dest.iterdir()):
            code, out = 0, "already_cloned"
            success = True
            status = "cloned"
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            code, out = run_cmd(
                ["git", "clone", "--depth", "1", url, str(dest)],
                timeout=300,
            )
            success = code == 0 and dest.is_dir()
            status = "cloned" if success else "clone_failed"
        write_log(aid, "clone.log", out)
        a.update(
            {
                "clone_success": success,
                "status": status,
                "error_stage": "" if success else "clone",
                "error_summary": "" if success else out[-500:],
                "tested_at": now_iso(),
            }
        )
        rows.append(
            {
                "agent_id": aid,
                "repo_url": url,
                "clone_success": success,
                "status": status,
                "local_path": str(dest),
                "error": "" if success else out[-200:],
            }
        )
        print(f"[clone] {aid} success={success}")

    save_registry(reg)
    write_csv(RESULTS_DIR / "bulk_agent_clone_report.csv", rows)
    ok = sum(1 for r in rows if r["clone_success"])
    print(f"Clone done: {ok}/{len(rows)}")


if __name__ == "__main__":
    main()
