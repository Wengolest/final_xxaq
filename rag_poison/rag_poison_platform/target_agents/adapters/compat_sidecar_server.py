"""Compat sidecar: unified /health /reset /ingest /query for external agents."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import urllib.error
import urllib.request
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_PATH.is_file():
    load_dotenv(_ENV_PATH)

app = FastAPI(title="compat_sidecar", version="0.1.0")

_documents: List[Dict[str, Any]] = []
_vectorizer: Optional[TfidfVectorizer] = None
_matrix = None
_NATIVE_BASE = os.environ.get("COMPAT_NATIVE_BASE_URL", "").rstrip("/")
_NATIVE_ENDPOINT = os.environ.get("COMPAT_NATIVE_QUERY_ENDPOINT", "/agents/invoke")


class IngestRequest(BaseModel):
    doc_id: str
    text: str
    source: Literal["clean", "poison"] = "clean"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


def _rebuild_index() -> None:
    global _vectorizer, _matrix
    texts = [d["text"] for d in _documents]
    if not texts:
        _vectorizer, _matrix = None, None
        return
    _vectorizer = TfidfVectorizer(max_features=8000)
    _matrix = _vectorizer.fit_transform(texts)


def _retrieve(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if not _documents or _vectorizer is None or _matrix is None:
        return []
    qv = _vectorizer.transform([question])
    scores = linear_kernel(qv, _matrix).flatten()
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    out: List[Dict[str, Any]] = []
    for rank, (idx, score) in enumerate(ranked, 1):
        doc = _documents[idx]
        out.append(
            {
                "rank": rank,
                "score": float(score),
                "doc_id": doc["doc_id"],
                "source": doc["source"],
                "text": doc["text"][:500],
            }
        )
    return out


def _mock_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    ctx = "\n".join(f"[{c['source']}] {c['text'][:200]}" for c in chunks[:3])
    return f"Based on retrieved context:\n{ctx}\n\nAnswer: {question}"


def _call_native(question: str, context: str) -> tuple[bool, str]:
    if not _NATIVE_BASE:
        return False, ""
    payload = {"input": f"Context:\n{context}\n\nQuestion: {question}"}
    data = __import__("json").dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_NATIVE_BASE}{_NATIVE_ENDPOINT}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = __import__("json").loads(body)
            except Exception:
                return True, body
            for k in ("output", "answer", "response", "result"):
                if k in parsed:
                    return True, str(parsed[k])
            return True, body[:2000]
    except Exception as exc:
        return False, str(exc)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "adapter_mode": "sidecar",
        "native_base": _NATIVE_BASE or None,
        "doc_count": len(_documents),
    }


@app.post("/reset")
def reset() -> Dict[str, Any]:
    global _documents, _vectorizer, _matrix
    _documents = []
    _vectorizer, _matrix = None, None
    return {"ok": True}


@app.post("/ingest")
def ingest(req: IngestRequest) -> Dict[str, Any]:
    _documents.append(
        {
            "doc_id": req.doc_id,
            "text": req.text,
            "source": req.source,
            "metadata": req.metadata,
        }
    )
    _rebuild_index()
    return {"ok": True, "doc_count": len(_documents)}


@app.post("/query")
def query(req: QueryRequest) -> Dict[str, Any]:
    chunks = _retrieve(req.question, req.top_k)
    context = "\n".join(c["text"] for c in chunks)
    native_ok, native_answer = _call_native(req.question, context)
    if native_ok and native_answer:
        answer = native_answer
        native_used = True
        deepseek_used = False
    else:
        answer = _mock_answer(req.question, chunks)
        native_used = False
        deepseek_used = False
    poison_retrieved = any(c["source"] == "poison" for c in chunks)
    poison_rank = next((c["rank"] for c in chunks if c["source"] == "poison"), None)
    return {
        "answer": answer,
        "sources": chunks,
        "poison_retrieved": poison_retrieved,
        "poison_rank": poison_rank,
        "adapter_mode": "hybrid" if native_used else "sidecar",
        "native_agent_used": native_used,
        "sidecar_used": True,
        "deepseek_used": deepseek_used,
    }
