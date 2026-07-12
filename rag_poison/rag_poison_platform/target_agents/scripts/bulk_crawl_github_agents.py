"""
Crawl GitHub for complete RAG agents, clone, venv install until TARGET count.

Retries clone/install failures automatically and skips to next candidate.
Does not modify A-F main experiment files or third-party repo source.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    AGENT_TEMPLATE,
    BULK_ROOT,
    RESULTS_DIR,
    agent_root,
    apply_api_dependency_fields,
    git_ls_remote,
    load_registry,
    repo_id_from_url,
    repo_path,
    run_cmd,
    save_registry,
    scan_repo_features,
    venv_path,
    write_csv,
    now_iso,
)
from utils.deepseek_env import write_agent_env_file  # noqa: E402

TARGET_DEFAULT = 20
CLONE_RETRIES = 2
INSTALL_TIMEOUT = 480
VENV_TIMEOUT = 120

FRAMEWORK_BLOCK = frozenset(
    {
        "langchain",
        "chroma",
        "dify",
        "open-webui",
        "llama_index",
        "llamaindex",
        "langserve",
        "langchain-chatchat",
        "langchain_chatchat",
        "notebooklm",
        "surfsense",
    }
)

CORE_RAG_PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "python-dotenv",
    "pydantic",
    "httpx",
    "openai",
    "tiktoken",
    "langchain",
    "langchain-core",
    "langchain-community",
    "langchain-openai",
    "langchain-chroma",
    "langgraph",
    "chromadb",
    "pypdf",
    "python-multipart",
    "sentence-transformers",
    "faiss-cpu",
    "rank-bm25",
    "aiofiles",
    "streamlit",
]

# Diverse complete-agent candidates (FastAPI / LangGraph / Chroma / FAISS / PDF / Ollama / multi-agent)
CRAWL_CANDIDATES: List[Dict[str, str]] = [
    {"repo_url": "https://github.com/JoshuaC215/agent-service-toolkit", "framework": "LangGraph+FastAPI+Streamlit", "reason": "full agent toolkit with RAG"},
    {"repo_url": "https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template", "framework": "FastAPI+LangGraph", "reason": "production LangGraph agent template"},
    {"repo_url": "https://github.com/ara-5/Genai-rag-agent", "framework": "LangGraph+RAG+CRAG", "reason": "agentic RAG with hybrid retrieval"},
    {"repo_url": "https://github.com/kanavkalra-in/rag_chatbot", "framework": "FastAPI+Streamlit+RAG", "reason": "multi-chatbot RAG service"},
    {"repo_url": "https://github.com/chelbapolandaa/Enterprise-AI-Customer-Support-Bot-Full-Stack-RAG-System", "framework": "FastAPI+FAISS+RAG", "reason": "customer support RAG bot"},
    {"repo_url": "https://github.com/TrueGrit16/KnowledgeAI", "framework": "FastAPI+Chroma+MultiAgent", "reason": "micro-agents RAG pipeline"},
    {"repo_url": "https://github.com/mallahyari/rag-agent-fastapi", "framework": "FastAPI+RAG", "reason": "RAG agent API"},
    {"repo_url": "https://github.com/alphasecio/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "LangChain RAG REST"},
    {"repo_url": "https://github.com/ranfysz/langchain-fastapi-rag", "framework": "FastAPI+LangChain", "reason": "document QA API"},
    {"repo_url": "https://github.com/sandeep-23/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "RAG FastAPI service"},
    {"repo_url": "https://github.com/ObSchwartz/fastapi-langchain-rag", "framework": "FastAPI+LangChain", "reason": "LangChain RAG server"},
    {"repo_url": "https://github.com/paveldedik/langchain-rag-api", "framework": "FastAPI+LangChain", "reason": "RAG REST API"},
    {"repo_url": "https://github.com/eyucoder/faq-chatbot-rag", "framework": "FastAPI+FAQ+RAG", "reason": "FAQ RAG chatbot"},
    {"repo_url": "https://github.com/Jaimboh/PDF-ChatBot-FastAPI", "framework": "FastAPI+PDF+RAG", "reason": "PDF chatbot API"},
    {"repo_url": "https://github.com/antoniolanza1996/rag-fastapi-langchain", "framework": "FastAPI+LangChain", "reason": "RAG LangChain API"},
    {"repo_url": "https://github.com/JeongJuhan/RAG_chatbot", "framework": "FastAPI+RAG", "reason": "RAG chatbot"},
    {"repo_url": "https://github.com/araweeli/fastapi-ollama-rag", "framework": "FastAPI+Ollama+RAG", "reason": "Ollama local RAG"},
    {"repo_url": "https://github.com/santorodeng/llama-rag-fastapi", "framework": "FastAPI+Llama+RAG", "reason": "Llama RAG API"},
    {"repo_url": "https://github.com/tjmlabs/fastapi-rag-template", "framework": "FastAPI+RAG", "reason": "RAG template app"},
    {"repo_url": "https://github.com/koenvandenberge/fastapi-rag-example", "framework": "FastAPI+RAG", "reason": "minimal RAG example"},
    {"repo_url": "https://github.com/Shauryasharma45/simple-rag-chatbot-fastapi", "framework": "FastAPI+RAG", "reason": "simple RAG API"},
    {"repo_url": "https://github.com/EthanCaddle/fastapi-rag", "framework": "FastAPI+RAG", "reason": "FastAPI RAG"},
    {"repo_url": "https://github.com/shauryasharma45/rag-fastapi", "framework": "FastAPI+RAG", "reason": "RAG FastAPI"},
    {"repo_url": "https://github.com/broadfield-ai/rag-chatbot-api", "framework": "FastAPI+RAG", "reason": "RAG chatbot API"},
    {"repo_url": "https://github.com/ttran9/crag-rag-agent", "framework": "LangChain+CRAG", "reason": "corrective RAG agent"},
    {"repo_url": "https://github.com/zahiry/franken-rag", "framework": "RAG+Multi", "reason": "Franken RAG agent"},
    {"repo_url": "https://github.com/SKNETWORKS-FAMILY-AICAMP/RAG-QnA-Langchain", "framework": "LangChain+RAG", "reason": "RAG QnA agent"},
    {"repo_url": "https://github.com/UETA-Takahiro/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "JP RAG FastAPI"},
    {"repo_url": "https://github.com/jermwang/fastapi-llm-app", "framework": "FastAPI+LLM", "reason": "LLM FastAPI app"},
    {"repo_url": "https://github.com/nadahasnim/fastapi-langgraph-starter-template", "framework": "FastAPI+LangGraph", "reason": "LangGraph starter"},
    {"repo_url": "https://github.com/imdeepmind/FastAPI-doc-QA-backend", "framework": "FastAPI+DocQA", "reason": "document QA backend"},
    {"repo_url": "https://github.com/Akshay-Khanna/FastAPI-RAG-Chatbot", "framework": "FastAPI+RAG", "reason": "RAG chatbot"},
    {"repo_url": "https://github.com/ssunpick/rag-fastapi", "framework": "FastAPI+RAG", "reason": "RAG FastAPI"},
    {"repo_url": "https://github.com/kyrolabs/chunkbase", "framework": "FastAPI+RAG", "reason": "chunking RAG API"},
    {"repo_url": "https://github.com/pixegami/langchain-rag-tutorial", "framework": "LangChain+RAG", "reason": "LangChain RAG tutorial app"},
    {"repo_url": "https://github.com/anarojoecheburua/RAG-with-Langchain-and-FastAPI", "framework": "FastAPI+FAISS", "reason": "FAISS RAG API"},
    {"repo_url": "https://github.com/iamtxena/simple-rag-chatbot", "framework": "FastAPI+Chroma", "reason": "simple RAG chatbot"},
    {"repo_url": "https://github.com/siddhantsaxena45/full_stack_rag_chatbot_with_memory", "framework": "FastAPI+FAISS+Memory", "reason": "RAG with memory"},
    {"repo_url": "https://github.com/coreybello/enterprise-rag-chatbot", "framework": "FastAPI+AgenticRAG", "reason": "enterprise agentic RAG"},
    {"repo_url": "https://github.com/run-llama/rags", "framework": "LlamaIndex+RAG", "reason": "LlamaIndex RAG app"},
    {"repo_url": "https://github.com/QuentinFuxa/PolyRAG", "framework": "FastAPI+RAG+SQL", "reason": "PolyRAG extension"},
    {"repo_url": "https://github.com/langchain-ai/rag-retrieval-api-template", "framework": "FastAPI+LangChain", "reason": "official RAG API template"},
    {"repo_url": "https://github.com/patchy631/ai-engineering-hub/tree/main/rag-agent", "framework": "FastAPI+RAG", "reason": "RAG agent hub"},
    {"repo_url": "https://github.com/steven2358/realtime-voice-chatbot", "framework": "FastAPI+Voice+RAG", "reason": "voice RAG chatbot"},
    {"repo_url": "https://github.com/Decentralised-AI/RAG-Chatbot-API", "framework": "FastAPI+RAG", "reason": "decentralised RAG API"},
    {"repo_url": "https://github.com/All-Hands-AI/OpenHands", "framework": "Agent+Code", "reason": "skip-heavy"},
    {"repo_url": "https://github.com/vercel/ai-chatbot", "framework": "Next.js", "reason": "skip-frontend"},
    {"repo_url": "https://github.com/NVIDIA/GenerativeAIExamples/tree/main/RAG", "framework": "NVIDIA+RAG", "reason": "nvidia RAG"},
    {"repo_url": "https://github.com/weaviate/Weaviate-Recipes/tree/main/integrations/llm-agent-frameworks/langchain", "framework": "Weaviate+RAG", "reason": "weaviate recipe"},
    {"repo_url": "https://github.com/hwchase17/langgraph-example", "framework": "LangGraph", "reason": "langgraph example"},
    {"repo_url": "https://github.com/langchain-ai/langgraph-example", "framework": "LangGraph", "reason": "langgraph official example"},
    {"repo_url": "https://github.com/langchain-ai/rag-chroma-template", "framework": "LangChain+Chroma", "reason": "chroma RAG template"},
    {"repo_url": "https://github.com/pinecone-io/examples/tree/master/learn/generation/langchain/handbook/08-langchain-retrieval-agent", "framework": "LangChain+Pinecone", "reason": "retrieval agent"},
]

GITHUB_SEARCH_QUERIES = [
    "rag fastapi chatbot language:python stars:>20",
    "langchain rag api language:python stars:>15",
    "langgraph agent fastapi language:python stars:>10",
    "pdf rag fastapi language:python stars:>5",
    "chroma rag chatbot language:python stars:>10",
    "faiss rag fastapi language:python stars:>5",
    "streamlit rag agent language:python stars:>10",
    "qdrant rag fastapi language:python stars:>5",
    "ollama rag fastapi language:python stars:>5",
    "corrective rag langgraph language:python stars:>3",
]

REPORT_CSV = RESULTS_DIR / "bulk_github_crawl_report.csv"


def _py_exe(vp: Path) -> Path:
    win = vp / "Scripts" / "python.exe"
    return win if win.is_file() else vp / "bin" / "python"


def _existing_urls(reg: Dict[str, Any]) -> Set[str]:
    return {a.get("repo_url", "").rstrip("/").lower() for a in reg.get("agents", [])}


def _is_blocked(url: str, repo_name: str) -> bool:
    low = (url + repo_name).lower()
    if any(b in low for b in FRAMEWORK_BLOCK):
        return True
    if "/tree/" in url:
        return True
    if low.endswith("/openhands") or "open-webui" in low or "/dify" in low:
        return True
    return False


def _github_search(query: str) -> List[Dict[str, str]]:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": 20}
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rag-poison-platform-crawler",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    out = []
    for item in data.get("items", []):
        name = item.get("full_name", "")
        if not name or "/" not in name:
            continue
        repo_url = item.get("html_url", f"https://github.com/{name}")
        desc = (item.get("description") or "")[:120]
        lang = item.get("language") or ""
        if lang and lang.lower() != "python":
            continue
        fw = "GitHubSearch+RAG"
        if "langgraph" in desc.lower():
            fw = "LangGraph+RAG"
        elif "fastapi" in desc.lower():
            fw = "FastAPI+RAG"
        elif "streamlit" in desc.lower():
            fw = "Streamlit+RAG"
        out.append({"repo_url": repo_url, "framework": fw, "reason": desc or "github search hit"})
    return out


def _discover_candidates(reg: Dict[str, Any]) -> List[Dict[str, str]]:
    seen = _existing_urls(reg)
    discovered: List[Dict[str, str]] = []
    for c in CRAWL_CANDIDATES:
        u = c["repo_url"].rstrip("/").lower()
        if u in seen or _is_blocked(c["repo_url"], c["repo_url"].split("/")[-1]):
            continue
        discovered.append(c)
        seen.add(u)
    for q in GITHUB_SEARCH_QUERIES:
        time.sleep(2.5)
        for c in _github_search(q):
            u = c["repo_url"].rstrip("/").lower()
            if u in seen or _is_blocked(c["repo_url"], c["repo_url"].split("/")[-1]):
                continue
            discovered.append(c)
            seen.add(u)
    return discovered


def _next_port(reg: Dict[str, Any]) -> int:
    ports = [int(a.get("assigned_port") or 0) for a in reg.get("agents", [])]
    return max(ports) + 1 if ports else 19201


def _make_entry(c: Dict[str, str], port: int) -> Dict[str, Any]:
    aid = repo_id_from_url(c["repo_url"])
    root = agent_root(aid)
    entry = dict(AGENT_TEMPLATE)
    entry.update(
        {
            "id": aid,
            "repo_url": c["repo_url"],
            "repo_name": c["repo_url"].rstrip("/").split("/")[-1],
            "framework": c["framework"],
            "local_path": str(root / "repo"),
            "venv_path": str(root / ".venv"),
            "candidate_reason": c.get("reason", "crawled"),
            "status": "candidate",
            "assigned_port": port,
            "sample_type": "external_github_agent",
            "deploy_commands": {
                "clone": f"git clone --depth 1 {c['repo_url']} {root / 'repo'}",
                "install": f"python -m venv {root / '.venv'} && pip install -r requirements.txt",
                "start": "uvicorn app:app --host 127.0.0.1 --port <port>",
            },
        }
    )
    return entry


def _unique_id(base: str, used: Set[str]) -> str:
    aid = base
    n = 1
    while aid in used:
        aid = f"{base}_{n}"
        n += 1
    used.add(aid)
    return aid


def _agent_repo(agent: Dict[str, Any]) -> Path:
    lp = agent.get("local_path", "")
    if lp:
        return Path(lp)
    return repo_path(agent["id"])


def _clone_agent(agent: Dict[str, Any]) -> Tuple[bool, str]:
    aid = agent["id"]
    url = agent["repo_url"]
    dest = _agent_repo(agent)
    agent_root(aid).mkdir(parents=True, exist_ok=True)
    if dest.is_dir() and any(dest.iterdir()):
        return True, "already_cloned"
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_out = ""
    for attempt in range(1, CLONE_RETRIES + 2):
        if dest.is_dir():
            shutil.rmtree(dest, ignore_errors=True)
        code, out = run_cmd(["git", "clone", "--depth", "1", url, str(dest)], timeout=300)
        last_out = out
        if code == 0 and dest.is_dir() and any(dest.iterdir()):
            return True, f"cloned_attempt_{attempt}"
        time.sleep(2)
    return False, last_out[-500:]


def _find_manifest(repo: Path) -> Tuple[str, Optional[Path]]:
    for name in ("requirements.txt", "backend/requirements.txt", "app/requirements.txt"):
        p = repo / name
        if p.is_file():
            return "requirements", p
    reqs = sorted(repo.rglob("requirements.txt"), key=lambda x: len(x.parts))
    if reqs:
        return "requirements", reqs[0]
    for name in ("pyproject.toml", "backend/pyproject.toml"):
        p = repo / name
        if p.is_file():
            return "pyproject", p
    pps = sorted(repo.rglob("pyproject.toml"), key=lambda x: len(x.parts))
    if pps:
        return "pyproject", pps[0]
    return "none", None


def _relax_requirements(src: Path, dst: Path) -> None:
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    relaxed = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            relaxed.append(line)
            continue
        s = re.sub(r"==[0-9][^\s;#]*", "", s)
        s = re.sub(r">=[0-9][^\s;#]*", "", s)
        s = re.sub(r"<=[0-9][^\s;#]*", "", s)
        relaxed.append(s)
    dst.write_text("\n".join(relaxed) + "\n", encoding="utf-8")


def _pip(py: str, args: List[str], repo: Path, logs: List[str], timeout: int = 180) -> Tuple[int, str]:
    code, out = run_cmd([py, "-m", "pip"] + args, cwd=repo, timeout=timeout)
    logs.append(f"pip {' '.join(args)} code={code}\n{out[-1500:]}")
    return code, out


def _install_agent(agent: Dict[str, Any]) -> Tuple[bool, str, str]:
    aid = agent["id"]
    repo = _agent_repo(agent)
    vp = Path(agent.get("venv_path")) if agent.get("venv_path") else venv_path(aid)
    logs: List[str] = [f"=== crawl install {aid} {now_iso()} ==="]
    manifest_type, manifest_path = _find_manifest(repo)
    if manifest_type == "none":
        return False, "no_manifest", "no requirements/pyproject"

    if not _py_exe(vp).is_file():
        code, out = run_cmd([sys.executable, "-m", "venv", str(vp)], timeout=VENV_TIMEOUT)
        logs.append(f"venv code={code}\n{out}")
        if code != 0:
            (agent_root(aid) / "install.log").write_text("\n".join(logs), encoding="utf-8")
            return False, "venv_failed", out[-400:]

    py = str(_py_exe(vp))
    _pip(py, ["install", "-q", "--upgrade", "pip", "setuptools", "wheel"], repo, logs, timeout=120)
    _pip(py, ["install", "-q", "numpy"], repo, logs, timeout=180)

    strategies: List[Tuple[str, List[str]]] = []
    if manifest_type == "requirements" and manifest_path:
        strategies.append(("strict", ["install", "-r", str(manifest_path)]))
        relaxed = agent_root(aid) / "requirements.relaxed.txt"
        _relax_requirements(manifest_path, relaxed)
        strategies.append(("relaxed", ["install", "-r", str(relaxed)]))
    elif manifest_type == "pyproject" and manifest_path:
        strategies.append(("editable", ["install", "-e", str(manifest_path.parent)]))

    strategies.append(("core_rag", ["install", "-q"] + CORE_RAG_PACKAGES))

    for label, pip_args in strategies:
        code, out = _pip(py, pip_args, repo, logs, timeout=INSTALL_TIMEOUT)
        if code == 0:
            write_agent_env_file(agent_root(aid), use_deepseek=True)
            (agent_root(aid) / "install.log").write_text("\n".join(logs), encoding="utf-8")
            return True, "", f"ok_via_{label}"
        time.sleep(1)

    (agent_root(aid) / "install.log").write_text("\n".join(logs), encoding="utf-8")
    return False, "pip_failed", out[-400:]


def _is_complete_agent(agent: Dict[str, Any], repo: Path) -> bool:
    feats = scan_repo_features(repo)
    if not (feats.get("has_fastapi") or feats.get("has_flask") or feats.get("requires_frontend")):
        py_main = list(repo.rglob("main.py")) + list(repo.rglob("app.py"))
        if not py_main:
            return False
    rag_markers = feats.get("has_langchain") or feats.get("has_langgraph") or feats.get("has_chroma") or feats.get("has_faiss") or feats.get("has_qdrant") or feats.get("has_llamaindex")
    if not rag_markers:
        combined = ""
        for p in list(repo.rglob("*.py"))[:80]:
            try:
                combined += p.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                pass
        rag_markers = any(x in combined for x in ("retriev", "vector", "embed", "chromadb", "faiss", "rag"))
    return bool(rag_markers)


def _count_install_success(reg: Dict[str, Any]) -> int:
    return sum(1 for a in reg.get("agents", []) if a.get("install_success"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=TARGET_DEFAULT)
    parser.add_argument("--max-new", type=int, default=80, help="max new candidates to try")
    args = parser.parse_args()

    BULK_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    used_ids = {a["id"] for a in reg.get("agents", [])}
    rows: List[Dict[str, Any]] = []

    print(f"[crawl] current install_success={_count_install_success(reg)} target={args.target}")

    candidates = _discover_candidates(reg)
    print(f"[crawl] discovered {len(candidates)} new candidate URLs")

    tried = 0
    for c in candidates:
        if _count_install_success(reg) >= args.target:
            break
        if tried >= args.max_new:
            break
        tried += 1

        reachable = False
        for attempt in range(3):
            if git_ls_remote(c["repo_url"]):
                reachable = True
                break
            time.sleep(3)
        if not reachable:
            rows.append({"repo_url": c["repo_url"], "status": "unreachable", "agent_id": "", "notes": "git ls-remote failed"})
            continue

        port = _next_port(reg)
        entry = _make_entry(c, port)
        entry["id"] = _unique_id(entry["id"], used_ids)
        reg.setdefault("agents", []).append(entry)
        aid = entry["id"]

        ok_clone, clone_note = _clone_agent(entry)
        entry["clone_success"] = ok_clone
        entry["status"] = "cloned" if ok_clone else "clone_failed"
        if not ok_clone:
            rows.append({"agent_id": aid, "repo_url": c["repo_url"], "status": "clone_failed", "notes": clone_note})
            save_registry(reg)
            continue

        repo = repo_path(aid)
        if not _is_complete_agent(entry, repo):
            entry["status"] = "skipped_not_complete_agent"
            rows.append({"agent_id": aid, "repo_url": c["repo_url"], "status": "skipped", "notes": "not a complete RAG agent"})
            save_registry(reg)
            continue

        feats = scan_repo_features(repo)
        entry.update(
            {
                "has_fastapi": feats.get("has_fastapi"),
                "has_flask": feats.get("has_flask"),
                "has_langchain": feats.get("has_langchain"),
                "has_langgraph": feats.get("has_langgraph"),
                "has_chroma": feats.get("has_chroma"),
                "has_faiss": feats.get("has_faiss"),
                "has_qdrant": feats.get("has_qdrant"),
                "has_llamaindex": feats.get("has_llamaindex"),
                "likely_endpoints": feats.get("likely_endpoints", {}),
                "has_requirements_txt": feats.get("has_requirements_txt"),
                "has_pyproject_toml": feats.get("has_pyproject_toml"),
            }
        )

        ok_install, err_type, note = _install_agent(entry)
        entry["install_attempted"] = True
        entry["install_success"] = ok_install
        entry["status"] = "installed" if ok_install else "install_failed"
        entry["error_type"] = err_type
        entry["tested_at"] = now_iso()
        if ok_install:
            apply_api_dependency_fields(entry, repo)
            write_agent_env_file(agent_root(aid), use_deepseek=True)

        rows.append(
            {
                "agent_id": aid,
                "repo_url": c["repo_url"],
                "framework": c["framework"],
                "status": entry["status"],
                "install_success": ok_install,
                "clone_success": ok_clone,
                "notes": note,
            }
        )
        save_registry(reg)
        print(f"[crawl] {aid} install_success={ok_install} total={_count_install_success(reg)}/{args.target}", flush=True)

    write_csv(
        REPORT_CSV,
        rows,
        fieldnames=["agent_id", "repo_url", "framework", "status", "install_success", "clone_success", "notes"],
    )
    final = _count_install_success(reg)
    print(f"[crawl] DONE install_success={final}/{args.target} report={REPORT_CSV}")


if __name__ == "__main__":
    main()
