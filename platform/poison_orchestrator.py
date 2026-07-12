"""Poison module orchestration helpers for defense_engine server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"
RUN_MODULE = Path(__file__).resolve().parent / "run_module.py"


def load_registry() -> dict[str, Any]:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def list_modules() -> list[dict[str, Any]]:
    reg = load_registry()
    api_ok = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))
    out = []
    for mid, mod in reg.get("modules", {}).items():
        out.append({
            "id": mid,
            "label": mod.get("label", mid),
            "dir": mod.get("dir"),
            "enabled": mod.get("enabled", True),
            "requires_api": mod.get("requires_api", False),
            "api_ready": api_ok or not mod.get("requires_api", False),
        })
    return out


def list_targets() -> list[dict[str, Any]]:
    reg = load_registry()
    return reg.get("targets", [])


def attacks_catalog() -> dict[str, Any]:
    reg = load_registry()
    families = []
    for mid, mod in reg.get("modules", {}).items():
        families.append({
            "family": mid,
            "label": mod.get("label", mid),
            "requires_api": mod.get("requires_api", False),
        })
    return {"families": families, "total": len(families)}


def run_module(module_id: str, timeout: int = 600) -> dict[str, Any]:
    reg = load_registry()
    mod = reg.get("modules", {}).get(module_id)
    if not mod:
        return {"ok": False, "error": f"Unknown module: {module_id}"}
    if mod.get("requires_api") and not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        return {"ok": False, "error": "DEEPSEEK_API_KEY or OPENAI_API_KEY required"}

    proc = subprocess.run(
        [sys.executable, str(RUN_MODULE), module_id],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )
    result_hint = None
    mod_dir = ROOT / mod["dir"]
    if mod.get("result_glob"):
        matches = sorted(mod_dir.glob(mod["result_glob"]), key=lambda p: p.stat().st_mtime)
        if matches:
            result_hint = str(matches[-1])
    elif mod.get("result_pointer"):
        ptr = mod_dir / mod["result_pointer"]
        if ptr.is_file():
            result_hint = str(ptr)

    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:] if proc.stdout else "",
        "stderr": proc.stderr[-2000:] if proc.stderr else "",
        "result_file": result_hint,
    }
