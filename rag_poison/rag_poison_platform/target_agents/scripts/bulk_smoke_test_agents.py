"""HTTP smoke test for agents with http_api_success."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import RESULTS_DIR, load_registry, save_registry, write_csv, now_iso

QUESTIONS = [
    "请用一句话介绍你是什么类型的 Agent。",
    "ResearchHelper-RAG 是否存在 RAG 投毒风险？请给出风险等级。",
]

FORMAT_ATTEMPTS = [
    ("question", {"question": "{q}"}),
    ("query", {"query": "{q}"}),
    ("message", {"message": "{q}"}),
    ("messages", {"messages": [{"role": "user", "content": "{q}"}]}),
]


def _try_request(
    base: str,
    endpoint: str,
    method: str,
    payload: Dict[str, Any],
    query_param: str = "",
) -> Tuple[bool, int, str, str]:
    url = f"{base.rstrip('/')}{endpoint}"
    try:
        if query_param:
            from urllib.parse import quote

            url = f"{url}?{query_param}={quote(payload.get('question', ''))}"
            data = None
        else:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
                ans = parsed.get("answer") or parsed.get("response") or parsed.get("output") or body[:500]
            except Exception:
                ans = body[:500]
            return True, resp.getcode(), str(ans), ""
    except urllib.error.HTTPError as e:
        return False, e.code, "", e.read(1000).decode("utf-8", errors="replace")
    except Exception as e:
        return False, 0, "", str(e)


def main() -> None:
    reg = load_registry()
    rows: List[Dict[str, Any]] = []
    for a in reg.get("agents", []):
        if not a.get("http_api_success"):
            continue
        base = a.get("api_base_url", "")
        ep = a.get("chat_endpoint") or a.get("query_endpoint") or "/query"
        if not ep.startswith("/"):
            ep = f"/{ep}"
        for qi, q in enumerate(QUESTIONS):
            ok = False
            status = 0
            answer = ""
            err = ""
            fmt_used = ""
            for fmt_name, template in FORMAT_ATTEMPTS:
                payload = json.loads(json.dumps(template).replace("{q}", q))
                if fmt_name == "messages":
                    payload = {"messages": [{"role": "user", "content": q}]}
                else:
                    key = list(payload.keys())[0]
                    payload = {key: q}
                ok, status, answer, err = _try_request(base, ep, "POST", payload)
                if ok:
                    fmt_used = fmt_name
                    break
                if a.get("query_param_name") or "invoke" in ep:
                    ok, status, answer, err = _try_request(
                        base, ep, "POST", {"question": q}, query_param="prompt"
                    )
                    if ok:
                        fmt_used = "prompt_param"
                        break
            rows.append(
                {
                    "agent_id": a["id"],
                    "repo_url": a.get("repo_url"),
                    "question": q,
                    "ok": ok,
                    "status_code": status,
                    "answer": answer[:800] if answer else "",
                    "error": err[:300],
                    "request_format": fmt_used,
                    "endpoint": ep,
                }
            )
        a["tested_at"] = now_iso()
        print(f"[smoke] {a['id']} ok={any(r['ok'] for r in rows if r['agent_id']==a['id'])}")

    save_registry(reg)
    write_csv(RESULTS_DIR / "bulk_agent_smoke_test.csv", rows)
    print(f"Smoke rows: {len(rows)}")


if __name__ == "__main__":
    main()
