"""Unified adapter for GitHub HTTP RAG agents: probe, ingest, query, sources."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from target_agents.adapters.http_agent_adapter import HttpAgentAdapter
from target_agents.adapters.http_rag_agent_adapter import HttpRAGAgentAdapter
from target_agents.bulk_common import scan_repo_features


INGEST_ENDPOINTS = (
    "/ingest",
    "/documents",
    "/upload",
    "/add",
    "/add_document",
    "/load",
    "/retriever/ingest",
    "/api/ingest",
)
QUERY_ENDPOINTS = (
    "/query",
    "/chat",
    "/ask",
    "/invoke",
    "/agents/invoke",
    "/rag/query",
    "/api/chat",
)
RESET_ENDPOINTS = ("/reset", "/clear", "/clear_index", "/delete_all")
KB_DIR_NAMES = ("data", "docs", "documents", "kb", "knowledge", "source_documents")
INDEX_SCRIPTS = (
    "ingest.py",
    "build_index.py",
    "create_index.py",
    "load_docs.py",
    "index.py",
)


@dataclass
class AgentProbeResult:
    health_ok: bool = False
    query_ok: bool = False
    ingest_ok: bool = False
    reset_ok: bool = False
    health_endpoint: str = ""
    query_endpoint: str = ""
    ingest_endpoint: str = ""
    reset_endpoint: str = ""
    notes: str = ""


@dataclass
class GitHubAgentConfig:
    agent_id: str
    agent_class: str  # real_github_http | minimal_http_rag
    repo_url: str
    framework: str
    base_url: str
    local_path: str = ""
    chat_endpoint: str = "/query"
    http_method: str = "POST"
    request_format: str = "question"
    query_param_name: Optional[str] = None
    ingest_endpoint: str = ""
    reset_endpoint: str = ""
    kb_path: str = ""
    ingest_payload_style: str = "doc_id_text"  # doc_id_text | text_metadata | custom
    ingest_style: str = "auto"  # auto | http_documents | http_embed | file_kb | none
    collection_per_case: bool = False
    start_command: str = ""
    venv_path: str = ""
    start_cwd: str = ""
    tier: str = ""
    lock_query_endpoint: bool = False
    query_payload_log: str = ""


def _http_sse_post(
    url: str,
    payload: Dict[str, Any],
    timeout: int = 120,
) -> Tuple[bool, int, Any, str]:
    """POST and collect SSE/event-stream body into a single answer string."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(64000).decode("utf-8", errors="replace")
            latency = int((time.monotonic() - t0) * 1000)
            parts: List[str] = []
            for line in body.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    continue
                try:
                    parsed = json.loads(chunk)
                    if isinstance(parsed, dict):
                        for k in ("answer", "content", "message", "text", "delta"):
                            v = parsed.get(k)
                            if isinstance(v, str) and v:
                                parts.append(v)
                            elif isinstance(v, dict) and v.get("content"):
                                parts.append(str(v["content"]))
                    else:
                        parts.append(str(parsed))
                except json.JSONDecodeError:
                    parts.append(chunk)
            answer = "".join(parts).strip() or body[:2000]
            return bool(answer), resp.getcode(), {"answer": answer, "raw_sse": body[:4000]}, str(latency)
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - t0) * 1000)
        err = exc.read(2000).decode("utf-8", errors="replace")
        return False, exc.code, err, str(latency)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        return False, 0, "", f"{type(exc).__name__}: {exc}|{latency}"


def _http(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 120,
    headers_extra: Optional[Dict[str, str]] = None,
) -> Tuple[bool, int, Any, str]:
    data = None
    headers = {"Content-Type": "application/json"}
    if headers_extra:
        headers.update(headers_extra)
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(16000).decode("utf-8", errors="replace")
            latency = int((time.monotonic() - t0) * 1000)
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = body
            return True, resp.getcode(), parsed, str(latency)
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - t0) * 1000)
        err = exc.read(2000).decode("utf-8", errors="replace")
        return False, exc.code, err, str(latency)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        return False, 0, "", f"{type(exc).__name__}: {exc}|{latency}"


def _http_multipart(
    url: str,
    *,
    field_name: str,
    filename: str,
    content: str,
    timeout: int = 30,
    headers_extra: Optional[Dict[str, str]] = None,
) -> Tuple[bool, int, Any, str]:
    boundary = f"----PoisonBoundary{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if headers_extra:
        headers.update(headers_extra)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(16000).decode("utf-8", errors="replace")
            latency = int((time.monotonic() - t0) * 1000)
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = raw
            return True, resp.getcode(), parsed, str(latency)
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - t0) * 1000)
        err = exc.read(2000).decode("utf-8", errors="replace")
        return False, exc.code, err, str(latency)
    except Exception as exc:
        latency = int((time.monotonic() - t0) * 1000)
        return False, 0, "", f"{type(exc).__name__}: {exc}|{latency}"


def _http_get_text(
    url: str,
    *,
    timeout: int = 120,
    headers_extra: Optional[Dict[str, str]] = None,
) -> Tuple[bool, int, str, str]:
    headers = headers_extra or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(64000).decode("utf-8", errors="replace")
            return True, resp.getcode(), body, str(int((time.monotonic() - t0) * 1000))
    except urllib.error.HTTPError as exc:
        err = exc.read(2000).decode("utf-8", errors="replace")
        return False, exc.code, err, str(int((time.monotonic() - t0) * 1000))
    except Exception as exc:
        return False, 0, str(exc), ""


