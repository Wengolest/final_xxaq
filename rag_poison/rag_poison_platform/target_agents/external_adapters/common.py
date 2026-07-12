"""Load and probe external agent adapter YAML configs."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from utils.deepseek_env import merge_process_env, write_agent_env_file

ADAPTER_DIR = Path(__file__).resolve().parent
BULK_ROOT = Path(r"D:\AI\target_agents_bulk")


def list_adapter_configs() -> List[Path]:
    return sorted(ADAPTER_DIR.glob("*.yaml"))


def load_adapter_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_all_adapters() -> List[Dict[str, Any]]:
    out = []
    for p in list_adapter_configs():
        if p.name.startswith("_"):
            continue
        cfg = load_adapter_config(p)
        cfg["_config_path"] = str(p)
        out.append(cfg)
    return out


def _http(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 8,
) -> Tuple[bool, int, str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            return True, resp.getcode(), body
    except urllib.error.HTTPError as e:
        return False, e.code, e.read(2000).decode("utf-8", errors="replace")
    except Exception as e:
        return False, 0, str(e)


def probe_health(base_url: str, health_endpoint: str) -> Tuple[bool, str]:
    ep = health_endpoint or "/health"
    if not ep.startswith("/"):
        ep = f"/{ep}"
    for path in (ep, "/docs", "/openapi.json"):
        ok, code, _ = _http("GET", f"{base_url.rstrip('/')}{path}")
        if ok or code in (200, 404):
            return True, path
    return False, ""


def probe_post_endpoint(
    base_url: str,
    endpoint: str,
    sample: Dict[str, Any],
    *,
    query_param: Optional[str] = None,
    query_value: str = "hello",
) -> Tuple[bool, str]:
    if not endpoint:
        return False, "no_endpoint"
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    url = f"{base_url.rstrip('/')}{endpoint}"
    if query_param:
        from urllib.parse import quote

        url = f"{url}?{query_param}={quote(query_value)}"
        ok, code, body = _http("POST", url, None, timeout=15)
    else:
        ok, code, body = _http("POST", url, sample, timeout=15)
    if ok or code in (200, 201, 422):
        return True, body[:200]
    return False, f"code={code}"


def _resolve_repo(cfg: Dict[str, Any]) -> Path:
    for key in ("repo_path", "local_path"):
        alt = cfg.get(key, "")
        if alt and Path(alt).is_dir():
            return Path(alt)
    agent_id = cfg.get("agent_id", "")
    return BULK_ROOT / agent_id / "repo"


def try_start_agent(cfg: Dict[str, Any], *, timeout_sec: int = 12) -> Tuple[bool, str, Optional[int]]:
    """Attempt subprocess start; return started, notes, pid."""
    start_cmd = cfg.get("start_command") or ""
    if not start_cmd:
        return False, "no_start_command", None
    repo = _resolve_repo(cfg)
    if not repo.is_dir():
        return False, "repo_missing", None

    agent_id = cfg.get("agent_id", "")
    write_agent_env_file(BULK_ROOT / agent_id, use_deepseek=True)
    env = merge_process_env(backend="deepseek")
    try:
        proc = subprocess.Popen(
            start_cmd,
            cwd=str(repo),
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(timeout_sec)
        base = cfg.get("base_url", "")
        if base and probe_health(base, cfg.get("health_endpoint", "/health"))[0]:
            return True, "started_and_healthy", proc.pid
        if proc.poll() is None:
            return True, "started_process_alive", proc.pid
        return False, "process_exited_early", proc.pid
    except Exception as e:
        return False, f"{type(e).__name__}", None
