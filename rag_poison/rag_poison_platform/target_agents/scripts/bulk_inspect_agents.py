"""Level 1b: Static repo inspection."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    load_registry,
    repo_path,
    save_registry,
    scan_repo_features,
    write_csv,
    now_iso,
)


def main() -> None:
    reg = load_registry()
    rows = []
    for a in reg.get("agents", []):
        aid = a["id"]
        repo = repo_path(aid)
        if not repo.is_dir():
            rows.append({"agent_id": aid, "inspected": False, "error": "no_repo"})
            continue
        feats = scan_repo_features(repo)
        a.update(feats)
        le = feats.get("likely_endpoints", {})
        a["docs_endpoint"] = le.get("docs", "/docs")
        a["health_endpoint"] = le.get("health", "")
        a["chat_endpoint"] = le.get("chat", le.get("invoke", ""))
        a["query_endpoint"] = le.get("query", "")
        a["ingest_endpoint"] = le.get("ingest", le.get("upload", le.get("documents", "")))
        if a.get("clone_success"):
            a["status"] = "cloned"
        a["tested_at"] = now_iso()
        rows.append(
            {
                "agent_id": aid,
                "inspected": True,
                "has_fastapi": feats.get("has_fastapi"),
                "has_langchain": feats.get("has_langchain"),
                "has_chroma": feats.get("has_chroma"),
                "has_faiss": feats.get("has_faiss"),
                "query_endpoint": a.get("query_endpoint"),
                "ingest_endpoint": a.get("ingest_endpoint"),
                "requires_docker": feats.get("requires_docker"),
            }
        )
        print(f"[inspect] {aid} fastapi={feats.get('has_fastapi')}")

    save_registry(reg)
    write_csv(RESULTS_DIR / "bulk_agent_inspect_report.csv", rows)
    print(f"Inspect done: {len(rows)}")


if __name__ == "__main__":
    main()
