"""Start local RAG variant servers (minimal_http_rag_agent on distinct ports)."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.local_variants.registry import build_local_variants  # noqa: E402
from utils.deepseek_env import deepseek_available, merge_process_env, write_agent_env_file  # noqa: E402

MINIMAL_RAG_DIR = PLATFORM_ROOT / "minimal_http_rag_agent"
VENV_PY = MINIMAL_RAG_DIR / ".venv" / "Scripts" / "python.exe"
VENV_UVICORN = MINIMAL_RAG_DIR / ".venv" / "Scripts" / "uvicorn.exe"
PID_DIR = PLATFORM_ROOT / "target_agents" / "local_variants" / "pids"


def _health(url: str, timeout: int = 4) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _start_variant(variant: Dict[str, Any], *, force: bool) -> Dict[str, Any]:
    port = variant["assigned_port"]
    url = variant["api_base_url"]
    backend = variant["model_backend"]
    aid = variant["agent_id"]
    pid_file = PID_DIR / f"{aid}.pid"

    if not force and pid_file.is_file() and _health(url):
        return {"agent_id": aid, "started": True, "skip": "already_running", "port": port}

    if not VENV_UVICORN.is_file():
        subprocess.run(
            [sys.executable, "-m", "venv", str(MINIMAL_RAG_DIR / ".venv")],
            check=False,
        )
        subprocess.run(
            [str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(MINIMAL_RAG_DIR / "requirements.txt")],
            check=False,
        )

    env = merge_process_env(backend=backend)
    env["PYTHONPATH"] = str(MINIMAL_RAG_DIR)
    env["DEFAULT_RETRIEVER_PROFILE"] = variant.get("default_retriever_profile", "tfidf_top5")
    env["MODEL_BACKEND"] = backend
    env["LOCAL_VARIANT_ID"] = aid

    proc = subprocess.Popen(
        [str(VENV_UVICORN), "app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(MINIMAL_RAG_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    time.sleep(3)
    ok = _health(url)
    return {
        "agent_id": aid,
        "started": ok,
        "port": port,
        "model_backend": backend,
        "pid": proc.pid,
        "health_ok": ok,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start local RAG variant servers")
    p.add_argument("--max-variants", type=int, default=None, help="Limit variants started")
    p.add_argument("--only", type=str, default=None, help="Single variant agent_id")
    p.add_argument("--force", action="store_true", help="Restart even if health OK")
    p.add_argument("--check-only", action="store_true", help="Health check only, no start")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    include_ds = deepseek_available()
    variants = build_local_variants(include_deepseek=include_ds)
    if args.only:
        variants = [v for v in variants if v["agent_id"] == args.only]
    if args.max_variants is not None:
        variants = variants[: max(0, args.max_variants)]

    write_agent_env_file(PLATFORM_ROOT / "target_agents" / "local_variants", use_deepseek=include_ds)

    rows: List[Dict[str, Any]] = []
    for v in variants:
        if args.check_only:
            ok = _health(v["api_base_url"])
            rows.append({"agent_id": v["agent_id"], "health_ok": ok, "port": v["assigned_port"]})
            print(f"[variant] {v['agent_id']} health={ok}")
            continue
        row = _start_variant(v, force=args.force)
        rows.append(row)
        print(f"[variant] {v['agent_id']} started={row.get('started')} backend={v['model_backend']}")

    up = sum(1 for r in rows if r.get("health_ok") or r.get("started"))
    print(f"Local variants up: {up}/{len(rows)} deepseek_enabled={include_ds}")


if __name__ == "__main__":
    main()
