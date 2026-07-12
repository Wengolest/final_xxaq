#!/usr/bin/env python3
"""快速冒烟：pydantic-ai 原生 runner + base_exfil + 真实 API。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.agent_runners.native.pydantic_ai_runner import run_pydantic_ai_case
from src.attacks.samples import collect_all_samples


def main() -> None:
    case = next(c for c in collect_all_samples() if c.id == "base_exfil")
    payload = case.to_payload()
    print("Running smoke: base_exfil + pydantic-ai native MCPToolset ...")
    result = run_pydantic_ai_case(payload, sanitized=False)
    print("invoke_path:", result.get("invoke_path"))
    print("attack_success:", result.get("attack_success"))
    print("tool_calls:", result.get("tool_calls"))
    print("audit_log:", result.get("audit_log"))
    print("error:", result.get("error_message"))
    if result.get("agent_error"):
        sys.exit(1)
    print("SMOKE OK")


if __name__ == "__main__":
    main()
