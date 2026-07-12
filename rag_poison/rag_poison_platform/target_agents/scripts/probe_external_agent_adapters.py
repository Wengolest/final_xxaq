"""Probe external agent adapter configs: start/connect, health, ingest, query."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import RESULTS_DIR, write_csv
from target_agents.external_adapters.common import (
    load_all_adapters,
    probe_health,
    probe_post_endpoint,
    try_start_agent,
)

PROBE_CSV = RESULTS_DIR / "external_agent_adapter_probe.csv"
FIELDS = [
    "agent_id",
    "started",
    "health_ok",
    "ingest_supported",
    "query_supported",
    "rag_loop_supported",
    "error_type",
    "notes",
]


def _probe_one(cfg: Dict[str, Any]) -> Dict[str, Any]:
    agent_id = cfg.get("agent_id", "")
    base = cfg.get("base_url", "")
    row: Dict[str, Any] = {
        "agent_id": agent_id,
        "started": False,
        "health_ok": False,
        "ingest_supported": False,
        "query_supported": False,
        "rag_loop_supported": False,
        "error_type": "",
        "notes": "",
    }
    try:
        health_ep = cfg.get("health_endpoint") or "/health"
        ok_health, used = probe_health(base, health_ep)
        if ok_health:
            row["health_ok"] = True
            row["notes"] = f"already_running{used}"
        else:
            started, note, _ = try_start_agent(cfg, timeout_sec=10)
            row["started"] = started
            row["notes"] = note
            if started:
                ok_health, used = probe_health(base, health_ep)
                row["health_ok"] = ok_health
                if ok_health:
                    row["notes"] = f"{note}; health={used}"
            else:
                row["error_type"] = "start_failed"
                return row

        if not row["health_ok"]:
            row["error_type"] = row["error_type"] or "health_failed"
            return row

        q_tpl = cfg.get("query_payload_template") or {"question": "hello"}
        q_ep = cfg.get("query_endpoint") or cfg.get("chat_endpoint") or ""
        q_param = cfg.get("query_param") or ""
        if q_ep:
            sample = {k: (v.replace("{query}", "hello") if isinstance(v, str) else v) for k, v in q_tpl.items()}
            ok_q, qnote = probe_post_endpoint(
                base, q_ep, sample, query_param=q_param or None, query_value="hello"
            )
            row["query_supported"] = ok_q
            if not ok_q:
                row["notes"] += f"; query_fail={qnote}"

        i_ep = cfg.get("ingest_endpoint") or ""
        if i_ep:
            i_tpl = cfg.get("ingest_payload_template")
            if i_tpl:
                sample_i = {
                    k: (v.replace("{text}", "probe").replace("{doc_id}", "probe_1") if isinstance(v, str) else v)
                    for k, v in i_tpl.items()
                }
                ok_i, inote = probe_post_endpoint(base, i_ep, sample_i)
            else:
                ok_i, inote = probe_post_endpoint(base, i_ep, {"filename": "probe.txt", "content": "probe"})
            row["ingest_supported"] = ok_i
            if not ok_i:
                row["notes"] += f"; ingest_fail={inote}"

        row["rag_loop_supported"] = row["health_ok"] and row["query_supported"] and row["ingest_supported"]
        if row["health_ok"] and row["query_supported"] and not row["ingest_supported"]:
            row["error_type"] = "no_ingest"
        elif row["health_ok"] and not row["query_supported"]:
            row["error_type"] = "no_query"
    except Exception as e:
        row["error_type"] = type(e).__name__
        row["notes"] = str(e)[:300]
    return row


def main() -> None:
    adapters = load_all_adapters()
    rows: List[Dict[str, Any]] = []
    for cfg in adapters:
        rows.append(_probe_one(cfg))
    write_csv(PROBE_CSV, rows, fieldnames=FIELDS)
    ok = sum(1 for r in rows if str(r.get("rag_loop_supported")).lower() == "true")
    print(f"Probed {len(rows)} adapters -> {PROBE_CSV} (rag_loop_supported={ok})")


if __name__ == "__main__":
    main()
