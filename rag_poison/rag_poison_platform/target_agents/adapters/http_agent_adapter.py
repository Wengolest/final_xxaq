"""Unified HTTP client for external target agents (outside platform venv)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import urllib.error
import urllib.request


class HttpAgentAdapter:
    """
    Minimal HTTP adapter for FastAPI / LangGraph style target agents.

    request_format presets:
      - question: {"question": "..."}
      - query: {"query": "..."}
      - message: {"message": "..."}
      - messages: {"messages": [{"role": "user", "content": "..."}]}
      - chat_messages_thread: {"messages": [...], "thread_id": "smoke"}
      - invoke_input: {"input": "..."}
      - custom: pass dict via query() metadata override
    """

    PRESETS: Dict[str, Dict[str, Any]] = {
        "question": lambda q, ctx, meta: {"question": q},
        "query": lambda q, ctx, meta: {"query": q},
        "message": lambda q, ctx, meta: {"message": q},
        "messages": lambda q, ctx, meta: {
            "messages": [{"role": "user", "content": q}]
        },
        "chat_messages_thread": lambda q, ctx, meta: {
            "messages": [q] if isinstance(q, str) else q,
            "thread_id": (meta or {}).get("thread_id", "smoke_test"),
        },
        "invoke_input": lambda q, ctx, meta: {"input": q},
        "input": lambda q, ctx, meta: {"input": q},
        "text": lambda q, ctx, meta: {"text": q},
    }

    def __init__(
        self,
        base_url: str,
        chat_endpoint: str,
        *,
        method: str = "POST",
        request_format: str = "question",
        query_param_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_sec: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.chat_endpoint = chat_endpoint if chat_endpoint.startswith("/") else f"/{chat_endpoint}"
        self.method = method.upper()
        self.request_format = request_format
        self.query_param_name = query_param_name
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.timeout_sec = timeout_sec

    def build_payload(
        self,
        question: str,
        context: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = metadata or {}
        if self.request_format == "custom" and "payload" in meta:
            payload = dict(meta["payload"])
            payload.setdefault("question", question)
            return payload
        builder = self.PRESETS.get(self.request_format)
        if not builder:
            raise ValueError(f"Unknown request_format: {self.request_format}")
        payload = builder(question, context, meta)
        if context is not None and isinstance(payload, dict):
            payload.setdefault("context", context)
        return payload

    def _extract_answer(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if not isinstance(data, dict):
            return str(data)

        for key in (
            "answer",
            "response",
            "output",
            "result",
            "content",
            "text",
            "message",
            "email",
        ):
            if key in data and data[key] is not None:
                val = data[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    return self._extract_answer(val)

        if "messages" in data and isinstance(data["messages"], list) and data["messages"]:
            last = data["messages"][-1]
            if isinstance(last, dict):
                return str(last.get("content", last))
            return str(last)

        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            if isinstance(choice, dict):
                msg = choice.get("message", choice)
                if isinstance(msg, dict):
                    return str(msg.get("content", msg))
                return str(msg)

        if "response" in data:
            blob = json.dumps(data["response"], ensure_ascii=False)
            for marker in ('"content": "', '"content":"'):
                if marker in blob:
                    start = blob.index(marker) + len(marker)
                    end = blob.find('"', start)
                    if end > start:
                        return blob[start:end]
            return blob[:4000]

        return json.dumps(data, ensure_ascii=False)[:4000]

    def query(
        self,
        question: str,
        context: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{self.chat_endpoint}"
        payload: Optional[Dict[str, Any]] = None
        body: Optional[bytes] = None

        if self.query_param_name:
            qs = urlencode({self.query_param_name: question})
            url = f"{url}?{qs}"
        else:
            payload = self.build_payload(question, context, metadata)
            body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body if self.method == "POST" and body is not None else None,
            headers=self.headers,
            method=self.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                status = resp.getcode()
                raw_text = resp.read().decode("utf-8", errors="replace")
                try:
                    raw = json.loads(raw_text)
                except json.JSONDecodeError:
                    raw = raw_text
                answer = self._extract_answer(raw)
                return {
                    "ok": 200 <= status < 300,
                    "status_code": status,
                    "answer": answer,
                    "raw": raw,
                    "error": "",
                }
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "status_code": exc.code,
                "answer": "",
                "raw": err_body,
                "error": f"HTTPError: {exc.code} {err_body[:500]}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 0,
                "answer": "",
                "raw": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def probe_url(self, path: str, method: str = "GET") -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {
                    "ok": True,
                    "status_code": resp.getcode(),
                    "path": path,
                    "error": "",
                }
        except urllib.error.HTTPError as exc:
            return {
                "ok": exc.code < 500,
                "status_code": exc.code,
                "path": path,
                "error": str(exc),
            }
        except Exception as exc:
            return {"ok": False, "status_code": 0, "path": path, "error": str(exc)}
