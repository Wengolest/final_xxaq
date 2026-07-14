#!/usr/bin/env python3
"""Run a single poison/defense module from registry.json."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(__file__).resolve().parent / "registry.json"


def load_registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def load_env() -> None:
    for env_path in [ROOT / ".env", ROOT / "MCP_test" / ".env", ROOT / "memory_poison" / ".env"]:
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            val = v.strip()
            if val and val != "your_key_here":
                os.environ.setdefault(k.strip(), val)


def run_cmd(cwd: Path, cmd: list[str], timeout: int | None = None, proxy: bool = False) -> int:
    print(f"\n>>> cwd={cwd}")
    print(f">>> {' '.join(cmd)}\n")
    env = os.environ.copy()
    if "prompt_poison" in str(cwd).replace("\\", "/"):
        env["PYTHONPATH"] = str(cwd) + os.pathsep + env.get("PYTHONPATH", "")

    # --proxy: 将所有 LLM 请求路由到 defense_proxy (:8200)
    if proxy:
        env["DEEPSEEK_BASE_URL"] = "http://localhost:8200/v1"
        env["DEEPSEEK_API_BASE"] = "http://localhost:8200"
        env["LLM_BASE_URL"] = "http://localhost:8200/v1"
        env["OPENAI_BASE_URL"] = "http://localhost:8200/v1"
        env["OPENAI_API_BASE"] = "http://localhost:8200/v1"
        print("[proxy] Routing through defense_proxy at http://localhost:8200")

    proc = subprocess.run(cmd, cwd=str(cwd), env=env, timeout=timeout)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one poison module")
    parser.add_argument("module", help="Module id from registry (e.g. multiagent, defense)")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--proxy", action="store_true", help="Route LLM calls through defense_proxy :8200")
    args = parser.parse_args()

    load_env()
    reg = load_registry()
    mod = reg["modules"].get(args.module)
    if not mod or not mod.get("enabled", True):
        print(f"Unknown or disabled module: {args.module}", file=sys.stderr)
        return 1

    mod_dir = (ROOT / mod["dir"]).resolve()
    if not mod_dir.is_dir():
        print(f"Module directory missing: {mod_dir}", file=sys.stderr)
        return 1

    cmd = mod.get("quick") or mod.get("full")
    if not cmd:
        print(f"No command configured for {args.module}", file=sys.stderr)
        return 1

    python = sys.executable
    if cmd[0] == "python":
        cmd = [python, *cmd[1:]]

    rc = run_cmd(mod_dir, cmd, timeout=args.timeout, proxy=args.proxy)
    if rc != 0:
        return rc

    if mod.get("result_glob"):
        matches = sorted(mod_dir.glob(mod["result_glob"]), key=lambda p: p.stat().st_mtime)
        if matches:
            print(f"\n[result] {matches[-1]}")
    elif mod.get("result_pointer"):
        ptr = mod_dir / mod["result_pointer"]
        if ptr.is_file():
            print(f"\n[result] {ptr}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
