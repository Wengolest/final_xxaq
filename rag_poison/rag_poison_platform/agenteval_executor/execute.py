"""
读取 AgentEVAL execution_bundle.json，执行全部 case，写出 results.json。

用法（在 rag_poison_platform 根目录）:
  python -m runners.run_agenteval_bundle --bundle path/to/execution_bundle.json
  python -m runners.run_agenteval_bundle --bundle ... --out results/agenteval_results.json
  python -m runners.run_agenteval_bundle --bundle ... --post http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from agenteval_executor.failure_stages import EXECUTION_SCHEMA, RESULTS_SCHEMA
from agenteval_executor.runners import run_one_case


def load_bundle(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # POST /evaluations 响应可能包一层 execution_bundle
    if "execution_bundle" in data and isinstance(data["execution_bundle"], dict):
        bundle = data["execution_bundle"]
        if not bundle.get("evaluation_id"):
            bundle["evaluation_id"] = data.get("evaluation_id") or data.get("analysis_id")
        return bundle
    return data


def write_results(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def post_results(base_url: str, evaluation_id: str, payload: Dict[str, Any], api_token: str = "") -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/evaluations/{evaluation_id}/results"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["X-API-Key"] = api_token
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status_code": resp.getcode(), "body": text}
    except error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": exc.code, "body": err}
    except Exception as exc:
        return {"ok": False, "status_code": 0, "body": str(exc)}


def execute_bundle(
    bundle: Dict[str, Any],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    schema = bundle.get("schema_version") or ""
    if schema and not str(schema).startswith("agenteval.execution"):
        raise ValueError(f"unsupported schema_version: {schema} (expect {EXECUTION_SCHEMA})")

    evaluation_id = bundle.get("evaluation_id") or bundle.get("analysis_id") or ""
    target = bundle.get("target") or {}
    cases: List[Dict[str, Any]] = list(bundle.get("cases") or [])
    if not cases:
        raise ValueError("execution_bundle.cases is empty")

    results: List[Dict[str, Any]] = []
    for case in cases:
        case_id = case.get("case_id")
        if not case_id:
            raise ValueError("case missing case_id")
        started = time.monotonic()
        if dry_run:
            item = {
                "case_id": case_id,
                "failure_stage": "not_triggered",
                "metrics": {
                    "real_attack_success": False,
                    "setup_ok": True,
                    "cleanup_ok": True,
                    "latency_ms": 0,
                    "dry_run": True,
                },
                "feedback": {"executor": "rag_poison_platform", "note": "dry_run"},
            }
        else:
            out = run_one_case(case, target)
            metrics = dict(out.get("metrics") or {})
            metrics.setdefault("latency_ms", int((time.monotonic() - started) * 1000))
            metrics.setdefault("real_attack_success", out.get("failure_stage") == "attack_success")
            item = {
                "case_id": case_id,
                "failure_stage": out.get("failure_stage") or "require_review",
                "metrics": metrics,
                "feedback": {
                    "executor": str(case.get("executor") or "rag_poison_platform"),
                    "attack_family": str(case.get("attack_family") or ""),
                },
            }
        if evaluation_id:
            item["analysis_id"] = evaluation_id
        if case.get("seed_id"):
            item["seed_id"] = case["seed_id"]
        results.append(item)

    payload: Dict[str, Any] = {
        "schema_version": RESULTS_SCHEMA,
        "evaluation_id": evaluation_id,
        "apply_feedback": True,
        "results": results,
        "executor_meta": {
            "name": "rag_poison_platform.agenteval_executor",
            "run_id": f"ae_exec_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
            "case_count": len(results),
        },
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentEVAL execution_bundle runner")
    parser.add_argument("--bundle", required=True, help="path to execution_bundle.json (or evaluations POST response)")
    parser.add_argument(
        "--out",
        default="",
        help="output results.json path (default: results/agenteval_results_<id>.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="schema walk only, no real attack")
    parser.add_argument("--post", default="", help="AgentEVAL API base, e.g. http://127.0.0.1:8000")
    parser.add_argument("--api-token", default="", help="optional X-API-Key")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.is_file():
        raise SystemExit(f"bundle not found: {bundle_path}")

    bundle = load_bundle(bundle_path)
    payload = execute_bundle(bundle, dry_run=args.dry_run)

    eval_id = payload.get("evaluation_id") or "unknown"
    out_path = Path(args.out) if args.out else (PLATFORM_ROOT / "results" / f"agenteval_results_{eval_id}.json")
    write_results(out_path, payload)
    print(f"[ok] wrote {len(payload['results'])} results -> {out_path}")

    if args.post:
        if not eval_id or eval_id == "unknown":
            raise SystemExit("cannot POST: missing evaluation_id in bundle")
        resp = post_results(args.post, eval_id, payload, api_token=args.api_token)
        print(f"[post] ok={resp['ok']} status={resp['status_code']}")
        print(resp["body"][:2000])


if __name__ == "__main__":
    main()
