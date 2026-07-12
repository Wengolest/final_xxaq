"""Score external GitHub agents and write shortlist + adapter YAML stubs."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import RESULTS_DIR, load_registry, repo_path, write_csv
from utils.deepseek_env import API_DEPENDENT_AGENT_IDS, classify_api_dependency, scan_repo_external_services

ADAPTER_DIR = SCRIPT_DIR.parent / "external_adapters"
SHORTLIST_CSV = RESULTS_DIR / "external_agent_candidate_shortlist.csv"
TOP_N = 3
PREFERRED_IDS = ["fastapi-meets-langgraph", "langgraph-agents", "gpt-researcher"]

AGENT_ADAPTER_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "fastapi-meets-langgraph": {
        "health_endpoint": "/docs",
        "query_endpoint": "/agents/invoke",
        "ingest_endpoint": "",
        "query_param": "prompt",
        "query_payload_template": {},
        "response_path": "response",
        "notes": "LangGraph invoke via query param prompt; no standard ingest API",
    },
    "langgraph-agents": {
        "health_endpoint": "/health",
        "query_endpoint": "/chat",
        "ingest_endpoint": "/embed",
        "query_payload_template": {
            "message": "{query}",
            "agent_type": "multipurpose",
        },
        "ingest_payload_template": {
            "content": "{text}",
            "collection_name": "general_knowledge",
        },
        "response_path": "response",
        "notes": "FastAPI+LangGraph; embed endpoint as ingest surrogate",
    },
    "gpt-researcher": {
        "health_endpoint": "/",
        "query_endpoint": "/api/chat",
        "ingest_endpoint": "/upload/",
        "query_payload_template": {"message": "{query}"},
        "ingest_payload_template": {},
        "response_path": "response",
        "notes": "Research agent; may need Tavily/search APIs; upload as ingest probe",
    },
}

FIELDS = [
    "agent_id",
    "reason",
    "install_success",
    "requires_api_key",
    "requires_external_service",
    "likely_start_command",
    "likely_query_endpoint",
    "likely_ingest_endpoint",
    "adapter_feasibility",
]


def _score_agent(agent: Dict[str, Any], inspect: Dict[str, str]) -> int:
    s = 0
    if agent.get("install_success"):
        s += 40
    if agent.get("clone_success"):
        s += 5
    if inspect.get("has_fastapi") == "True" or agent.get("has_fastapi"):
        s += 15
    if inspect.get("has_langchain") == "True" or agent.get("has_langchain"):
        s += 5
    if inspect.get("has_langgraph") == "True" or agent.get("has_langgraph"):
        s += 5
    if inspect.get("query_endpoint"):
        s += 15
    elif agent.get("query_endpoint") or agent.get("chat_endpoint"):
        s += 10
    if inspect.get("ingest_endpoint") or agent.get("ingest_endpoint"):
        s += 15
    if agent.get("id") in API_DEPENDENT_AGENT_IDS:
        s -= 50
    if agent.get("install_skipped") or agent.get("external_service_missing"):
        s -= 40
    if str(inspect.get("requires_docker", "")).lower() == "true":
        s -= 10
    return s


def _feasibility(agent: Dict[str, Any], score: int) -> str:
    if agent.get("id") in API_DEPENDENT_AGENT_IDS:
        return "low_external_api_deps"
    if not agent.get("install_success"):
        return "low_install_failed"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _venv_python(agent: Dict[str, Any]) -> str:
    vp = Path(agent.get("venv_path") or venv_path(agent["id"]))
    win = vp / "Scripts" / "python.exe"
    if win.is_file():
        return str(win)
    return str(vp / "bin" / "python")


def _start_command(agent: Dict[str, Any]) -> str:
    port = agent.get("assigned_port") or 19001
    py = _venv_python(agent)
    aid = agent.get("id", "")
    if aid == "gpt-researcher":
        return f'"{py}" -m uvicorn backend.server.app:app --host 127.0.0.1 --port {port}'
    start_tpl = (agent.get("deploy_commands") or {}).get("start", "")
    if start_tpl:
        return start_tpl.replace("<port>", str(port)).replace("uvicorn", f'"{py}" -m uvicorn', 1)
    if agent.get("has_fastapi"):
        return f'"{py}" -m uvicorn app:app --host 127.0.0.1 --port {port}'
    return ""


def _load_inspect() -> Dict[str, Dict[str, str]]:
    path = RESULTS_DIR / "bulk_agent_inspect_report.csv"
    out: Dict[str, Dict[str, str]] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out[row["agent_id"]] = row
    return out


def _adapter_yaml(agent: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    port = agent.get("assigned_port") or 19001
    le = agent.get("likely_endpoints") or {}
    query = (
        row.get("likely_query_endpoint")
        or agent.get("query_endpoint")
        or agent.get("chat_endpoint")
        or le.get("query")
        or le.get("chat")
        or le.get("invoke")
        or ""
    )
    ingest = row.get("likely_ingest_endpoint") or agent.get("ingest_endpoint") or le.get("ingest") or le.get("upload") or ""
    overrides = AGENT_ADAPTER_OVERRIDES.get(agent["id"], {})
    query = overrides.get("query_endpoint") or query
    ingest = overrides.get("ingest_endpoint") if "ingest_endpoint" in overrides else ingest
    return {
        "agent_id": agent["id"],
        "sample_type": "external_github_agent",
        "local_path": agent.get("local_path", ""),
        "repo_path": agent.get("local_path", ""),
        "base_url": f"http://127.0.0.1:{port}",
        "assigned_port": port,
        "start_command": row["likely_start_command"],
        "health_endpoint": overrides.get("health_endpoint") or agent.get("health_endpoint") or le.get("health") or "/health",
        "ingest_endpoint": ingest,
        "query_endpoint": query,
        "reset_endpoint": overrides.get("reset_endpoint", ""),
        "request_format": overrides.get("request_format", "json"),
        "query_param": overrides.get("query_param", ""),
        "query_payload_template": overrides.get(
            "query_payload_template", {"question": "{query}"}
        ),
        "ingest_payload_template": overrides.get(
            "ingest_payload_template", {"text": "{text}", "doc_id": "{doc_id}"}
        ),
        "response_path": overrides.get("response_path", "answer"),
        "requires_api_key": True,
        "deepseek_compat": True,
        "notes": overrides.get("notes", row["reason"]),
    }


def main() -> None:
    reg = load_registry()
    inspect_map = _load_inspect()
    candidates: List[Dict[str, Any]] = []

    for agent in reg.get("agents", []):
        if agent.get("local_variant"):
            continue
        aid = agent["id"]
        if not agent.get("clone_success"):
            continue
        insp = inspect_map.get(aid, {})
        repo = Path(agent["local_path"]) if agent.get("local_path") else repo_path(aid)
        _, _, ext_missing = classify_api_dependency(
            aid, repo, install_success=bool(agent.get("install_success"))
        )
        score = _score_agent(agent, insp)
        query_ep = insp.get("query_endpoint") or agent.get("query_endpoint") or agent.get("chat_endpoint") or ""
        ingest_ep = insp.get("ingest_endpoint") or agent.get("ingest_endpoint") or ""
        ext_markers = scan_repo_external_services(repo) if repo.is_dir() else []
        row = {
            "agent_id": aid,
            "reason": f"score={score}; fastapi={insp.get('has_fastapi', agent.get('has_fastapi'))}; query={query_ep or 'none'}",
            "install_success": agent.get("install_success", False),
            "requires_api_key": agent.get("requires_llm_key", True),
            "requires_external_service": ext_missing or aid in API_DEPENDENT_AGENT_IDS,
            "likely_start_command": _start_command(agent),
            "likely_query_endpoint": query_ep,
            "likely_ingest_endpoint": ingest_ep,
            "adapter_feasibility": _feasibility(agent, score),
            "_score": score,
            "_ext_markers": ",".join(ext_markers[:4]),
        }
        candidates.append(row)

    by_id = {c["agent_id"]: c for c in candidates}
    candidates.sort(key=lambda x: x["_score"], reverse=True)

    def _eligible(c: Dict[str, Any]) -> bool:
        return bool(c.get("likely_start_command"))

    shortlisted: List[Dict[str, Any]] = []
    for pid in PREFERRED_IDS:
        c = by_id.get(pid)
        if c and _eligible(c):
            shortlisted.append(c)
    for c in candidates:
        if c in shortlisted:
            continue
        if not _eligible(c):
            continue
        shortlisted.append(c)
        if len(shortlisted) >= TOP_N:
            break
    shortlisted = shortlisted[:TOP_N]

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    out_rows = []
    for c in shortlisted:
        c.pop("_score", None)
        ext = c.pop("_ext_markers", "")
        if ext:
            c["reason"] += f"; ext_deps={ext}"
        agent = next(a for a in reg["agents"] if a["id"] == c["agent_id"])
        ov = AGENT_ADAPTER_OVERRIDES.get(c["agent_id"], {})
        if ov.get("query_endpoint"):
            c["likely_query_endpoint"] = ov["query_endpoint"]
        if "ingest_endpoint" in ov:
            c["likely_ingest_endpoint"] = ov["ingest_endpoint"]
        if ov.get("notes"):
            c["reason"] = ov["notes"]
        out_rows.append({k: c.get(k, "") for k in FIELDS})
        yaml_path = ADAPTER_DIR / f"{c['agent_id']}.yaml"
        with yaml_path.open("w", encoding="utf-8") as f:
            yaml.dump(_adapter_yaml(agent, c), f, allow_unicode=True, sort_keys=False)

    write_csv(SHORTLIST_CSV, out_rows, fieldnames=FIELDS)
    print(f"Shortlisted {len(out_rows)} agents -> {SHORTLIST_CSV}")
    for r in out_rows:
        print(f"  {r['agent_id']} feasibility={r['adapter_feasibility']}")


if __name__ == "__main__":
    main()
