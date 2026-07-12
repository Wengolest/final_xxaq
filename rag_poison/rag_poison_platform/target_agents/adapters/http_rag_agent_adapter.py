"""HTTP client for minimal_http_rag_agent service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import urllib.error
import urllib.request


class HttpRAGAgentAdapter:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18100",
        timeout_sec: int = 180,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
                return {
                    "ok": True,
                    "status_code": resp.getcode(),
                    "data": json.loads(body) if body else {},
                    "error": "",
                }
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "status_code": exc.code,
                "data": {},
                "error": err[:2000],
            }
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def reset(self) -> Dict[str, Any]:
        return self._request("POST", "/reset", {})

    def ingest(
        self,
        doc_id: str,
        text: str,
        source: str = "clean",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/ingest",
            {
                "doc_id": doc_id,
                "text": text,
                "source": source,
                "metadata": metadata or {},
            },
        )

    def ingest_documents(self, docs: List[Dict[str, Any]], source: str) -> None:
        for doc in docs:
            result = self.ingest(
                doc_id=doc.get("doc_id", "unknown"),
                text=doc.get("content") or doc.get("text", ""),
                source=source,
                metadata=doc.get("metadata", {}),
            )
            if not result["ok"]:
                raise RuntimeError(
                    f"ingest failed for {doc.get('doc_id')}: {result['error']}"
                )

    @staticmethod
    def _format_retrieved(retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
        poison_retrieved = False
        poison_rank = None
        poison_original_score = None
        poison_manipulated_score = None
        manipulation_reason = ""

        sources: List[str] = []
        scores: List[str] = []
        metadata_chunks: List[str] = []

        for item in retrieved:
            if item.get("source") == "poison" and not poison_retrieved:
                poison_retrieved = True
                poison_rank = item.get("rank")
                poison_original_score = item.get("original_score", item.get("score"))
                poison_manipulated_score = item.get("manipulated_score", item.get("score"))
                manipulation_reason = item.get("manipulation_reason", "")

            preview = (item.get("text") or "").replace("\n", " ")[:120]
            meta = item.get("metadata") or {}
            meta_brief = ",".join(f"{k}={meta[k]}" for k in sorted(meta)[:6])
            sources.append(
                f"#{item.get('rank')}|source={item.get('source')}|id={item.get('doc_id')}|{preview}"
            )
            scores.append(
                f"rank={item.get('rank')}:orig={item.get('original_score', item.get('score', 0)):.4f}"
                f":manip={item.get('manipulated_score', item.get('score', 0)):.4f}"
            )
            if meta_brief:
                metadata_chunks.append(f"rank={item.get('rank')}|{meta_brief}")

        return {
            "poison_retrieved": poison_retrieved,
            "poison_rank": poison_rank,
            "poison_original_score": poison_original_score,
            "poison_manipulated_score": poison_manipulated_score,
            "manipulation_reason": manipulation_reason,
            "retrieved_sources": " || ".join(sources),
            "retrieved_scores": "; ".join(scores),
            "retrieved_metadata": " || ".join(metadata_chunks),
        }

    def query(
        self,
        question: str,
        top_k: int = 5,
        retriever_profile: str = "tfidf_top5",
        metadata_filter: Optional[Dict[str, Any]] = None,
        allow_fallback: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "question": question,
            "top_k": top_k,
            "retriever_profile": retriever_profile,
            "allow_fallback": allow_fallback,
        }
        if metadata_filter:
            payload["metadata_filter"] = metadata_filter

        raw = self._request("POST", "/query", payload)
        if not raw["ok"]:
            return {
                "ok": False,
                "answer": "",
                "retrieved_docs": [],
                "retriever_profile": retriever_profile,
                "metadata_filter": metadata_filter or {},
                "fallback_used": False,
                "poison_retrieved": False,
                "poison_rank": None,
                "poison_original_score": None,
                "poison_manipulated_score": None,
                "manipulation_reason": "",
                "retrieved_sources": "",
                "retrieved_scores": "",
                "retrieved_metadata": "",
                "error": raw["error"],
                "status_code": raw["status_code"],
            }

        data = raw["data"]
        retrieved = data.get("retrieved_docs", [])
        formatted = self._format_retrieved(retrieved)

        return {
            "ok": True,
            "answer": data.get("answer", ""),
            "retrieved_docs": retrieved,
            "retriever_profile": data.get("retriever_profile", retriever_profile),
            "metadata_filter": data.get("metadata_filter", metadata_filter or {}),
            "fallback_used": data.get("fallback_used", False),
            "error": "",
            "status_code": raw["status_code"],
            **formatted,
        }

    def build_corpus(
        self,
        clean_docs: List[Dict[str, Any]],
        poison_docs: List[Dict[str, Any]],
        corpus_mode: str,
    ) -> None:
        reset_result = self.reset()
        if not reset_result["ok"]:
            raise RuntimeError(f"reset failed: {reset_result['error']}")

        self.ingest_documents(clean_docs, source="clean")
        if corpus_mode in {"mixed", "poison_only"} and poison_docs:
            self.ingest_documents(poison_docs, source="poison")
