"""Level 1d: Try start services and probe HTTP endpoints."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    agent_root,
    apply_api_dependency_fields,
    load_registry,
    logs_path,
    repo_path,
    run_cmd,
    save_registry,
    venv_path,
    write_csv,
    write_log,
    now_iso,
)
from utils.deepseek_env import merge_process_env, write_agent_env_file  # noqa: E402

START_VARIANTS = [
    ["uvicorn", "app:app"],
    ["uvicorn", "main:app"],
    ["uvicorn", "app.main:app"],
    ["uvicorn", "src.main:app"],
    ["uvicorn", "api.main:app"],
    ["uvicorn", "server:app"],
]


def _http_get(url: str, timeout: int = 5) -> Tuple[bool, int, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            return True, resp.getcode(), body
    except urllib.error.HTTPError as e:
        return False, e.code, e.read(2000).decode("utf-8", errors="replace")
    except Exception as e:
        return False, 0, str(e)


def _parse_openapi(body: str) -> List[str]:
    try:
        data = json.loads(body)
        return list((data.get("paths") or {}).keys())
    except Exception:
        return []


def _py(vp: Path) -> str:
    return str(vp / "Scripts" / "python.exe")


def main() -> None:
    reg = load_registry()
    rows = []
    for a in reg.get("agents", []):
        aid = a["id"]
        if a.get("install_skipped") or not a.get("install_success"):
            rows.append(
                {
                    "agent_id": aid,
                    "startup_success": False,
                    "skip": a.get("skip_reason") or "no_install",
                }
            )
            continue

        apply_api_dependency_fields(a, repo_path(aid))
        if a.get("external_service_missing") or a.get("status") in (
            "external_service_missing",
            "install_success_but_external_service_missing",
        ):
            a.update(
                {
                    "startup_success": False,
                    "http_api_success": False,
                    "poison_test_supported": False,
                    "sample_type": "api_dependent_agent",
                    "status": a.get("status") or "external_service_missing",
                    "error_stage": "external_api",
                    "error_summary": a.get("api_dependency_notes") or "missing non-DeepSeek API keys",
                    "tested_at": now_iso(),
                }
            )
            rows.append(
                {
                    "agent_id": aid,
                    "startup_success": False,
                    "skip": a.get("status"),
                }
            )
            print(f"[start] {aid} SKIP external_service_missing")
            continue

        write_agent_env_file(agent_root(aid), use_deepseek=True)

        port = a.get("assigned_port") or 19001
        base = f"http://127.0.0.1:{port}"
        vp = venv_path(aid)
        repo = repo_path(aid)
        uvicorn = str(vp / "Scripts" / "uvicorn.exe")
        logs: List[str] = []
        started = False
        used_cmd: List[str] = []

        for variant in START_VARIANTS:
            cmd = [uvicorn, *variant[1:], "--host", "127.0.0.1", "--port", str(port)]
            proc = None
            try:
                import subprocess

                proc = subprocess.Popen(
                    cmd,
                    cwd=str(repo),
                    env=merge_process_env(backend="deepseek"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                time.sleep(6)
                ok, code, _ = _http_get(f"{base}/docs", timeout=4)
                if not ok:
                    ok, code, _ = _http_get(f"{base}/health", timeout=4)
                if not ok:
                    ok, code, body = _http_get(f"{base}/openapi.json", timeout=4)
                else:
                    body = ""
                if ok or code in (200, 404, 405):
                    started = True
                    used_cmd = cmd
                    logs.append(f"START OK: {' '.join(cmd)} code={code}")
                    if proc and proc.poll() is None:
                        (logs_path(aid) / "startup.pid").write_text(str(proc.pid))
                    break
            except Exception as exc:
                logs.append(f"start err: {exc}")
            finally:
                if not started and proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                elif not started and proc:
                    logs.append(proc.stderr.read() if proc.stderr else "")

        http_ok = False
        endpoints_found: List[str] = []
        if started:
            for ep in ["/docs", "/openapi.json", "/health", "/query", "/chat", "/invoke"]:
                ok, code, body = _http_get(f"{base}{ep}", timeout=5)
                logs.append(f"probe {ep}: ok={ok} code={code}")
                if ok or code == 200:
                    http_ok = True
                    endpoints_found.append(ep)
            ok, _, body = _http_get(f"{base}/openapi.json", timeout=5)
            if ok:
                paths = _parse_openapi(body)
                logs.append(f"openapi paths: {paths[:20]}")
                for p in paths:
                    if "query" in p and not a.get("query_endpoint"):
                        a["query_endpoint"] = p
                    if "chat" in p and not a.get("chat_endpoint"):
                        a["chat_endpoint"] = p
                    if any(x in p for x in ("ingest", "upload", "document")):
                        a["ingest_endpoint"] = p

        write_log(aid, "startup.log", "\n".join(logs))
        write_log(aid, "probe.log", "\n".join(logs))

        if http_ok and not a.get("external_service_missing"):
            a["sample_type"] = "external_github_agent"
            a["poison_test_supported"] = bool(a.get("rag_capable"))

        a.update(
            {
                "startup_success": started,
                "http_api_success": http_ok,
                "api_base_url": base if http_ok else "",
                "status": "http_ok" if http_ok else ("running" if started else "startup_failed"),
                "error_stage": "" if started else "startup",
                "error_summary": "" if started else logs[-1][:400] if logs else "no_start",
                "deploy_commands": {
                    **a.get("deploy_commands", {}),
                    "start": " ".join(used_cmd) if used_cmd else "",
                },
                "tested_at": now_iso(),
            }
        )
        rows.append(
            {
                "agent_id": aid,
                "startup_success": started,
                "http_api_success": http_ok,
                "api_base_url": a.get("api_base_url"),
                "endpoints_found": "|".join(endpoints_found),
                "port": port,
            }
        )
        print(f"[start] {aid} started={started} http={http_ok}")

    save_registry(reg)
    write_csv(RESULTS_DIR / "bulk_agent_start_probe_report.csv", rows)
    print(
        f"Start/probe: startup={sum(1 for r in rows if r.get('startup_success'))} "
        f"http={sum(1 for r in rows if r.get('http_api_success'))}"
    )


if __name__ == "__main__":
    main()
