"""
原生 Agent 实验 worker：在 agents/{id}/venv 中运行，调用各框架自有 MCP 集成。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agent_runners.native.adapters import NATIVE_AGENTS, get_native_adapter  # noqa: E402


def main() -> None:
    """CLI：--agent 选择原生 runner，结果写入 --output JSON。"""
    p = argparse.ArgumentParser()
    p.add_argument("--agent", required=True, choices=list(NATIVE_AGENTS))
    p.add_argument("--payload", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--sanitized", action="store_true")
    args = p.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    fn = get_native_adapter(args.agent)
    try:
        result = fn(payload, sanitized=args.sanitized)
    except Exception:
        import traceback

        result = {
            "framework": args.agent,
            "invoke_path": "native_error",
            "attack_success": False,
            "agent_error": True,
            "error_message": traceback.format_exc()[-3000:],
            "refused": False,
            "ignored": False,
        }
    result["agent_framework"] = args.agent
    result["sample_id"] = payload.get("sample_id")
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
