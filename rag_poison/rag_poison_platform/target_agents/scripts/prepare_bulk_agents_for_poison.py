"""
Prepare bulk GitHub agents for poison testing: sync env, fix deps, probe HTTP.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.adapters.github_http_rag_adapter import (
    GitHubAgentConfig,
    GitHubHttpRagAdapter,
    apply_manifest_overrides,
    config_from_bulk_entry,
)
from target_agents.bulk_common import BULK_ROOT, RESULTS_DIR, load_registry, update_agent, save_registry

MANIFEST_PATH = SCRIPT_DIR.parent / "bulk_agent_poison_manifest.yaml"
PLATFORM_ENV = PLATFORM_ROOT / ".env"
PROBE_CSV = RESULTS_DIR / "bulk_agent_poison_probe.csv"


def _sync_env(agent_root: Path) -> None:
    ps1 = SCRIPT_DIR / "deploy_helpers.ps1"
    if ps1.is_file() and agent_root.is_dir():
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-AgentDir", str(agent_root)],
            capture_output=True,
            timeout=30,
        )


def _pip_install(venv_py: Path, packages: List[str], cwd: Path) -> Tuple[bool, str]:
    if not venv_py.is_file():
        return False, "no_venv_python"
    cmd = [str(venv_py), "-m", "pip", "install", "-q"] + packages
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
    return r.returncode == 0, (r.stderr or r.stdout)[-500:]


def _fix_common_deps(agent_id: str, repo: Path, venv_py: Path) -> List[str]:
    fixes: List[str] = []
    minimal = ["langchain-text-splitters", "python-dotenv", "uvicorn", "fastapi"]
    if agent_id in ("rag-with-langchain-and-fastapi", "langserve"):
        minimal.append("faiss-cpu")
    if agent_id == "langgraph-agents":
        minimal.extend(["chromadb", "langchain-chroma"])
    ok, msg = _pip_install(venv_py, minimal, repo)
    if ok:
        fixes.append("pip_minimal_deps")
    else:
        fixes.append(f"pip_partial:{msg[:80]}")

    if agent_id == "rag-with-langchain-and-fastapi":
        _apply_rag_langchain_patch(repo)
        fixes.append("rag_langchain_patch")
    if agent_id == "langgraph-agents":
        _apply_langgraph_patch(repo)
        fixes.append("langgraph_reset_patch")
    if agent_id == "langserve":
        _apply_langserve_patch(repo)
        fixes.append("langserve_patch")
    return fixes


def _apply_rag_langchain_patch(repo: Path) -> None:
    """test-only adapter for local poison evaluation"""
    rag_py = repo / "rag.py"
    if rag_py.is_file():
        text = rag_py.read_text(encoding="utf-8")
        if "POISON_TEST_FAKE_EMBEDDINGS" not in text:
            text = text.replace(
                "from langchain.text_splitter import RecursiveCharacterTextSplitter",
                "from langchain_text_splitters import RecursiveCharacterTextSplitter",
            )
            text = text.replace(
                "from langchain_openai.embeddings import OpenAIEmbeddings",
                "import os\nfrom langchain_openai.embeddings import OpenAIEmbeddings\n"
                "from langchain_community.embeddings import FakeEmbeddings",
            )
            old_setup = "    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)"
            new_setup = (
                "    if os.getenv('POISON_TEST_FAKE_EMBEDDINGS', '1') == '1':\n"
                "        embeddings = FakeEmbeddings(size=384)\n"
                "    else:\n"
                "        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)"
            )
            if old_setup in text:
                text = text.replace(old_setup, new_setup)
            rag_py.write_text(text, encoding="utf-8")

    ep = repo / "endpoints.py"
    if ep.is_file() and "/documents" not in ep.read_text(encoding="utf-8"):
        ep.write_text(
            '''# test-only adapter for local poison evaluation
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from rag import get_rag_response

router = APIRouter()

class DocIn(BaseModel):
    text: str
    doc_id: str = "doc"
    metadata: dict = {}

@router.get("/query/")
async def query_rag_system(query: str):
    try:
        response = await get_rag_response(query)
        return {"query": query, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents")
async def ingest_document(doc: DocIn):
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    path = data_dir / "my_document.txt"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    src = (doc.metadata or {}).get("source", "clean")
    header = f"\\n--- doc_id={doc.doc_id} source={src} ---\\n"
    path.write_text(existing + header + doc.text, encoding="utf-8")
    return {"ok": True, "doc_id": doc.doc_id, "source": src}

@router.post("/reset")
async def reset_kb():
    path = Path("data/my_document.txt")
    if path.is_file():
        path.unlink()
    return {"ok": True}
''',
            encoding="utf-8",
        )


def _apply_langgraph_patch(repo: Path) -> None:
    main_py = repo / "main.py"
    if not main_py.is_file():
        return
    text = main_py.read_text(encoding="utf-8")
    if "/reset" in text:
        return
    insert = '''

@app.post("/reset")
async def reset_collections(collection_name: str = "general_knowledge"):
    """test-only adapter for local poison evaluation"""
    try:
        from storage.vector_store import VectorStoreManager
        mgr = VectorStoreManager()
        mgr.delete_collection(collection_name)
        return {"ok": True, "collection": collection_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}
'''
    if 'if __name__ == "__main__"' in text:
        text = text.replace('if __name__ == "__main__"', insert + '\nif __name__ == "__main__"')
    else:
        text += insert
    main_py.write_text(text, encoding="utf-8")


def _apply_langserve_patch(repo: Path) -> None:
    server = repo / "examples" / "retrieval" / "server.py"
    if not server.is_file():
        return
    text = server.read_text(encoding="utf-8")
    if "test_poison_kb" in text:
        return
    extra = '''

# test-only adapter for local poison evaluation
from pydantic import BaseModel
from langchain_core.documents import Document

_poison_docs: list[Document] = []

class PoisonDocIn(BaseModel):
    text: str
    doc_id: str = "doc"
    metadata: dict = {}

@app.post("/test_ingest")
async def test_ingest(doc: PoisonDocIn):
    src = (doc.metadata or {}).get("source", "clean")
    _poison_docs.append(Document(page_content=doc.text, metadata={"source": src, "doc_id": doc.doc_id}))
    global vectorstore, retriever
    all_docs = [Document(page_content="cats like fish"), Document(page_content="dogs like sticks")] + _poison_docs
    vectorstore = FAISS.from_texts([d.page_content for d in all_docs], embedding=OpenAIEmbeddings(), metadatas=[d.metadata for d in all_docs])
    retriever = vectorstore.as_retriever()
    return {"ok": True, "count": len(_poison_docs)}

@app.post("/reset")
async def test_reset():
    global _poison_docs, vectorstore, retriever
    _poison_docs = []
    vectorstore = FAISS.from_texts(["cats like fish", "dogs like sticks"], embedding=OpenAIEmbeddings())
    retriever = vectorstore.as_retriever()
    return {"ok": True}
'''
    text = text.replace("if __name__ ==", extra + "\nif __name__ ==")
    server.write_text(text, encoding="utf-8")


def _load_manifest() -> Dict[str, Dict[str, Any]]:
    if not MANIFEST_PATH.is_file():
        return {}
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    return data.get("agents", {})


def _probe_agent(cfg: GitHubAgentConfig, auto_start: bool) -> Dict[str, Any]:
    adapter = GitHubHttpRagAdapter(cfg)
    if auto_start:
        pr = adapter.probe()
        if not pr.health_ok and cfg.start_command:
            adapter.try_start(wait_sec=12)
        pr = adapter.probe()
    else:
        pr = adapter.probe()
    return {
        "agent_id": cfg.agent_id,
        "base_url": cfg.base_url,
        "health_ok": pr.health_ok,
        "query_ok": pr.query_ok,
        "ingest_ok": pr.ingest_ok,
        "reset_ok": pr.reset_ok,
        "query_endpoint": pr.query_endpoint,
        "ingest_endpoint": pr.ingest_endpoint,
        "reset_endpoint": pr.reset_endpoint,
        "start_command": cfg.start_command,
        "ingest_style": cfg.ingest_style,
        "notes": pr.notes,
    }


def prepare_agents(agent_ids: Optional[List[str]] = None, auto_start: bool = True) -> List[Dict[str, Any]]:
    registry = load_registry()
    manifest = _load_manifest()
    results: List[Dict[str, Any]] = []

    for entry in registry.get("agents", []):
        aid = entry.get("id", "")
        if not entry.get("install_success"):
            continue
        if agent_ids and aid not in agent_ids:
            continue
        mf = manifest.get(aid, {})
        if mf.get("tier") == "skip":
            results.append({"agent_id": aid, "skipped": True, "reason": mf.get("notes", "skip")})
            continue

        agent_root = BULK_ROOT / aid
        repo = Path(entry.get("local_path", "")) or (agent_root / "repo")
        if not repo.is_dir():
            repo = agent_root / "repo"
        venv_py = Path(entry.get("venv_path", "")) / "Scripts" / "python.exe"
        if not venv_py.is_file():
            venv_py = agent_root / ".venv" / "Scripts" / "python.exe"

        _sync_env(agent_root)
        if repo.is_dir() and venv_py.is_file():
            fixes = _fix_common_deps(aid, repo, venv_py)
        else:
            fixes = ["repo_or_venv_missing"]

        cfg = config_from_bulk_entry(entry)
        cfg = apply_manifest_overrides(cfg, mf, entry)
        row = _probe_agent(cfg, auto_start=auto_start)
        row["fixes"] = fixes
        row["tier"] = mf.get("tier", "?")
        results.append(row)

        try:
            update_agent(
                registry,
                aid,
                startup_success=row["health_ok"],
                http_api_success=row["query_ok"],
                rag_capable=bool(mf.get("rag_capable")),
                api_base_url=cfg.base_url if row["health_ok"] else entry.get("api_base_url", ""),
                poison_test_supported=row["ingest_ok"] or row["query_ok"],
                chat_endpoint=row.get("query_endpoint") or cfg.chat_endpoint,
                ingest_endpoint=row.get("ingest_endpoint") or cfg.ingest_endpoint,
            )
        except KeyError:
            pass

    save_registry(registry)
    PROBE_CSV.parent.mkdir(parents=True, exist_ok=True)
    if results:
        import csv
        fields = sorted({k for r in results for k in r})
        with PROBE_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)
    print(f"Probed {len(results)} agents -> {PROBE_CSV}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", action="append", default=None)
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    rows = prepare_agents(agent_ids=args.agent, auto_start=not args.no_auto_start)
    ok = sum(1 for r in rows if r.get("health_ok") and r.get("query_ok"))
    print(f"Ready for poison test: {ok}/{len(rows)}")


if __name__ == "__main__":
    main()
