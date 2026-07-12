"""Export local RAG variants to results/local_rag_variants.csv."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import RESULTS_DIR, write_csv  # noqa: E402
from target_agents.local_variants.registry import build_local_variants  # noqa: E402
from utils.deepseek_env import deepseek_available  # noqa: E402

FIELDS = [
    "agent_id",
    "sample_type",
    "local_variant",
    "model_backend",
    "default_retriever_profile",
    "api_base_url",
    "assigned_port",
    "poison_test_supported",
    "repo_url",
    "notes",
]


def main() -> None:
    rows = []
    for v in build_local_variants(include_deepseek=deepseek_available()):
        rows.append({k: v.get(k, "") for k in FIELDS})
        rows[-1]["sample_type"] = "local_variant"
        rows[-1]["local_variant"] = True
    out = RESULTS_DIR / "local_rag_variants.csv"
    write_csv(out, rows, fieldnames=FIELDS)
    print(f"Exported {len(rows)} local variants -> {out}")


if __name__ == "__main__":
    main()
