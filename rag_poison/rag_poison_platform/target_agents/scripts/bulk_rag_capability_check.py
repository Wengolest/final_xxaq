"""Check RAG capability: ingest + query + vector store signals."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    apply_api_dependency_fields,
    load_registry,
    repo_path,
    save_registry,
    write_csv,
    now_iso,
)


def check_rag_capable(agent: dict, repo: Path) -> dict:
    le = agent.get("likely_endpoints") or {}
    ingest = agent.get("ingest_endpoint") or le.get("ingest") or le.get("upload") or le.get("documents")
    query = agent.get("query_endpoint") or le.get("query") or agent.get("chat_endpoint") or le.get("chat")
    has_vs = any(
        agent.get(k) for k in ("has_chroma", "has_faiss", "has_qdrant", "has_llamaindex")
    )
    kb_dirs = []
    for name in ("data", "knowledge", "knowledge_base", "documents", "docs", "vectorstore", "chroma_db"):
        if (repo / name).is_dir():
            kb_dirs.append(name)

    rag_capable = bool(
        agent.get("http_api_success")
        and query
        and (ingest or kb_dirs or has_vs)
    )
    return {
        "rag_capable": rag_capable,
        "ingest_endpoint": ingest or "",
        "query_endpoint": query or "",
        "knowledge_dirs": "|".join(kb_dirs),
        "has_vector_store_lib": has_vs,
        "rag_signals": f"ingest={bool(ingest)} kb={bool(kb_dirs)} vs={has_vs}",
    }


def main() -> None:
    reg = load_registry()
    rows = []
    for a in reg.get("agents", []):
        if not a.get("http_api_success") and not a.get("clone_success"):
            continue
        repo = repo_path(a["id"])
        if repo.is_dir():
            apply_api_dependency_fields(a, repo)
        info = check_rag_capable(a, repo) if repo.is_dir() else {"rag_capable": False}
        a.update(info)
        if info.get("rag_capable"):
            a["status"] = "rag_capable"
        if a.get("external_service_missing"):
            a["poison_test_supported"] = False
            a["sample_type"] = "api_dependent_agent"
        elif info.get("rag_capable") and a.get("http_api_success"):
            a["poison_test_supported"] = True
            a["sample_type"] = "external_github_agent"
        a["tested_at"] = now_iso()
        rows.append({"agent_id": a["id"], **info})
        print(f"[rag] {a['id']} capable={info.get('rag_capable')}")

    save_registry(reg)
    write_csv(RESULTS_DIR / "bulk_rag_capability_report.csv", rows)
    print(f"RAG capable: {sum(1 for r in rows if r.get('rag_capable'))}/{len(rows)}")


if __name__ == "__main__":
    main()
