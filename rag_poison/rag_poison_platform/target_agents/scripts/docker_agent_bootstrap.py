"""Bootstrap Docker-backed GitHub RAG agents with structured logging."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
OVERRIDES = SCRIPT_DIR / "docker_overrides"
LOG_PATH = PLATFORM_ROOT / "results" / "docker_agent_deploy_log.md"
LOG_JSON = PLATFORM_ROOT / "results" / "docker_agent_deploy_state.json"

AGENTS = [
    {
        "id": "rag-fastapi-chatbot",
        "repo": Path(r"D:\AI\target_agents_bulk\rag-fastapi-chatbot\repo"),
        "compose": "docker-compose.yml",
        "compose_cwd": None,
        "override": "rag-fastapi-poison.compose.yml",
        "project": "poison_ragfastapi",
        "services": ["db", "redis", "minio", "ollama", "backend"],
        "health_urls": ["http://127.0.0.1:19051/docs", "http://127.0.0.1:19051/openapi.json"],
        "notes": "Full stack; backend uses Ollama ChatOllama",
    },
    {
        "id": "tech-trends-chatbot",
        "repo": Path(r"D:\AI\target_agents_bulk\tech-trends-chatbot\repo"),
        "compose": "docker-compose.yml",
        "compose_cwd": "backend",
        "override": "tech-trends-poison.compose.yml",
        "project": "poison_techtrends",
        "services": ["redis"],
        "health_urls": [],
        "api_start": {
            "venv": Path(r"D:\AI\target_agents_bulk\tech-trends-chatbot\.venv\Scripts\python.exe"),
            "cwd": Path(r"D:\AI\target_agents_bulk\tech-trends-chatbot\repo\backend"),
            "cmd": ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            "health": "http://127.0.0.1:8000/health",
            "env_extra": {"REDIS_HOST": "127.0.0.1", "REDIS_PORT": "6380"},
        },
        "notes": "Redis via compose; FastAPI via host uvicorn",
    },
    {
        "id": "enterprise-rag-chatbot",
        "repo": Path(r"D:\AI\target_agents_bulk\enterprise-rag-chatbot\repo"),
        "compose": "docker-compose.yml",
        "compose_cwd": "deploy/compose",
        "override": None,
        "project": "poison_enterprise",
        "services": ["rag_db", "weaviate"],
        "health_urls": ["http://127.0.0.1:8080/v1/.well-known/ready"],
        "notes": "Minimal deps only (rag_db+weaviate); app container needs zep+langfuse",
    },
    {
        "id": "rag-template",
        "repo": Path(r"D:\AI\target_agents_bulk\rag-template\repo"),
        "compose": None,
        "compose_cwd": None,
        "override": None,
        "project": "poison_ragtemplate",
        "services": ["qdrant_standalone"],
        "health_urls": ["http://127.0.0.1:6333/"],
        "qdrant_run": True,
        "notes": "No docker-compose; Tilt/k3d only. Standalone qdrant for vector DB.",
    },
]


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> Tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout, shell=False
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, str(exc)


def _http_probe(url: str, timeout: int = 5) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(500).decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.getcode(), "latency_ms": int((time.monotonic() - t0) * 1000), "body": body[:200]}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.read(300).decode("utf-8", errors="replace")[:200]}
    except Exception as exc:
        return {"ok": False, "status": 0, "error": str(exc)}


def _docker_ps() -> str:
    _, out = _run(["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
    return out


def _compose_ps(cwd: Path, compose_file: str, project: str) -> str:
    rc, out = _run(
        ["docker", "compose", "-p", project, "-f", compose_file, "ps", "-a"],
        cwd=cwd,
        timeout=60,
    )
    return out if rc == 0 else f"compose ps failed rc={rc}: {out[-1500:]}"


def _container_logs(names: List[str], tail: int = 40) -> Dict[str, str]:
    logs: Dict[str, str] = {}
    for name in names:
        rc, out = _run(["docker", "logs", "--tail", str(tail), name], timeout=30)
        logs[name] = out[-2000:] if rc == 0 else f"log_error: {out[-500:]}"
    return logs


def _sync_env(agent_repo: Path, agent_id: str) -> None:
    ps1 = SCRIPT_DIR / "deploy_helpers.ps1"
    if ps1.is_file():
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-AgentDir", str(agent_repo), "-AgentId", agent_id],
            capture_output=True,
            timeout=30,
        )


def _write_env_from_platform(cwd: Path, extra: Optional[Dict[str, str]] = None) -> None:
    from utils.deepseek_env import build_compat_env_map, load_deepseek_env

    compat = build_compat_env_map(load_deepseek_env())
    lines = ["# poison-test env"]
    for k, v in compat.items():
        if v and k in ("OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "LLM_MODEL", "MODEL"):
            lines.append(f"{k}={v}")
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}={v}")
    (cwd / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def bootstrap_agent(spec: Dict[str, Any]) -> Dict[str, Any]:
    aid = spec["id"]
    repo: Path = spec["repo"]
    result: Dict[str, Any] = {
        "agent_id": aid,
        "started_at": datetime.now().isoformat(),
        "repo": str(repo),
        "compose_file": None,
        "compose_cwd": None,
        "project": spec.get("project"),
        "services_requested": spec.get("services", []),
        "container_names": [],
        "exposed_ports": [],
        "compose_up_rc": None,
        "compose_up_log": "",
        "compose_ps": "",
        "docker_ps_after": "",
        "container_logs": {},
        "health_probes": {},
        "api_probe": {},
        "ok": False,
        "stage": "init",
        "notes": spec.get("notes", ""),
    }

    files_found = {
        "docker-compose.yml": (repo / "docker-compose.yml").is_file(),
        "compose.yaml": (repo / "compose.yaml").is_file(),
        ".env.example": (repo / ".env.example").is_file(),
        "README.md": (repo / "README.md").is_file(),
    }
    if spec.get("compose_cwd"):
        sub = repo / spec["compose_cwd"]
        files_found[f"{spec['compose_cwd']}/docker-compose.yml"] = (sub / "docker-compose.yml").is_file()
        files_found[f"{spec['compose_cwd']}/.env.example"] = (sub / ".env.example").is_file()
    result["files_found"] = files_found

    if spec.get("qdrant_run"):
        result["stage"] = "qdrant_standalone"
        rc, out = _run(
            [
                "docker", "run", "-d", "--name", "poison_qdrant_ragtemplate",
                "-p", "6333:6333", "-p", "6334:6334",
                "qdrant/qdrant:latest",
            ],
            timeout=120,
        )
        result["compose_up_rc"] = rc
        result["compose_up_log"] = out[-2000:]
        result["container_names"] = ["poison_qdrant_ragtemplate"]
        time.sleep(3)
        for url in spec.get("health_urls", []):
            result["health_probes"][url] = _http_probe(url)
        result["docker_ps_after"] = _docker_ps()
        result["container_logs"] = _container_logs(result["container_names"])
        result["ok"] = any(p.get("ok") for p in result["health_probes"].values())
        result["stage"] = "qdrant_ok" if result["ok"] else "qdrant_health_fail"
        return result

    if not spec.get("compose"):
        result["stage"] = "no_compose"
        result["ok"] = False
        return result

    cwd = repo / spec["compose_cwd"] if spec.get("compose_cwd") else repo
    compose_file = spec["compose"]
    override = spec.get("override")
    project = spec["project"]

    result["compose_file"] = str(cwd / compose_file)
    result["compose_cwd"] = str(cwd)

    _sync_env(repo, aid)
    if aid == "tech-trends-chatbot":
        _sync_env(repo, aid)
        _run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT_DIR / "deploy_helpers.ps1"),
                "-AgentDir",
                str(cwd),
                "-AgentId",
                aid,
            ],
            timeout=60,
        )
    elif aid == "rag-fastapi-chatbot":
        ex = repo / ".env.example"
        if ex.is_file():
            text = ex.read_text(encoding="utf-8")
            for old, new in {
                "username": "poison_test",
                "yourpassword": "poison_test_pass",
                "your-secret-key": "poison_test_secret",
                "your-salt": "poison_test_salt",
                "your-algorithm": "HS256",
                "your-email": "poison@test.local",
                "your-model from huggingface": "sentence-transformers/all-MiniLM-L6-v2",
                "your-model from ollama": "deepseek-chat",
                "huggingface token": "hf_poison_test",
                "your-domain": "localhost",
            }.items():
                text = text.replace(old, new)
            text += "\nPOSTGRES_USER=poison_test\nPOSTGRES_PASSWORD=poison_test_pass\nPOSTGRES_DB=poison_test_db\n"
            text += "OLLAMA_HOST=http://ollama:11434\nREDIS_URL=redis://redis:6379\n"
            text += "BROKER_URL=redis://redis:6379/0\nBACKEND_URL=redis://redis:6379/1\n"
            from utils.deepseek_env import build_compat_env_map, load_deepseek_env
            for k, v in build_compat_env_map(load_deepseek_env()).items():
                if v:
                    text += f"{k}={v}\n"
            (repo / ".env").write_text(text, encoding="utf-8")
    elif aid == "enterprise-rag-chatbot":
        compose_dir = repo / "deploy" / "compose"
        ex = compose_dir / ".env.example"
        if ex.is_file():
            (compose_dir / ".env").write_text(ex.read_text(encoding="utf-8"), encoding="utf-8")

    compose_cmd = ["docker", "compose", "-p", project, "-f", compose_file]
    if override:
        compose_cmd.extend(["-f", str(OVERRIDES / override)])
    compose_cmd.extend(["up", "-d", *spec.get("services", [])])

    result["stage"] = "compose_up"
    rc, log = _run(compose_cmd, cwd=cwd, timeout=600)
    result["compose_up_rc"] = rc
    result["compose_up_log"] = log[-4000:]
    time.sleep(8)

    result["compose_ps"] = _compose_ps(cwd, compose_file if not override else compose_file, project)
    if override:
        result["compose_ps"] = _compose_ps(cwd, compose_file, project)
        # re-run with both files for ps
        rc_ps, ps_out = _run(
            ["docker", "compose", "-p", project, "-f", compose_file, "-f", str(OVERRIDES / override), "ps", "-a"],
            cwd=cwd,
        )
        result["compose_ps"] = ps_out if rc_ps == 0 else result["compose_ps"]

    result["docker_ps_after"] = _docker_ps()

    # Parse container names from docker ps filtered by project prefix
    rc_j, ps_json = _run(["docker", "ps", "-a", "--format", "{{.Names}}"], timeout=30)
    if rc_j == 0:
        prefix = project
        result["container_names"] = [n.strip() for n in ps_json.splitlines() if prefix in n.strip().lower() or aid.split("-")[0] in n.lower()]
    if not result["container_names"]:
        rc_j2, ps_json2 = _run(
            ["docker", "compose", "-p", project, "-f", compose_file, "ps", "--format", "json"],
            cwd=cwd,
            timeout=30,
        )
        if rc_j2 == 0 and ps_json2.strip():
            try:
                for line in ps_json2.strip().splitlines():
                    obj = json.loads(line)
                    result["container_names"].append(obj.get("Name") or obj.get("Names", ""))
                    ports = obj.get("Publishers") or obj.get("Ports") or ""
                    if ports:
                        result["exposed_ports"].append(str(ports))
            except json.JSONDecodeError:
                pass

    result["container_logs"] = _container_logs(result["container_names"][:6])

    for url in spec.get("health_urls", []):
        result["health_probes"][url] = _http_probe(url)

    api = spec.get("api_start")
    if api and api.get("venv") and Path(api["venv"]).is_file():
        result["stage"] = "api_uvicorn_start"
        import os

        env = os.environ.copy()
        env.update(api.get("env_extra") or {})
        subprocess.Popen(
            [str(api["venv"]), *api["cmd"]],
            cwd=str(api["cwd"]),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(10)
        result["api_probe"][api["health"]] = _http_probe(api["health"])

    health_ok = any(p.get("ok") for p in result["health_probes"].values())
    api_ok = any(p.get("ok") for p in result.get("api_probe", {}).values())
    result["ok"] = (rc == 0) and (health_ok or api_ok)
    result["stage"] = "health_ok" if result["ok"] else "health_or_compose_fail"
    return result


def append_markdown(sections: List[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = not LOG_PATH.is_file()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        if header:
            f.write(f"# Docker Agent Deploy Log\n\nGenerated: {datetime.now().isoformat()}\n\n")
        for sec in sections:
            f.write(sec)
            if not sec.endswith("\n"):
                f.write("\n")
            f.write("\n")


def main() -> None:
    sys.path.insert(0, str(PLATFORM_ROOT))
    baseline_ps = _docker_ps()
    _, compose_ver = _run(["docker", "compose", "version"])

    append_markdown([
        f"## Baseline — {datetime.now().isoformat()}",
        "### docker compose version",
        "```",
        compose_ver.strip(),
        "```",
        "### docker ps -a (before agent bootstrap)",
        "```",
        baseline_ps.strip(),
        "```",
    ])

    state: Dict[str, Any] = {"baseline_ps": baseline_ps, "agents": [], "updated_at": datetime.now().isoformat()}
    if LOG_JSON.is_file():
        try:
            state = json.loads(LOG_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    for spec in AGENTS:
        print(f"[docker-bootstrap] {spec['id']} ...", flush=True)
        res = bootstrap_agent(spec)
        state.setdefault("agents", []).append(res)
        state["updated_at"] = datetime.now().isoformat()
        LOG_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        md = [
            f"## Agent: {res['agent_id']} — {datetime.now().isoformat()}",
            f"- **stage**: {res.get('stage')}",
            f"- **ok**: {res.get('ok')}",
            f"- **notes**: {res.get('notes')}",
            f"- **compose_file**: `{res.get('compose_file')}`",
            f"- **compose_cwd**: `{res.get('compose_cwd')}`",
            f"- **project**: `{res.get('project')}`",
            f"- **services_requested**: {res.get('services_requested')}",
            f"- **container_names**: {res.get('container_names')}",
            "### files_found",
            "```json",
            json.dumps(res.get("files_found", {}), ensure_ascii=False, indent=2),
            "```",
            f"### compose up (rc={res.get('compose_up_rc')})",
            "```",
            (res.get("compose_up_log") or "")[-3500:],
            "```",
            "### compose ps",
            "```",
            (res.get("compose_ps") or "")[-2500:],
            "```",
            "### docker ps (after)",
            "```",
            (res.get("docker_ps_after") or "")[-2500:],
            "```",
            "### health probes",
            "```json",
            json.dumps(res.get("health_probes", {}), ensure_ascii=False, indent=2),
            "```",
            "### api probes",
            "```json",
            json.dumps(res.get("api_probe", {}), ensure_ascii=False, indent=2),
            "```",
            "### container logs (tail)",
        ]
        for name, log in (res.get("container_logs") or {}).items():
            md.extend([f"#### {name}", "```", log[-1800:], "```"])
        append_markdown(md)
        print(json.dumps({"agent": res["agent_id"], "ok": res["ok"], "stage": res["stage"]}, ensure_ascii=False))

    append_markdown([f"## Bootstrap complete — {datetime.now().isoformat()}"])
    print(f"Wrote {LOG_PATH}")
    print(f"Wrote {LOG_JSON}")


if __name__ == "__main__":
    main()
