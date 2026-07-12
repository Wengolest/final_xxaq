"""Probe HTTP endpoints for agents listed in registry.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from target_agents.adapters.http_agent_adapter import HttpAgentAdapter

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "registry.yaml"


def load_registry() -> list:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload.get("agents", [])


def probe_agent(agent: dict) -> None:
    agent_id = agent.get("id", "unknown")
    base = (agent.get("api_base_url") or "").strip()
    status = agent.get("status", "")

    print(f"\n=== {agent_id} (status={status}) ===")
    if not base:
        print("  skip: api_base_url empty")
        return

    adapter = HttpAgentAdapter(
        base_url=base,
        chat_endpoint=agent.get("chat_endpoint") or "/chat",
        method=agent.get("http_method", "POST"),
        request_format=agent.get("request_format", "question"),
        query_param_name=agent.get("query_param_name"),
    )

    for label, path in [
        ("docs", agent.get("docs_endpoint") or "/docs"),
        ("health", agent.get("health_endpoint") or ""),
        ("openapi", "/openapi.json"),
    ]:
        if not path:
            continue
        result = adapter.probe_url(path)
        print(
            f"  [{label}] {path} -> ok={result['ok']} "
            f"status={result['status_code']} err={result.get('error', '')[:80]}"
        )

    chat_path = agent.get("chat_endpoint")
    if chat_path and status in {"running", "installed"}:
        smoke_q = "ping: reply with one short sentence."
        chat_result = adapter.query(smoke_q)
        print(
            f"  [chat] {chat_path} -> ok={chat_result['ok']} "
            f"status={chat_result['status_code']}"
        )
        if chat_result.get("error"):
            print(f"    error: {chat_result['error'][:200]}")
        elif chat_result.get("answer"):
            print(f"    answer: {str(chat_result['answer'])[:120]}...")


def main() -> None:
    agents = load_registry()
    candidates = [
        a
        for a in agents
        if a.get("api_base_url") or a.get("status") in {"running", "installed", "cloned"}
    ]
    if not candidates:
        print("No agents in registry.")
        return
    for agent in agents:
        try:
            probe_agent(agent)
        except Exception as exc:
            print(f"\n=== {agent.get('id')} ERROR ===\n  {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
