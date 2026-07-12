"""Check DeepSeek-only API env; write results/agent_api_env_check.csv."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))

from target_agents.bulk_common import RESULTS_DIR, write_csv  # noqa: E402
from utils.env_bootstrap import deepseek_env_rows  # noqa: E402

CSV_FIELDS = ["key_name", "present", "masked_preview", "notes"]


def main() -> None:
    rows = deepseek_env_rows()
    out = RESULTS_DIR / "agent_api_env_check.csv"
    write_csv(out, rows, fieldnames=CSV_FIELDS)
    present = sum(1 for r in rows if r.get("present") == "true")
    print(f"[api_env] DeepSeek vars present: {present}/{len(rows)}")
    for r in rows:
        preview = r.get("masked_preview") or "(empty)"
        print(f"  {r['key_name']}: present={r['present']} preview={preview}")
    print(f"CSV -> {out}")


if __name__ == "__main__":
    main()
