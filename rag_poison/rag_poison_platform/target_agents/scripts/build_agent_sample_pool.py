"""Build heterogeneous agent sample pool (external + local variants) for poison screening."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    load_registry,
    repo_path,
    write_csv,
    now_iso,
)
from target_agents.local_variants.registry import build_local_variants  # noqa: E402
from utils.deepseek_env import classify_api_dependency, deepseek_available  # noqa: E402

POOL_CSV = RESULTS_DIR / "agent_sample_pool.csv"
SUMMARY_JSON = RESULTS_DIR / "agent_sample_pool_summary.json"

CSV_FIELDS = [
    "agent_id",
    "sample_type",
    "local_variant",
    "model_backend",
    "repo_url",
    "api_base_url",
    "clone_success",
    "install_success",
    "startup_success",
    "http_api_success",
    "rag_capable",
    "poison_test_supported",
    "poison_tested",
    "external_service_missing",
    "status",
    "default_retriever_profile",
    "notes",
]

MIN_POOL_SIZE = 20
MIN_POISON_SUPPORTED = 20


def _external_row(agent: Dict[str, Any]) -> Dict[str, Any]:
    aid = agent["id"]
    repo = repo_path(aid)
    install_ok = bool(agent.get("install_success"))
    status, sample_type, ext_missing = classify_api_dependency(
        aid, repo, install_success=install_ok
    )
    if agent.get("external_service_missing"):
        ext_missing = True
        sample_type = "api_dependent_agent"
        status = agent.get("status") or "external_service_missing"
    elif agent.get("sample_type"):
        sample_type = agent["sample_type"]
    elif install_ok and not ext_missing:
        sample_type = "external_github_agent"

    poison_ok = bool(
        sample_type == "external_github_agent"
        and agent.get("rag_capable")
        and agent.get("http_api_success")
        and not ext_missing
        and not agent.get("install_skipped")
    )

    return {
        "agent_id": aid,
        "sample_type": sample_type,
        "local_variant": False,
        "model_backend": "deepseek" if agent.get("requires_llm_key") else "",
        "repo_url": agent.get("repo_url", ""),
        "api_base_url": agent.get("api_base_url", ""),
        "clone_success": agent.get("clone_success", False),
        "install_success": install_ok,
        "startup_success": agent.get("startup_success", False),
        "http_api_success": agent.get("http_api_success", False),
        "rag_capable": agent.get("rag_capable", False),
        "poison_test_supported": poison_ok,
        "poison_tested": agent.get("poison_tested", False),
        "external_service_missing": ext_missing,
        "status": status or agent.get("status", ""),
        "default_retriever_profile": "",
        "notes": agent.get("api_dependency_notes") or agent.get("notes", ""),
    }


def _local_row(variant: Dict[str, Any]) -> Dict[str, Any]:
    backend = variant["model_backend"]
    if backend == "deepseek" and not deepseek_available():
        backend = "mock"
    return {
        "agent_id": variant["agent_id"],
        "sample_type": "local_variant",
        "local_variant": True,
        "model_backend": backend,
        "repo_url": variant["repo_url"],
        "api_base_url": variant["api_base_url"],
        "clone_success": True,
        "install_success": True,
        "startup_success": False,
        "http_api_success": True,
        "rag_capable": True,
        "poison_test_supported": True,
        "poison_tested": False,
        "external_service_missing": False,
        "status": "local_variant_ready",
        "default_retriever_profile": variant.get("default_retriever_profile", ""),
        "notes": variant.get("notes", ""),
    }


def main() -> None:
    reg = load_registry()
    rows: List[Dict[str, Any]] = []

    for agent in reg.get("agents", []):
        if agent.get("local_variant"):
            continue
        rows.append(_external_row(agent))

    for variant in build_local_variants(include_deepseek=deepseek_available()):
        rows.append(_local_row(variant))

    total = len(rows)
    poison_supported = sum(1 for r in rows if r.get("poison_test_supported"))
    by_type: Dict[str, int] = {}
    for r in rows:
        t = r.get("sample_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    pool_complete = total >= MIN_POOL_SIZE and poison_supported >= MIN_POISON_SUPPORTED

    summary = {
        "generated_at": now_iso(),
        "total_samples": total,
        "poison_test_supported_count": poison_supported,
        "by_sample_type": by_type,
        "pool_complete": pool_complete,
        "min_pool_size": MIN_POOL_SIZE,
        "min_poison_supported": MIN_POISON_SUPPORTED,
        "deepseek_available": deepseek_available(),
        "completion_blockers": [],
    }
    if total < MIN_POOL_SIZE:
        summary["completion_blockers"].append(f"total_samples {total} < {MIN_POOL_SIZE}")
    if poison_supported < MIN_POISON_SUPPORTED:
        summary["completion_blockers"].append(
            f"poison_test_supported {poison_supported} < {MIN_POISON_SUPPORTED}"
        )
    if not deepseek_available():
        summary["completion_blockers"].append("DEEPSEEK_API_KEY not set; deepseek variants use mock")

    write_csv(POOL_CSV, rows, fieldnames=CSV_FIELDS)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("--- agent sample pool ---")
    print(f"total_samples: {total}")
    print(f"poison_test_supported: {poison_supported}")
    print(f"by_type: {by_type}")
    print(f"pool_complete: {pool_complete}")
    print(f"CSV -> {POOL_CSV}")
    print(f"Summary -> {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
