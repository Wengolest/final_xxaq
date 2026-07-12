#!/usr/bin/env python3
"""Import poison module JSON/CSV results into defense_engine experiments store."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _load_prompt_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for row in data.get("results", []):
        compromised = row.get("injection_succeeded", False)
        results.append({
            "id": row.get("case_id", ""),
            "family": "prompt_injection",
            "is_attack": row.get("case_id") != "baseline_safe_question",
            "content": (row.get("prompt") or "")[:80],
            "verdict": "passed" if row.get("verdict") == "PASS" else ("blocked" if row.get("verdict") == "FAIL" else "warned"),
            "blocked_by": "" if compromised else "model_interaction",
            "risk_score": 1.0 if compromised else 0.1,
            "layer_details": {},
            "elapsed_ms": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    summary = data.get("summary", {})
    total = summary.get("total") or len(results)
    attacks = [r for r in results if r["is_attack"]]
    compromised_n = sum(1 for r in attacks if r["verdict"] != "passed")
    dsr = (len(attacks) - compromised_n) / len(attacks) if attacks else 0
    return {
        "name": f"Prompt投毒评估 — {path.stem}",
        "attack_families": ["prompt_injection"],
        "metrics": {
            "dsr": round(dsr, 4),
            "asr": round(compromised_n / len(attacks), 4) if attacks else 0,
            "fpr": 0,
            "fnr": round(compromised_n / len(attacks), 4) if attacks else 0,
            "total_samples": total,
            "attack_compromised": compromised_n,
        },
        "results": results,
        "timeline": [{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "status_change",
            "target_id": "library_faq_agent",
            "attack_family": "prompt_injection",
            "case_id": "",
            "message": f"Imported from {path.name}",
        }],
    }


def _load_multiagent_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for scenario, info in data.items():
        if not isinstance(info, dict):
            continue
        success = info.get("attack_success_rate", 0) or info.get("asr", 0)
        results.append({
            "id": scenario,
            "family": "multi_agent_hijack",
            "is_attack": True,
            "content": scenario[:80],
            "verdict": "passed" if success < 0.5 else "blocked",
            "blocked_by": "decision_supervision" if success < 0.5 else "",
            "risk_score": float(success),
            "layer_details": {},
            "elapsed_ms": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return {
        "name": f"多Agent投毒 — {path.stem}",
        "attack_families": ["multi_agent_hijack"],
        "metrics": {"dsr": 0.5, "asr": 0.5, "total_samples": len(results)},
        "results": results,
        "timeline": [],
    }


def import_result_file(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        if "prompt_injection" in path.name or "deepseek" in path.name:
            return _load_prompt_json(path)
        return _load_multiagent_json(path)
    raise ValueError(f"Unsupported result file: {path}")


def post_to_server(payload: dict[str, Any], base_url: str = "http://127.0.0.1:8100") -> dict[str, Any]:
    import urllib.request

    body = json.dumps({
        "name": payload["name"],
        "mode": "balanced",
        "attack_families": payload.get("attack_families", []),
        "metrics": payload["metrics"],
        "results": payload["results"],
        "timeline": payload.get("timeline", []),
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/experiments/manual",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: aggregate_results.py <result.json> [--post]")
        return 1
    path = Path(sys.argv[1]).resolve()
    payload = import_result_file(path)
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    if "--post" in sys.argv:
        resp = post_to_server(payload)
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
