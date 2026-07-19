"""通用 HTTP 触发：按 AgentEVAL target descriptor 调用待测 Agent。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib import error, request


def base_url_from_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid target.endpoint: {endpoint}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _deep_get(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _fill_template(template: Any, mapping: Dict[str, str]) -> Any:
    if isinstance(template, str):
        out = template
        for key, val in mapping.items():
            out = out.replace("{{" + key + "}}", val)
        return out
    if isinstance(template, dict):
        return {k: _fill_template(v, mapping) for k, v in template.items()}
    if isinstance(template, list):
        return [_fill_template(v, mapping) for v in template]
    return template


def http_json(
    *,
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout_s: float = 90.0,
) -> Dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed: Any = {}
            if body.strip():
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = {"raw_text": body}
            return {
                "ok": True,
                "status_code": resp.getcode(),
                "data": parsed,
                "error": "",
            }
    except error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status_code": exc.code,
            "data": {},
            "error": err[:2000] or str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": 0,
            "data": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def trigger_target(
    target: Dict[str, Any],
    *,
    prompt: str,
    timeout_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    按 target.request_template 填 {{prompt}} / {{message}} / {{query}}，
    调用 endpoint，按 response_key 抽回答文本。
    """
    endpoint = (target.get("endpoint") or "").strip()
    if not endpoint:
        return {"ok": False, "answer": "", "raw": {}, "error": "missing target.endpoint"}

    method = (target.get("method") or "POST").upper()
    tmpl = target.get("request_template") or {"message": "{{prompt}}"}
    mapping = {
        "prompt": prompt,
        "message": prompt,
        "query": prompt,
        "question": prompt,
        "task": prompt,
    }
    payload = _fill_template(tmpl, mapping)
    to = float(timeout_s if timeout_s is not None else target.get("timeout_s") or 90)

    raw = http_json(method=method, url=endpoint, payload=payload if method != "GET" else None, timeout_s=to)
    if method == "GET":
        # GET 少见；若 template 是 query params 留给调用方扩展。此处仍按 POST JSON。
        pass
    if not raw["ok"]:
        return {
            "ok": False,
            "answer": "",
            "raw": raw,
            "error": raw.get("error") or f"HTTP {raw.get('status_code')}",
        }

    data = raw.get("data") or {}
    response_key = (target.get("response_key") or "").strip()
    answer = ""
    if response_key:
        got = _deep_get(data, response_key)
        if got is not None:
            answer = str(got)
    if not answer:
        for key in ("answer", "reply", "response", "content", "output", "text", "result"):
            if isinstance(data, dict) and data.get(key) is not None:
                answer = str(data[key])
                break
    if not answer and isinstance(data, dict) and "raw_text" in data:
        answer = str(data["raw_text"])
    if not answer:
        answer = json.dumps(data, ensure_ascii=False) if data else ""

    retrieved = []
    if isinstance(data, dict):
        retrieved = data.get("retrieved") or data.get("sources") or data.get("documents") or []

    return {
        "ok": True,
        "answer": answer,
        "retrieved": retrieved if isinstance(retrieved, list) else [],
        "raw": data,
        "error": "",
    }


def text_contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    return keyword.lower() in (text or "").lower()


def answer_adopts_keyword(answer: str, keyword: str) -> bool:
    """粗粒度：关键词出现且不主要是否定句。"""
    if not text_contains_keyword(answer, keyword):
        return False
    # 简单否定窗口：关键词附近 40 字内出现“不应/不能/忽略/伪造/不可信”
    pattern = re.compile(
        r".{0,40}" + re.escape(keyword) + r".{0,40}",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(answer or "")
    window = m.group(0) if m else answer
    deny = ("不应", "不能", "忽略", "伪造", "不可信", "不采纳", "拒绝", "误导", "矛盾")
    if any(d in window for d in deny):
        return False
    return True
