#!/usr/bin/env python3
"""Run quick evaluation across all poison modules (offline first, then API modules if key set)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(__file__).resolve().parent / "registry.json"
RUN_MODULE = Path(__file__).resolve().parent / "run_module.py"


def has_api_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-only", action="store_true", help="Skip modules that need LLM API")
    parser.add_argument("--modules", default="", help="Comma-separated module ids (default: all enabled)")
    parser.add_argument("--proxy", action="store_true", help="Route all LLM calls through defense_proxy :8200")
    args = parser.parse_args()

    with open(REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)

    selected = [m.strip() for m in args.modules.split(",") if m.strip()] or list(reg["modules"].keys())
    api_ok = has_api_key()
    print(f"Project root: {ROOT}")
    print(f"API key present: {api_ok}")
    print(f"Modules to run: {selected}\n")

    failed: list[str] = []
    for mid in selected:
        mod = reg["modules"].get(mid)
        if not mod or not mod.get("enabled", True):
            print(f"[SKIP] {mid}: not enabled")
            continue
        if args.offline_only and mod.get("requires_api"):
            print(f"[SKIP] {mid}: requires API (--offline-only)")
            continue
        if mod.get("requires_api") and not api_ok:
            print(f"[SKIP] {mid}: no DEEPSEEK_API_KEY / OPENAI_API_KEY")
            continue

        print("=" * 70)
        print(f"MODULE: {mid} — {mod.get('label', mid)}")
        print("=" * 70)
        cmd = [sys.executable, str(RUN_MODULE), mid]
        if args.proxy:
            cmd.append("--proxy")
        rc = subprocess.call(cmd)
        if rc != 0:
            failed.append(mid)
            print(f"[FAIL] {mid} exit={rc}")
        else:
            print(f"[OK] {mid}")

    print("\n" + "=" * 70)
    if failed:
        print(f"Failed modules: {', '.join(failed)}")
        return 1
    print("All selected modules completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
