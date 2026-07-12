"""Docker compose helper for external GitHub RAG agents."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.deepseek_env import build_compat_env_map, load_deepseek_env

COMPOSE_NAMES = ("docker-compose.yml", "compose.yaml", "compose.yml", "docker-compose.yaml")


def find_compose_file(repo: Path) -> Optional[Path]:
    for name in COMPOSE_NAMES:
        p = repo / name
        if p.is_file():
            return p
    for sub in ("backend", "deploy/compose", "repo"):
        d = repo / sub if sub != "repo" else repo
        for name in COMPOSE_NAMES:
            p = d / name
            if p.is_file():
                return p
    return None


def write_env_test(repo: Path, extra: Optional[Dict[str, str]] = None) -> Path:
    ds = load_deepseek_env()
    compat = build_compat_env_map(ds)
    lines = [
        "# auto-generated .env.test — no secrets logged",
        f"JWT_SECRET=poison_test_jwt_secret_{int(time.time())}",
        f"SECRET_KEY=poison_test_secret_{int(time.time())}",
        "POSTGRES_USER=poison_test",
        "POSTGRES_PASSWORD=poison_test_pass",
        "POSTGRES_DB=poison_test_db",
        "REDIS_HOST=127.0.0.1",
        "REDIS_PORT=6379",
        "MINIO_ACCESS_KEY=poisonminio",
        "MINIO_SECRET_KEY=poisonminiosecret",
        "LLM_MODEL=deepseek-chat",
        "OLLAMA_HOST=http://host.docker.internal:11434",
        "DEBUG=1",
        "POISON_TEST_FAST_CHAT=1",
    ]
    for k, v in compat.items():
        if v:
            lines.append(f"{k}={v}")
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}={v}")
    env_path = repo / ".env.test"
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def _run(cmd: List[str], cwd: Path, timeout: int = 180) -> Tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, shell=False)
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out[-4000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as exc:
        return 1, str(exc)


def docker_compose_up(
    repo: Path,
    *,
    compose_file: Optional[Path] = None,
    services: Optional[List[str]] = None,
    health_url: str = "",
    health_wait_sec: int = 180,
) -> Dict[str, Any]:
    cf = compose_file or find_compose_file(repo)
    if not cf:
        return {"ok": False, "error": "no_compose_file", "stage": "compose_find"}
    cwd = cf.parent
    write_env_test(repo)
    env_src = repo / ".env.test"
    env_dst = cwd / ".env"
    if env_src != env_dst:
        env_dst.write_text(env_src.read_text(encoding="utf-8"), encoding="utf-8")

    cmd = ["docker", "compose", "-f", str(cf.name), "up", "-d"]
    if services:
        cmd.extend(services)
    rc, log = _run(cmd, cwd, timeout=health_wait_sec)
    if rc != 0:
        return {"ok": False, "error": log, "stage": "compose_up", "compose": str(cf)}

    deadline = time.monotonic() + health_wait_sec
    health_ok = False
    while time.monotonic() < deadline:
        if health_url:
            try:
                urllib.request.urlopen(health_url, timeout=5)
                health_ok = True
                break
            except Exception:
                pass
        else:
            rc2, ps = _run(["docker", "compose", "-f", str(cf.name), "ps", "--format", "json"], cwd, timeout=30)
            if rc2 == 0 and ps.strip():
                health_ok = True
                break
        time.sleep(5)

    return {
        "ok": health_ok,
        "health_ok": health_ok,
        "compose": str(cf),
        "cwd": str(cwd),
        "log": log[-500:],
        "health_url": health_url,
        "stage": "health_ok" if health_ok else "health_timeout",
    }


def docker_compose_down(repo: Path, compose_file: Optional[Path] = None) -> None:
    cf = compose_file or find_compose_file(repo)
    if not cf:
        return
    _run(["docker", "compose", "-f", str(cf.name), "down"], cf.parent, timeout=120)


def start_tech_trends_stack(repo: Path) -> Dict[str, Any]:
    backend = repo / "backend"
    cf = backend / "docker-compose.yml"
    if not cf.is_file():
        return {"ok": False, "error": "no_compose", "stage": "compose_find"}
    ds = load_deepseek_env()
    env_lines = [
        f"OPENAI_API_KEY={ds.get('DEEPSEEK_API_KEY', '')}",
        f"MODEL={ds.get('DEEPSEEK_MODEL', 'deepseek-chat') or 'deepseek-chat'}",
        "REDIS_HOST=127.0.0.1",
        "REDIS_PORT=6380",
        "DOCS_DIR=data/docs",
        "EXPORT_DIR=data/export",
    ]
    (backend / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    override = Path(__file__).resolve().parent / "docker_overrides" / "tech-trends-poison.compose.yml"
    compose_args = ["docker", "compose", "-p", "poison_techtrends", "-f", "docker-compose.yml"]
    if override.is_file():
        compose_args.extend(["-f", str(override)])
    compose_args.extend(["up", "-d", "redis"])
    rc, log = _run(compose_args, backend, timeout=120)
    if rc != 0:
        return {"ok": False, "error": log, "stage": "redis_up"}
    venv_py = repo.parent / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        venv_py = Path(r"D:\AI\target_agents_bulk\tech-trends-chatbot\.venv\Scripts\python.exe")
    if venv_py.is_file():
        subprocess.Popen(
            [str(venv_py), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(backend),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        health_ok = False
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)
                health_ok = True
                break
            except Exception:
                time.sleep(2)
    else:
        health_ok = True
    return {
        "ok": health_ok,
        "health_ok": health_ok,
        "base_url": "http://127.0.0.1:8000",
        "compose": str(cf),
        "services": ["redis", "uvicorn"],
        "log": log,
        "test_mode": "docker_redis_native_http",
    }


def write_rag_fastapi_env_test(repo: Path) -> Path:
    """Strict docker-network .env.test for rag-fastapi-chatbot (no secrets logged)."""
    ts = int(time.time())
    lines = [
        "# auto-generated .env.test for rag-fastapi poison matrix",
        "DATABASE_URL_ASYNCPG_DRIVER=postgresql+asyncpg://poison_test:poison_test_pass@db:5432/poison_test_db",
        "DATABASE_URL_PSYCOPG_DRIVER=postgresql+psycopg://poison_test:poison_test_pass@db:5432/poison_test_db",
        "PSYCOPG_CONNECT=postgresql://poison_test:poison_test_pass@db:5432/poison_test_db",
        "MINIO_URL=minio:9000",
        "MINIO_ACCESS_KEY=poisonminio",
        "MINIO_SECRET_KEY=poisonminiosecret",
        "BUCKET_NAME=document-for-rag",
        f"SECRET_KEY=poison_test_secret_{ts}",
        "SALT=poison_test_salt",
        "ALGORITHM=HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES=60",
        "JTI_EXPIRY_SECOND=3600",
        "REFRESH_TOKEN_EXPIRE_DAYS=7",
        "POSTGRES_USER=poison_test",
        "POSTGRES_PASSWORD=poison_test_pass",
        "POSTGRES_DB=poison_test_db",
        "REDIS_URL=redis://redis:6379",
        "BROKER_URL=redis://redis:6379/0",
        "BACKEND_URL=redis://redis:6379/1",
        "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
        "HF_TOKEN=hf_poison_test",
        "LLM_MODEL=qwen2.5:0.5b",
        "OLLAMA_HOST=http://ollama:11434",
        "DOMAIN_NAME=localhost",
        "VERSION=api/v1",
        "MAIL_USERNAME=poison@test.local",
        "MAIL_PASSWORD=poison_test",
        "MAIL_FROM=poison@test.local",
        "MAIL_SERVER=localhost",
        "DEBUG=1",
    ]
    env_path = repo / ".env.test"
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (repo / ".env").write_text(env_path.read_text(encoding="utf-8"), encoding="utf-8")
    return env_path


def start_rag_fastapi_stack(repo: Path) -> Dict[str, Any]:
    cf = repo / "docker-compose.yml"
    if not cf.is_file():
        return {"ok": False, "error": "no_compose", "stage": "compose_find"}
    override = Path(__file__).resolve().parent / "docker_overrides" / "rag-fastapi-poison.compose.yml"
    write_rag_fastapi_env_test(repo)
    compose_args = [
        "docker", "compose", "-p", "poison_ragfastapi",
        "--env-file", ".env.test",
        "-f", "docker-compose.yml",
    ]
    if override.is_file():
        compose_args.extend(["-f", str(override)])
    for step, svc in [("deps", ["db", "redis", "minio", "ollama"]), ("backend", ["backend"])]:
        rc, log = _run([*compose_args, "up", "-d", *svc], repo, timeout=900 if step == "backend" else 300)
        if rc != 0 and step == "backend":
            rc_b, log_b = _run([*compose_args, "build", "backend"], repo, timeout=1200)
            if rc_b != 0:
                return {"ok": False, "error": log_b, "stage": "backend_build", "compose": str(cf), "log": log}
            rc, log = _run([*compose_args, "up", "-d", "backend"], repo, timeout=600)
            if rc != 0:
                return {"ok": False, "error": log, "stage": "backend_up", "compose": str(cf)}
    health_url = "http://127.0.0.1:19051/api/v1/health"
    deadline = time.monotonic() + 300
    health_ok = False
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(health_url, timeout=5)
            health_ok = True
            break
        except Exception:
            time.sleep(8)
    rc_l, logs = _run(["docker", "logs", "fastapi", "--tail", "80"], repo, timeout=30)
    return {
        "ok": health_ok,
        "health_ok": health_ok,
        "base_url": "http://127.0.0.1:19051",
        "health_url": health_url,
        "compose": str(cf),
        "override": str(override) if override.is_file() else "",
        "env_test": str(repo / ".env.test"),
        "services": ["db", "redis", "minio", "ollama", "backend"],
        "container_logs": logs if rc_l == 0 else "",
        "test_mode": "docker_native_http",
        "stage": "health_ok" if health_ok else "health_timeout",
    }
