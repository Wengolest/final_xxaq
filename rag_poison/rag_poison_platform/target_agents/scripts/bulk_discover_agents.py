"""
Level 0: Register 30+ GitHub Agent/RAG candidates into bulk_registry.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    AGENT_TEMPLATE,
    BULK_ROOT,
    RESULTS_DIR,
    REGISTRY_PATH,
    agent_root,
    git_ls_remote,
    load_registry,
    repo_id_from_url,
    save_registry,
    write_csv,
)

# Curated candidates: FastAPI/LangChain/LangGraph/RAG API projects (small-to-medium).
CANDIDATES: List[Dict[str, str]] = [
    {"repo_url": "https://github.com/naghost-dev/Fastapi-meets-Langgraph", "framework": "FastAPI+LangGraph", "reason": "LangGraph agent HTTP invoke"},
    {"repo_url": "https://github.com/iamtxena/simple-rag-chatbot", "framework": "FastAPI+Chroma", "reason": "simple RAG chatbot API"},
    {"repo_url": "https://github.com/anarojoecheburua/RAG-with-Langchain-and-FastAPI", "framework": "FastAPI+LangChain+FAISS", "reason": "LangChain RAG FastAPI"},
    {"repo_url": "https://github.com/shamspias/langgraph-agents", "framework": "LangGraph", "reason": "LangGraph multi-agent"},
    {"repo_url": "https://github.com/pixegami/langchain-rag-tutorial", "framework": "LangChain", "reason": "LangChain RAG tutorial"},
    {"repo_url": "https://github.com/mallahyari/rag-agent-fastapi", "framework": "FastAPI+RAG", "reason": "RAG agent FastAPI"},
    {"repo_url": "https://github.com/alphasecio/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "LangChain RAG API"},
    {"repo_url": "https://github.com/ranfysz/langchain-fastapi-rag", "framework": "FastAPI+LangChain", "reason": "document QA API"},
    {"repo_url": "https://github.com/sandeep-23/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "RAG FastAPI example"},
    {"repo_url": "https://github.com/UETA-Takahiro/langchain-rag-fastapi", "framework": "FastAPI+LangChain", "reason": "JP RAG FastAPI"},
    {"repo_url": "https://github.com/ObSchwartz/fastapi-langchain-rag", "framework": "FastAPI+LangChain", "reason": "LangChain RAG server"},
    {"repo_url": "https://github.com/paveldedik/langchain-rag-api", "framework": "FastAPI+LangChain", "reason": "RAG REST API"},
    {"repo_url": "https://github.com/eyucoder/faq-chatbot-rag", "framework": "FastAPI+RAG", "reason": "FAQ RAG chatbot"},
    {"repo_url": "https://github.com/Jaimboh/PDF-ChatBot-FastAPI", "framework": "FastAPI+PDF RAG", "reason": "PDF chatbot API"},
    {"repo_url": "https://github.com/antoniolanza1996/rag-fastapi-langchain", "framework": "FastAPI+LangChain", "reason": "RAG LangChain API"},
    {"repo_url": "https://github.com/JeongJuhan/RAG_chatbot", "framework": "FastAPI+RAG", "reason": "RAG chatbot"},
    {"repo_url": "https://github.com/araweeli/fastapi-ollama-rag", "framework": "FastAPI+Ollama", "reason": "Ollama RAG API"},
    {"repo_url": "https://github.com/santorodeng/llama-rag-fastapi", "framework": "FastAPI+Llama", "reason": "Llama RAG API"},
    {"repo_url": "https://github.com/tjmlabs/fastapi-rag-template", "framework": "FastAPI+RAG", "reason": "RAG template"},
    {"repo_url": "https://github.com/koenvandenberge/fastapi-rag-example", "framework": "FastAPI+RAG", "reason": "minimal RAG example"},
    {"repo_url": "https://github.com/Shauryasharma45/simple-rag-chatbot-fastapi", "framework": "FastAPI+RAG", "reason": "simple RAG API"},
    {"repo_url": "https://github.com/jermwang/fastapi-llm-app", "framework": "FastAPI+LLM", "reason": "LLM FastAPI app"},
    {"repo_url": "https://github.com/langchain-ai/langserve", "framework": "LangServe", "reason": "LangServe RAG server"},
    {"repo_url": "https://github.com/run-llama/llama_index", "framework": "LlamaIndex", "reason": "LlamaIndex core (inspect only)"},
    {"repo_url": "https://github.com/chroma-core/chroma", "framework": "Chroma", "reason": "vector DB with API"},
    {"repo_url": "https://github.com/ttran9/crag-rag-agent", "framework": "LangChain RAG", "reason": "CRAG agent"},
    {"repo_url": "https://github.com/zahiry/franken-rag", "framework": "RAG", "reason": "Franken RAG"},
    {"repo_url": "https://github.com/SKNETWORKS-FAMILY-AICAMP/RAG-QnA-Langchain", "framework": "LangChain RAG", "reason": "RAG QnA"},
    {"repo_url": "https://github.com/EthanCaddle/fastapi-rag", "framework": "FastAPI+RAG", "reason": "FastAPI RAG"},
    {"repo_url": "https://github.com/shauryasharma45/rag-fastapi", "framework": "FastAPI+RAG", "reason": "RAG FastAPI"},
    {"repo_url": "https://github.com/broadfield-ai/rag-chatbot-api", "framework": "FastAPI+RAG", "reason": "RAG chatbot API"},
    {"repo_url": "https://github.com/part-ai/fastapi-chatbot", "framework": "FastAPI", "reason": "FastAPI chatbot"},
    {"repo_url": "https://github.com/assafelovic/gpt-researcher", "framework": "Research Agent", "reason": "research agent (heavy)"},
    {"repo_url": "https://github.com/microsoft/sample-app-aoai-chatGPT", "framework": "Azure+FastAPI", "reason": "Azure chat RAG sample"},
    {"repo_url": "https://github.com/langchain-ai/chat-langchain", "framework": "LangChain", "reason": "chat-langchain"},
    {"repo_url": "https://github.com/hwchase17/langchain", "framework": "LangChain", "reason": "langchain monorepo (heavy)"},
    {"repo_url": "https://github.com/langgenius/dify", "framework": "Dify", "reason": "platform (too heavy, register only)"},
    {"repo_url": "https://github.com/open-webui/open-webui", "framework": "OpenWebUI", "reason": "platform (too heavy, register only)"},
]


def build_agent_entry(c: Dict[str, str], idx: int) -> Dict[str, Any]:
    base_id = repo_id_from_url(c["repo_url"])
    agent_id = base_id
    if idx > 0:
        agent_id = f"{base_id}_{idx}"
    root = agent_root(agent_id)
    entry = dict(AGENT_TEMPLATE)
    entry.update(
        {
            "id": agent_id,
            "repo_url": c["repo_url"],
            "repo_name": c["repo_url"].rstrip("/").split("/")[-1],
            "framework": c["framework"],
            "local_path": str(root / "repo"),
            "venv_path": str(root / ".venv"),
            "candidate_reason": c["reason"],
            "status": "candidate",
            "assigned_port": 19001 + idx,
            "deploy_commands": {
                "clone": f"git clone {c['repo_url']} {root / 'repo'}",
                "install": f"python -m venv {root / '.venv'} && pip install -r requirements.txt",
                "start": "uvicorn app:app --host 127.0.0.1 --port <port>",
            },
        }
    )
    return entry


def main() -> None:
    BULK_ROOT.mkdir(parents=True, exist_ok=True)
    seen_ids: set[str] = set()
    agents: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []

    for i, c in enumerate(CANDIDATES):
        aid = repo_id_from_url(c["repo_url"])
        suffix = 0
        while aid in seen_ids:
            suffix += 1
            aid = f"{repo_id_from_url(c['repo_url'])}_{suffix}"
        seen_ids.add(aid)
        entry = build_agent_entry(c, i)
        entry["id"] = aid
        entry["assigned_port"] = 19001 + i
        reachable = git_ls_remote(c["repo_url"])
        entry["notes"] = "repo_reachable" if reachable else "repo_unreachable_at_discover"
        agents.append(entry)
        rows.append(
            {
                "agent_id": aid,
                "repo_url": c["repo_url"],
                "framework_guess": c["framework"],
                "reason": c["reason"],
                "status": "candidate",
                "repo_reachable": reachable,
            }
        )

    save_registry({"agents": agents})
    out = RESULTS_DIR / "bulk_agent_candidates.csv"
    write_csv(out, rows)
    print(f"Registered {len(agents)} candidates -> {REGISTRY_PATH}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