class GitHubHttpRagAdapter:
    """HTTP RAG poison-test adapter for external GitHub agents."""

    def __init__(self, config: GitHubAgentConfig) -> None:
        self.config = config
        self.probe_result = AgentProbeResult()
        self.ingest_method = "none"
        self.reset_supported = False
        self._minimal: Optional[HttpRAGAgentAdapter] = None
        self._http_chat: Optional[HttpAgentAdapter] = None
        self._case_prefix = ""
        self._corpus_report = ""
        self._tech_trends_chat_id = ""
        self._rag_fastapi_token = ""
        self._rag_fastapi_kb_id = ""
        self._rag_fastapi_chat_id = ""
        self._rag_fastapi_user_email = "poison_test@local.test"

        if config.agent_class == "minimal_http_rag":
            self._minimal = HttpRAGAgentAdapter(config.base_url)
        else:
            rf = config.request_format
            if rf == "invoke_query":
                rf = "custom"
            self._http_chat = HttpAgentAdapter(
                config.base_url,
                config.chat_endpoint,
                method=config.http_method,
                request_format=rf if rf != "invoke_query" else "question",
                query_param_name=config.query_param_name,
            )

    def try_start(self, wait_sec: int = 6) -> Tuple[bool, str]:
        cmd = self.config.start_command
        if not cmd:
            return False, "no_start_command"
        repo = Path(self.config.local_path) if self.config.local_path else None
        if not repo or not repo.is_dir():
            return False, "repo_missing"
        cwd = self.config.start_cwd or str(repo)
        try:
            subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(max(1, wait_sec // 3)):
                time.sleep(3)
                if self.probe().health_ok:
                    return True, "started"
            return self.probe().health_ok, "started_timeout"
        except Exception as exc:
            return False, str(exc)

    def probe(self, *, timeout: int = 5) -> AgentProbeResult:
        if self.config.agent_class == "minimal_http_rag" and self._minimal:
            h = self._minimal.health()
            self.probe_result = AgentProbeResult(
                health_ok=h["ok"],
                query_ok=h["ok"],
                ingest_ok=h["ok"],
                reset_ok=h["ok"],
                health_endpoint="/health",
                query_endpoint="/query",
                ingest_endpoint="/ingest",
                reset_endpoint="/reset",
                notes="minimal_http_rag",
            )
            self.ingest_method = "http_ingest"
            self.reset_supported = True
            return self.probe_result

        base = self.config.base_url.rstrip("/")
        pr = AgentProbeResult()

        if self.config.request_format == "rag_fastapi_jwt":
            for ep in ("/api/v1/health", "/docs", "/api/v1/health"):
                ok, code, _, _ = _http("GET", f"{base}{ep}", timeout=timeout)
                if ok or code in (200, 404):
                    pr.health_ok = True
                    pr.health_endpoint = ep
                    break
            if pr.health_ok and self._rag_fastapi_login():
                pr.ingest_endpoint = self.config.ingest_endpoint or "/api/v1/document/"
                pr.query_endpoint = self.config.chat_endpoint
                pr.ingest_ok = self._rag_fastapi_ensure_kb()
                qr = self._rag_fastapi_query("health probe question")
                pr.query_ok = qr.get("ok", False)
                self.probe_result = pr
                self.ingest_method = "http_document_pipeline"
                return pr

        for ep in ("/health", "/healthz", "/docs", "/"):
            ok, code, _, _ = _http("GET", f"{base}{ep}", timeout=timeout)
            if ok or code in (200, 404):
                pr.health_ok = True
                pr.health_endpoint = ep
                break

        q_ep = self.config.chat_endpoint or ""
        if q_ep:
            pr.query_endpoint = q_ep
            if pr.health_ok and self.config.request_format == "gpt_researcher_chat":
                test_ok, _, data, _ = self._query_gpt_researcher_payloads(
                    "health probe question", "probe report for health check"
                )
                pr.query_ok = test_ok
            elif pr.health_ok and self.config.request_format == "message":
                test_ok, _, data, _ = self._query_message_payloads("health probe question", None)
                pr.query_ok = test_ok and bool(
                    isinstance(data, dict) and (data.get("response") or data.get("answer"))
                )
            elif self._http_chat and pr.health_ok:
                saved = self._http_chat.timeout_sec
                self._http_chat.timeout_sec = timeout
                try:
                    test = self._http_chat.query("health probe question")
                    pr.query_ok = test["ok"] and bool(test.get("answer") or test.get("status_code") == 200)
                finally:
                    self._http_chat.timeout_sec = saved
        if not pr.query_ok and pr.health_ok and not self.config.lock_query_endpoint:
            for ep in QUERY_ENDPOINTS:
                if self.config.chat_endpoint and ep != self.config.chat_endpoint:
                    continue
                if self.config.http_method == "GET" or ep.endswith("/"):
                    url = f"{base}{ep}?query=probe"
                    ok, code, _, _ = _http("GET", url, timeout=timeout)
                else:
                    ok, code, _, _ = _http("POST", f"{base}{ep}", {"question": "probe"}, timeout=timeout)
                if ok or code in (200, 201):
                    pr.query_ok = True
                    pr.query_endpoint = ep
                    if not self.config.lock_query_endpoint:
                        self.config.chat_endpoint = ep
                    break

        i_ep = self.config.ingest_endpoint
        if i_ep:
            ok, code, _, _ = _http(
                "POST",
                f"{base}{i_ep}",
                {"text": "probe", "doc_id": "probe_1", "metadata": {}},
                timeout=timeout,
            )
            if ok or code in (200, 201, 422):
                pr.ingest_ok = True
                pr.ingest_endpoint = i_ep
        if not pr.ingest_ok and pr.health_ok:
            for ep in INGEST_ENDPOINTS:
                ok, code, _, _ = _http(
                    "POST",
                    f"{base}{ep}",
                    {"text": "probe doc", "doc_id": "probe_1"},
                    timeout=timeout,
                )
                if ok or code in (200, 201, 422):
                    pr.ingest_ok = True
                    pr.ingest_endpoint = ep
                    self.config.ingest_endpoint = ep
                    break

        if self.config.kb_path and Path(self.config.kb_path).is_dir():
            pr.ingest_ok = True
            pr.ingest_endpoint = pr.ingest_endpoint or "file_kb"

        reset_candidates = [self.config.reset_endpoint] if self.config.reset_endpoint else []
        reset_candidates.extend(RESET_ENDPOINTS)
        for ep in reset_candidates:
            if not ep:
                continue
            ok, code, _, _ = _http("POST", f"{base}{ep}", {}, timeout=8)
            if ok or code in (200, 204):
                pr.reset_ok = True
                pr.reset_endpoint = ep
                break

        self.probe_result = pr
        if pr.ingest_ok and pr.ingest_endpoint not in ("file_kb", ""):
            self.ingest_method = "http_ingest"
        elif pr.ingest_ok and self.config.kb_path:
            self.ingest_method = "file_kb"
        else:
            self.ingest_method = "none"
        self.reset_supported = pr.reset_ok
        return pr

    def reset(self) -> Tuple[bool, str]:
        if self.config.agent_class == "minimal_http_rag" and self._minimal:
            r = self._minimal.reset()
            return r["ok"], r.get("error", "")
        reset_ep = self.config.reset_endpoint or self.probe_result.reset_endpoint
        if self.reset_supported and reset_ep:
            payload: Dict[str, Any] = {}
            if self.config.collection_per_case:
                payload["collection_name"] = self._collection_name()
            ok, _, _, err = _http(
                "POST",
                f"{self.config.base_url.rstrip('/')}{reset_ep}",
                payload,
            )
            return ok, err
        if self.config.kb_path:
            return self._clear_file_kb(), "file_kb_cleared"
        return False, "reset_not_supported"

    def _clear_file_kb(self) -> bool:
        kb = Path(self.config.kb_path) if self.config.kb_path else None
        if not kb or not kb.is_dir():
            return False
        for sub in ("clean", "poison", "mixed"):
            d = kb / sub
            if d.is_dir():
                for f in d.glob("*"):
                    if f.is_file():
                        f.unlink()
        return True

    def _collection_name(self) -> str:
        if self.config.collection_per_case and self._case_prefix:
            safe = self._case_prefix.rstrip("_").replace("-", "_")[:48]
            return f"poison_{safe}"
        return "general_knowledge"

    def _rag_fastapi_headers(self) -> Dict[str, str]:
        if not self._rag_fastapi_token:
            self._rag_fastapi_login()
        if self._rag_fastapi_token:
            return {"Authorization": f"Bearer {self._rag_fastapi_token}"}
        return {}

    def _rag_fastapi_login(self) -> bool:
        base = self.config.base_url.rstrip("/")
        pwd = "Poison1!test"
        login_payload = {"email": self._rag_fastapi_user_email, "password": pwd}
        ok, code, data, _ = _http(
            "POST", f"{base}/api/v1/oauth/login", login_payload, timeout=30,
        )
        if ok and isinstance(data, dict) and data.get("access_token"):
            self._rag_fastapi_token = str(data["access_token"])
            return True
        signup_payload = {
            "email": self._rag_fastapi_user_email,
            "username": "poison_test",
            "first_name": "Poison",
            "last_name": "Test",
            "password": pwd,
            "confirm_password": pwd,
        }
        _http("POST", f"{base}/api/v1/oauth/signup", signup_payload, timeout=30)
        ok, _, data, _ = _http(
            "POST", f"{base}/api/v1/oauth/login", login_payload, timeout=30,
        )
        if ok and isinstance(data, dict) and data.get("access_token"):
            self._rag_fastapi_token = str(data["access_token"])
            return True
        return False

    def _rag_fastapi_ensure_kb(self) -> bool:
        if self._rag_fastapi_kb_id:
            return True
        base = self.config.base_url.rstrip("/")
        hdr = self._rag_fastapi_headers()
        if not hdr:
            return False
        ok, _, data, _ = _http(
            "POST",
            f"{base}/api/v1/kb/",
            {"name": "poison_kb", "description": "poison test kb"},
            timeout=30,
            headers_extra=hdr,
        )
        if ok and isinstance(data, dict) and data.get("id"):
            self._rag_fastapi_kb_id = str(data["id"])
            return True
        return False

    def _rag_fastapi_ensure_chat(self) -> bool:
        if self._rag_fastapi_chat_id:
            return True
        base = self.config.base_url.rstrip("/")
        hdr = self._rag_fastapi_headers()
        if not hdr:
            return False
        ok, _, data, _ = _http("POST", f"{base}/api/v1/chat/", {}, timeout=30, headers_extra=hdr)
        if ok and isinstance(data, dict) and data.get("id"):
            self._rag_fastapi_chat_id = str(data["id"])
            return True
        return False

    def _rag_fastapi_ingest_docs(self, docs: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not self._rag_fastapi_ensure_kb():
            return False, "rag_fastapi_kb_failed"
        base = self.config.base_url.rstrip("/")
        hdr = self._rag_fastapi_headers()
        if not hdr:
            return False, "rag_fastapi_auth_failed"
        doc_ids: List[str] = []
        for doc in docs:
            text = doc.get("content") or doc.get("text", "")
            doc_id = f"{self._case_prefix}{doc.get('doc_id', 'doc')}"
            fname = f"poison_test_{doc_id}.txt"
            url = f"{base}/api/v1/document/?kb_id={self._rag_fastapi_kb_id}"
            ok, code, data, err = _http_multipart(
                url, field_name="files", filename=fname, content=text, timeout=120, headers_extra=hdr,
            )
            if not ok and code not in (200, 201):
                return False, f"upload_failed:{code}:{err}"
            if isinstance(data, list) and data:
                doc_ids.append(str(data[0].get("id", "")))
            elif isinstance(data, dict) and data.get("id"):
                doc_ids.append(str(data["id"]))
        for did in doc_ids:
            if not did:
                continue
            ok_c, _, _, err_c = _http(
                "POST", f"{base}/api/v1/chunking/?document_id={did}", {}, timeout=180, headers_extra=hdr,
            )
            if not ok_c:
                return False, f"chunk_failed:{err_c}"
            ok_e, _, _, err_e = _http(
                "POST", f"{base}/api/v1/embedding/?document_id={did}", {}, timeout=300, headers_extra=hdr,
            )
            if not ok_e:
                return False, f"embed_failed:{err_e}"
        return True, "ok"

    def _rag_fastapi_query(self, question: str) -> Dict[str, Any]:
        if not self._rag_fastapi_ensure_chat():
            return {"ok": False, "answer": "", "http_status": 0, "error": "chat_create_failed"}
        base = self.config.base_url.rstrip("/")
        hdr = self._rag_fastapi_headers()
        ep = self.config.chat_endpoint.replace("{chat_id}", self._rag_fastapi_chat_id)
        from urllib.parse import quote
        url = f"{base}{ep}?question={quote(question)}"
        ok, status, data, latency = _http("POST", url, None, timeout=180, headers_extra=hdr)
        answer = ""
        if isinstance(data, str):
            answer = data.strip()
        elif isinstance(data, dict):
            answer = str(data.get("answer") or data.get("message") or data.get("content") or "")
        return {
            "ok": ok and bool(answer),
            "answer": answer,
            "http_status": status,
            "latency_ms": latency,
            "error": "" if ok and answer else str(data),
        }

    def _build_report_from_docs(self, docs: List[Dict[str, Any]], source: str) -> str:
        parts: List[str] = []
        for doc in docs:
            text = doc.get("content") or doc.get("text", "")
            doc_id = doc.get("doc_id", "doc")
            parts.append(f"[{source}:{doc_id}]\n{text}")
        return "\n\n".join(parts)

    def _ingest_http_multipart(self, docs: List[Dict[str, Any]], source: str) -> Tuple[bool, str]:
        ep = self.config.ingest_endpoint or self.probe_result.ingest_endpoint
        if not ep:
            return False, "no_upload_endpoint"
        base = self.config.base_url.rstrip("/")
        field_names = ("file", "files", "document", "upload")
        ok_any = False
        last_err = ""
        for doc in docs:
            text = doc.get("content") or doc.get("text", "")
            doc_id = f"{self._case_prefix}{doc.get('doc_id', 'doc')}"
            fname = f"poison_test_{doc_id}.txt"
            uploaded = False
            for field in field_names:
                ok, code, _, err = _http_multipart(
                    f"{base}{ep}",
                    field_name=field,
                    filename=fname,
                    content=text,
                    timeout=30,
                )
                if ok or code in (200, 201):
                    uploaded = True
                    ok_any = True
                    break
                last_err = f"{field}:code={code} {err}"
            if not uploaded:
                return False, last_err or "multipart_upload_failed"
        return ok_any, "ok"

    def _ingest_http(self, docs: List[Dict[str, Any]], source: str) -> Tuple[bool, str]:
        if self.config.request_format == "rag_fastapi_jwt":
            return self._rag_fastapi_ingest_docs(docs)
        ep = self.config.ingest_endpoint or self.probe_result.ingest_endpoint
        if not ep or ep == "file_kb":
            return False, "no_http_ingest"
        base = self.config.base_url.rstrip("/")
        style = self.config.ingest_style
        if ep == "/test_ingest":
            style = "http_documents"

        if style == "http_upload":
            report = self._build_report_from_docs(docs, source)
            if report:
                self._corpus_report = (
                    f"{self._corpus_report}\n\n{report}".strip() if self._corpus_report else report
                )
            mp_ok, mp_msg = self._ingest_http_multipart(docs, source)
            if mp_ok or self._corpus_report:
                return True, mp_msg if mp_ok else "report_only"
            return False, mp_msg

        for doc in docs:
            text = doc.get("content") or doc.get("text", "")
            doc_id = f"{self._case_prefix}{doc.get('doc_id', 'doc')}"
            meta = {**(doc.get("metadata") or {}), "source": source}
            payloads: List[Dict[str, Any]] = []
            if style == "http_embed":
                payloads = [
                    {"content": text, "collection_name": self._collection_name(), "content_type": "text"},
                    {"content": text, "collection_name": self._collection_name()},
                ]
            elif style == "http_upload":
                payloads = [
                    {"text": text, "doc_id": doc_id, "source": source, "metadata": meta},
                    {"content": text, "metadata": meta},
                ]
            else:
                payloads = [
                    {"doc_id": doc_id, "text": text, "source": source, "metadata": meta},
                    {"text": text, "metadata": meta},
                    {"content": text, "doc_id": doc_id},
                ]
            ok_any = False
            last_err = ""
            for payload in payloads:
                ok, code, _, err = _http("POST", f"{base}{ep}", payload)
                if ok or code in (200, 201):
                    ok_any = True
                    break
                last_err = f"code={code} {err}"
            if not ok_any:
                return False, last_err
        return True, "ok"

    def _ingest_files(self, docs: List[Dict[str, Any]], source: str) -> Tuple[bool, str]:
        repo = Path(self.config.local_path) if self.config.local_path else None
        if not repo or not repo.is_dir():
            return False, "no_local_path"

        kb_root = Path(self.config.kb_path) if self.config.kb_path else None
        if not kb_root:
            for name in KB_DIR_NAMES:
                candidate = repo / name
                if candidate.is_dir():
                    kb_root = candidate
                    break
        if not kb_root:
            kb_root = repo / "test_poison_kb"
        target_dir = kb_root / source
        target_dir.mkdir(parents=True, exist_ok=True)
        for old in target_dir.glob("poison_test_*.txt"):
            old.unlink()

        for i, doc in enumerate(docs):
            text = doc.get("content") or doc.get("text", "")
            fname = f"poison_test_{self._case_prefix}{doc.get('doc_id', i)}.txt"
            (target_dir / fname).write_text(text, encoding="utf-8")

        for script in INDEX_SCRIPTS:
            sp = repo / script
            if sp.is_file():
                py = self._venv_python()
                if py:
                    subprocess.run(
                        [str(py), str(sp)],
                        cwd=str(repo),
                        capture_output=True,
                        timeout=120,
                    )
                break

        self.ingest_method = "file_kb"
        self.config.kb_path = str(kb_root)
        return True, f"wrote_{len(docs)}_files_to_{target_dir}"

    def _venv_python(self) -> Optional[Path]:
        vp = self.config.venv_path
        if vp:
            win = Path(vp) / "Scripts" / "python.exe"
            if win.is_file():
                return win
            lin = Path(vp) / "bin" / "python"
            if lin.is_file():
                return lin
        return None

    def build_corpus(
        self,
        clean_docs: List[Dict[str, Any]],
        poison_docs: List[Dict[str, Any]],
        corpus_mode: str,
        *,
        case_id: str = "",
    ) -> Tuple[bool, str]:
        self._case_prefix = f"{case_id}_" if case_id else ""
        if self.config.request_format == "gpt_researcher_chat":
            self._corpus_report = ""
        self.reset()

        if self.config.agent_class == "minimal_http_rag" and self._minimal:
            if corpus_mode == "poison_only":
                self._minimal.reset()
                if poison_docs:
                    self._minimal.ingest_documents(poison_docs, source="poison")
            elif corpus_mode == "clean":
                self._minimal.build_corpus(clean_docs, [], corpus_mode="clean")
            else:
                self._minimal.build_corpus(clean_docs, poison_docs, corpus_mode="mixed")
            self.ingest_method = "http_ingest"
            return True, "minimal_http"

        to_ingest: List[Tuple[List[Dict[str, Any]], str]] = []
        if corpus_mode == "clean":
            to_ingest = [(clean_docs, "clean")]
        elif corpus_mode == "poison_only":
            to_ingest = [(poison_docs, "poison")]
        else:
            to_ingest = [(clean_docs, "clean"), (poison_docs, "poison")]

        for docs, source in to_ingest:
            if not docs:
                continue
            if self.config.request_format == "gpt_researcher_chat":
                report = self._build_report_from_docs(docs, source)
                if report:
                    self._corpus_report = (
                        f"{self._corpus_report}\n\n{report}".strip() if self._corpus_report else report
                    )
            style = self.config.ingest_style
            if style in ("none",) and not self.config.kb_path and not self.config.ingest_endpoint:
                return False, "no_ingest_path"
            http_first = bool(
                self.config.ingest_endpoint
                and style in ("http_documents", "http_embed", "http_upload", "http_records", "auto")
            )
            if http_first:
                ok, msg = self._ingest_http(docs, source)
                if ok:
                    self.ingest_method = "http_ingest"
                    continue
            if style == "file_kb" or (style == "auto" and self.config.kb_path and not self.config.ingest_endpoint):
                ok, msg = self._ingest_files(docs, source)
                if not ok:
                    return False, msg
                continue
            if self.config.ingest_endpoint:
                ok, msg = self._ingest_http(docs, source)
                if ok:
                    self.ingest_method = "http_ingest"
                    continue
            if self.config.kb_path:
                ok, msg = self._ingest_files(docs, source)
                if not ok:
                    return False, msg
                continue
            return False, "ingest_failed"
        return True, self.ingest_method

    def _extract_gpt_researcher_answer(self, data: Any) -> str:
        if not isinstance(data, dict):
            return str(data) if data else ""
        resp = data.get("response")
        if isinstance(resp, dict):
            return str(resp.get("content") or resp.get("message") or "")
        if isinstance(resp, str):
            return resp
        for k in ("answer", "content", "message", "output"):
            if k in data:
                return str(data[k])
        return ""

    def _query_gpt_researcher_payloads(
        self,
        question: str,
        report: str,
    ) -> Tuple[bool, int, Any, str]:
        base = self.config.base_url.rstrip("/")
        ep = self.config.chat_endpoint
        report_text = report or self._corpus_report or "research report"
        candidates: List[Tuple[str, Dict[str, Any]]] = [
            (
                "report_messages",
                {
                    "report": report_text,
                    "messages": [{"role": "user", "content": question}],
                },
            ),
            (
                "report_messages_query",
                {
                    "report": report_text,
                    "messages": [{"role": "user", "content": question}],
                    "query": question,
                },
            ),
            (
                "report_messages_task",
                {
                    "report": report_text,
                    "messages": [{"role": "user", "content": question}],
                    "task": question,
                },
            ),
        ]
        last_err = ""
        for label, payload in candidates:
            ok, status, data, latency = _http("POST", f"{base}{ep}", payload, timeout=60)
            answer = self._extract_gpt_researcher_answer(data)
            if ok and answer and "error" not in str(data).lower()[:80]:
                self.config.query_payload_log = label
                return ok, status, data, latency
            last_err = str(data)[:300]
        return False, 0, last_err, "0"

    def _query_message_payloads(
        self,
        question: str,
        collection_name: Optional[str],
    ) -> Tuple[bool, int, Any, str]:
        base = self.config.base_url.rstrip("/")
        ep = self.config.chat_endpoint.replace("{chat_id}", "poison_test_chat")
        candidates: List[Tuple[str, Dict[str, Any]]] = []
        p_msg: Dict[str, Any] = {"message": question, "agent_type": "multipurpose"}
        if collection_name:
            p_msg["collection_name"] = collection_name
        candidates.append(("message", p_msg))
        candidates.append(("input", {"input": question}))
        candidates.append(
            ("messages", {"messages": [{"role": "user", "content": question}], "agent_type": "multipurpose"})
        )
        last_err = ""
        for label, payload in candidates:
            ok, status, data, latency = _http("POST", f"{base}{ep}", payload)
            answer = ""
            if isinstance(data, dict):
                answer = str(data.get("response") or data.get("answer") or data.get("output") or "")
            if ok and answer:
                self.config.query_payload_log = label
                return ok, status, data, latency
            last_err = str(data)[:200]
        return False, 0, last_err, "0"

    def _extract_sources(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return {
                "retrieved_sources": "unknown",
                "poison_retrieved": "unknown",
                "poison_rank": "unknown",
                "retrieved_scores": "",
            }

        source_keys = (
            "sources",
            "retrieved_docs",
            "source_documents",
            "context",
            "citations",
            "documents",
            "metadata",
        )
        chunks: List[str] = []
        poison_retrieved: Any = False
        poison_rank: Any = None

        for key in source_keys:
            if key not in data:
                continue
            val = data[key]
            if isinstance(val, list):
                for i, item in enumerate(val, 1):
                    if isinstance(item, dict):
                        text = (item.get("text") or item.get("content") or str(item))[:120]
                        src = item.get("source", "")
                        chunks.append(f"#{i}|{src}|{text}")
                        if src == "poison" and not poison_retrieved:
                            poison_retrieved = True
                            poison_rank = i
                    else:
                        chunks.append(f"#{i}|{str(item)[:120]}")
            elif isinstance(val, str):
                chunks.append(val[:500])

        if not chunks:
            return {
                "retrieved_sources": "unknown",
                "poison_retrieved": "unknown",
                "poison_rank": "unknown",
                "retrieved_scores": "",
            }
        return {
            "retrieved_sources": " || ".join(chunks),
            "poison_retrieved": poison_retrieved,
            "poison_rank": poison_rank,
            "retrieved_scores": "",
        }

    def query(self, question: str) -> Dict[str, Any]:
        if self.config.agent_class == "minimal_http_rag" and self._minimal:
            r = self._minimal.query(question)
            return {
                "ok": r["ok"],
                "answer": r.get("answer", ""),
                "http_status": r.get("status_code", 0),
                "latency_ms": "",
                "error": r.get("error", ""),
                "poison_retrieved": r.get("poison_retrieved", False),
                "poison_rank": r.get("poison_rank"),
                "retrieved_sources": r.get("retrieved_sources", ""),
                "retrieved_scores": r.get("retrieved_scores", ""),
            }

        coll = self._collection_name() if self.config.collection_per_case else None

        if self.config.request_format == "invoke_input":
            base = self.config.base_url.rstrip("/")
            ep = self.config.chat_endpoint
            ok, status, data, latency = _http("POST", f"{base}{ep}", {"input": question})
        elif self.config.request_format == "gpt_researcher_chat":
            ok, status, data, latency = self._query_gpt_researcher_payloads(question, self._corpus_report)
            answer = self._extract_gpt_researcher_answer(data)
            src = self._extract_sources(data if isinstance(data, dict) else {})
            if self._corpus_report and ("[poison:" in self._corpus_report or "[poison:" in self._corpus_report.lower()):
                src["poison_retrieved"] = True
                src["poison_rank"] = 1
            return {
                "ok": ok and bool(answer),
                "answer": answer,
                "http_status": status,
                "latency_ms": latency.split("|")[0] if "|" in str(latency) else latency,
                "error": "" if ok and answer else str(data),
                **src,
            }
        elif self.config.request_format == "rag_fastapi_jwt":
            return self._rag_fastapi_query(question)
        elif self.config.request_format == "tech_trends_sse":
            base = self.config.base_url.rstrip("/")
            if not self._tech_trends_chat_id:
                ok_c, _, data_c, _ = _http("POST", f"{base}/chats", {})
                if ok_c and isinstance(data_c, dict):
                    self._tech_trends_chat_id = str(data_c.get("id", "poison_test_chat"))
                else:
                    self._tech_trends_chat_id = "poison_test_chat"
                    _http("POST", f"{base}/chats", {})
            ep = self.config.chat_endpoint.replace("{chat_id}", self._tech_trends_chat_id)
            ok, status, data, latency = _http_sse_post(f"{base}{ep}", {"message": question})
            answer = data.get("answer", "") if isinstance(data, dict) else str(data)
            return {
                "ok": ok and bool(answer),
                "answer": answer,
                "http_status": status,
                "latency_ms": latency.split("|")[0] if "|" in str(latency) else latency,
                "error": "" if ok and answer else str(data),
                **self._extract_sources(data if isinstance(data, dict) else {}),
            }
        elif self.config.request_format == "enterprise_chat":
            base = self.config.base_url.rstrip("/")
            ep = self.config.chat_endpoint
            ok, status, data, latency = _http(
                "POST", f"{base}{ep}", {"message": question, "use_rag": True, "conversation_id": "poison_test"},
            )
            answer = ""
            if isinstance(data, dict):
                resp = data.get("response")
                if isinstance(resp, dict):
                    answer = str(resp.get("content") or resp.get("answer") or resp.get("message") or "")
                answer = answer or str(
                    data.get("answer") or data.get("content")
                    or (data.get("message") if not str(data.get("message", "")).startswith("Query") else "")
                )
            return {
                "ok": ok and bool(answer),
                "answer": answer,
                "http_status": status,
                "latency_ms": latency.split("|")[0] if "|" in str(latency) else latency,
                "error": "" if ok and answer else str(data),
                **self._extract_sources(data if isinstance(data, dict) else {}),
            }
        elif self.config.request_format == "context_agent_chat":
            base = self.config.base_url.rstrip("/")
            ep = self.config.chat_endpoint
            ok, status, data, latency = _http(
                "POST", f"{base}{ep}", {"question": question, "use_rag": True, "use_agent": False},
            )
            answer = str(data.get("answer", "")) if isinstance(data, dict) else ""
            src = self._extract_sources(data if isinstance(data, dict) else {})
            if isinstance(data, dict) and data.get("sources"):
                chunks = [f"#{i}|{s}" for i, s in enumerate(data["sources"], 1)]
                src["retrieved_sources"] = " || ".join(chunks)
            return {
                "ok": ok and bool(answer),
                "answer": answer,
                "http_status": status,
                "latency_ms": latency.split("|")[0] if "|" in str(latency) else latency,
                "error": "" if ok and answer else str(data),
                **src,
            }
        elif self.config.request_format == "message":
            ok, status, data, latency = self._query_message_payloads(question, coll)
        elif self.config.request_format == "text":
            base = self.config.base_url.rstrip("/")
            ep = self.config.chat_endpoint
            ok, status, data, latency = _http("POST", f"{base}{ep}", {"text": question})
        elif self.config.http_method == "GET" or self.config.chat_endpoint.rstrip("/").endswith("/"):
            base = self.config.base_url.rstrip("/")
            ep = self.config.chat_endpoint
            param = self.config.query_param_name or "query"
            url = f"{base}{ep}?{urlencode({param: question})}"
            ok, status, data, latency = _http("GET", url)
        elif self.config.query_param_name and self._http_chat:
            ok_r = self._http_chat.query(question)
            return {
                "ok": ok_r["ok"],
                "answer": ok_r.get("answer", ""),
                "http_status": ok_r.get("status_code", 0),
                "latency_ms": "",
                "error": ok_r.get("error", ""),
                **self._extract_sources(ok_r.get("raw")),
            }
        elif self._http_chat:
            ok_r = self._http_chat.query(question)
            raw = ok_r.get("raw")
            src = self._extract_sources(raw if isinstance(raw, dict) else {})
            if isinstance(raw, dict):
                if "poison_retrieved" in raw:
                    src["poison_retrieved"] = raw["poison_retrieved"]
                if "poison_rank" in raw:
                    src["poison_rank"] = raw["poison_rank"]
                if "sources" in raw and isinstance(raw["sources"], list):
                    chunks = [
                        f"#{s.get('rank', i)}|{s.get('source', '')}|{str(s.get('text', ''))[:120]}"
                        for i, s in enumerate(raw["sources"], 1)
                        if isinstance(s, dict)
                    ]
                    if chunks:
                        src["retrieved_sources"] = " || ".join(chunks)
            return {
                "ok": ok_r["ok"],
                "answer": ok_r.get("answer", ""),
                "http_status": ok_r.get("status_code", 0),
                "latency_ms": "",
                "error": ok_r.get("error", ""),
                "raw": raw,
                **src,
            }
        else:
            ok, status, data, latency = _http(
                "POST",
                f"{self.config.base_url.rstrip('/')}{self.config.chat_endpoint}",
                {"question": question},
            )
            answer = ""
            if isinstance(data, dict):
                for k in ("answer", "response", "result", "output", "message"):
                    if k in data:
                        answer = str(data[k])
                        break
            elif isinstance(data, str):
                answer = data
            src = self._extract_sources(data if isinstance(data, dict) else {})
            return {
                "ok": ok,
                "answer": answer,
                "http_status": status,
                "latency_ms": latency.split("|")[0] if latency else "",
                "error": "" if ok else str(data),
                **src,
            }

        answer = ""
        if isinstance(data, dict):
            for k in ("answer", "response", "result", "output"):
                if k in data:
                    answer = str(data[k])
                    break
        elif isinstance(data, str):
            answer = data
        src = self._extract_sources(data if isinstance(data, dict) else {})
        return {
            "ok": ok,
            "answer": answer,
            "http_status": status,
            "latency_ms": latency.split("|")[0] if "|" in str(latency) else latency,
            "error": "" if ok else str(data),
            **src,
        }


def detect_kb_path(local_path: str) -> str:
    repo = Path(local_path)
    if not repo.is_dir():
        return ""
    for name in KB_DIR_NAMES:
        p = repo / name
        if p.is_dir():
            return str(p)
    return ""


def config_from_registry_entry(entry: Dict[str, Any]) -> GitHubAgentConfig:
    aid = entry.get("id", "")
    repo = entry.get("repo_url", "")
    is_minimal = aid == "minimal_http_rag_agent" or str(repo).startswith("local://")
    agent_class = "minimal_http_rag" if is_minimal else "real_github_http"
    rf = entry.get("request_format", "question")
    if rf == "invoke_query":
        rf = "question"
    return GitHubAgentConfig(
        agent_id=aid,
        agent_class=agent_class,
        repo_url=repo,
        framework=entry.get("framework", ""),
        base_url=entry.get("api_base_url", ""),
        local_path=entry.get("local_path", ""),
        chat_endpoint=entry.get("chat_endpoint", "/query"),
        http_method=entry.get("http_method", "POST"),
        request_format=rf,
        query_param_name=entry.get("query_param_name"),
        ingest_endpoint=entry.get("ingest_endpoint", ""),
        reset_endpoint=entry.get("reset_endpoint", ""),
        kb_path=detect_kb_path(entry.get("local_path", "")),
    )


def _resolve_repo_path(entry: Dict[str, Any]) -> str:
    aid = entry.get("id", "")
    candidates = [
        Path(r"D:\AI\target_agents_bulk") / aid / "repo",
        Path(r"D:\AI\target_agents") / aid.replace("-", "_"),
    ]
    lp = entry.get("local_path", "")
    if lp:
        candidates.append(Path(lp))
    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return lp


def _build_start_command(
    entry: Dict[str, Any],
    manifest: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    mf = manifest or {}
    vp = entry.get("venv_path", "")
    py = Path(vp) / "Scripts" / "python.exe" if vp else None
    if not py or not py.is_file():
        aid = entry.get("id", "")
        alt = Path(r"D:\AI\target_agents_bulk") / aid / ".venv" / "Scripts" / "python.exe"
        if alt.is_file():
            py = alt
    port = entry.get("assigned_port") or 19099
    repo_path = _resolve_repo_path(entry)
    entry_mod = mf.get("entry_module", "main:app")
    cwd_rel = mf.get("cwd", "repo")
    if cwd_rel == "repo":
        start_cwd = repo_path
    else:
        start_cwd = str((Path(repo_path) / cwd_rel).resolve())

    if mf.get("server_type") == "quart":
        return f'"{py}" -m quart run --host 127.0.0.1 --port {port}', start_cwd
    if py and py.is_file():
        env_prefix = ""
        if mf.get("env_pythonpath"):
            env_prefix = f'set PYTHONPATH={mf["env_pythonpath"]} && '
        extra_env = mf.get("start_env") or {}
        extra_parts = [f"set {k}={v}" for k, v in extra_env.items()]
        extra_str = " && ".join(extra_parts) + " && " if extra_parts else ""
        return (
            f'set PYTHONPATH= && set POISON_TEST_FAKE_EMBEDDINGS=1 && {extra_str}{env_prefix}"{py}" -m uvicorn {entry_mod} --host 127.0.0.1 --port {port}',
            start_cwd,
        )
    return "", start_cwd


def apply_manifest_overrides(
    cfg: GitHubAgentConfig,
    manifest: Dict[str, Any],
    entry: Dict[str, Any],
) -> GitHubAgentConfig:
    if not manifest:
        return cfg
    start, cwd = _build_start_command(entry, manifest)
    if start:
        cfg.start_command = start
    if cwd:
        cfg.start_cwd = cwd
    for key in (
        "chat_endpoint",
        "ingest_endpoint",
        "reset_endpoint",
        "http_method",
        "request_format",
        "query_param_name",
        "ingest_style",
        "kb_path",
        "tier",
    ):
        if manifest.get(key):
            setattr(cfg, key, manifest[key])
    if manifest.get("collection_per_case"):
        cfg.collection_per_case = True
    if manifest.get("lock_query_endpoint") or manifest.get("chat_endpoint"):
        cfg.lock_query_endpoint = True
    if manifest.get("rag_capable") is False and cfg.ingest_style == "auto":
        cfg.ingest_style = "none"
    if cfg.ingest_style == "http_embed" and not cfg.ingest_endpoint:
        cfg.ingest_endpoint = "/embed"
    if cfg.kb_path and not Path(cfg.kb_path).is_absolute():
        cfg.kb_path = str(Path(cfg.local_path) / cfg.kb_path)
    port = entry.get("assigned_port")
    if port and not cfg.base_url:
        cfg.base_url = f"http://127.0.0.1:{port}"
    return cfg


def config_from_bulk_entry(
    entry: Dict[str, Any],
    manifest: Optional[Dict[str, Any]] = None,
) -> GitHubAgentConfig:
    repo_path = _resolve_repo_path(entry)
    feats = scan_repo_features(Path(repo_path)) if repo_path and Path(repo_path).is_dir() else {}
    le = feats.get("likely_endpoints") or entry.get("likely_endpoints") or {}
    port = entry.get("assigned_port") or 19099
    chat = (
        entry.get("query_endpoint")
        or entry.get("chat_endpoint")
        or le.get("query")
        or le.get("chat")
        or le.get("invoke")
        or "/query"
    )
    ingest = entry.get("ingest_endpoint") or le.get("ingest") or le.get("documents") or le.get("upload") or ""
    reset_ep = entry.get("reset_endpoint") or ""
    start, start_cwd = _build_start_command(entry, manifest)
    vp = entry.get("venv_path", "")
    return GitHubAgentConfig(
        agent_id=entry.get("id", ""),
        agent_class="real_github_http",
        repo_url=entry.get("repo_url", ""),
        framework=entry.get("framework", ""),
        base_url=entry.get("api_base_url") or f"http://127.0.0.1:{port}",
        local_path=repo_path,
        chat_endpoint=chat,
        http_method="GET" if chat.endswith("/") else "POST",
        request_format="question",
        ingest_endpoint=ingest,
        reset_endpoint=reset_ep,
        kb_path=detect_kb_path(repo_path),
        ingest_style="auto",
        start_command=start,
        start_cwd=start_cwd,
        venv_path=vp,
    )
