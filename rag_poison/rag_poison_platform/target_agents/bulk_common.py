"""Shared utilities for bulk GitHub agent deployment pipeline."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from utils.paths import RESULTS_DIR

BULK_ROOT = Path(r"D:\AI\target_agents_bulk")
REGISTRY_PATH = PLATFORM_ROOT / "target_agents" / "bulk_registry.yaml"
BASE_PORT = 19001

AGENT_TEMPLATE: Dict[str, Any] = {
    "id": "",
    "repo_url": "",
    "repo_name": "",
    "framework": "",
    "local_path": "",
    "venv_path": "",
    "candidate_reason": "",
    "status": "candidate",
    "clone_success": False,
    "install_success": False,
    "startup_success": False,
    "http_api_success": False,
    "rag_capable": False,
    "poison_tested": False,
    "poison_test_supported": False,
    "grade": "D",
    "sample_type": "",
    "local_variant": False,
    "model_backend": "",
    "external_service_missing": False,
    "api_dependency_notes": "",
    "requires_llm_key": True,
    "requires_database": False,
    "requires_docker": False,
    "requires_frontend": False,
    "has_requirements_txt": False,
    "has_pyproject_toml": False,
    "has_dockerfile": False,
    "has_fastapi": False,
    "has_flask": False,
    "has_langchain": False,
    "has_langgraph": False,
    "has_llamaindex": False,
    "has_chroma": False,
    "has_faiss": False,
    "has_qdrant": False,
    "likely_endpoints": {
        "docs": "",
        "health": "",
        "openapi": "",
        "chat": "",
        "query": "",
        "invoke": "",
        "ingest": "",
        "upload": "",
        "documents": "",
    },
    "api_base_url": "",
    "assigned_port": 0,
    "docs_endpoint": "",
    "health_endpoint": "",
    "chat_endpoint": "",
    "query_endpoint": "",
    "ingest_endpoint": "",
    "request_format": "",
    "response_format_notes": "",
    "error_stage": "",
    "error_summary": "",
    "deploy_commands": {"clone": "", "install": "", "start": ""},
    "tested_at": "",
    "notes": "",
}


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def agent_root(agent_id: str) -> Path:
    return BULK_ROOT / agent_id


def repo_path(agent_id: str) -> Path:
    return agent_root(agent_id) / "repo"


def venv_path(agent_id: str) -> Path:
    return agent_root(agent_id) / ".venv"


def logs_path(agent_id: str) -> Path:
    p = agent_root(agent_id) / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_log(agent_id: str, name: str, text: str) -> Path:
    path = logs_path(agent_id) / name
    path.write_text(text, encoding="utf-8", errors="replace")
    return path


def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {"agents": []}
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"agents": []}


def save_registry(data: Dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def get_agent(registry: Dict[str, Any], agent_id: str) -> Optional[Dict[str, Any]]:
    for a in registry.get("agents", []):
        if a.get("id") == agent_id:
            return a
    return None


def update_agent(registry: Dict[str, Any], agent_id: str, **fields: Any) -> None:
    for a in registry.get("agents", []):
        if a.get("id") == agent_id:
            a.update(fields)
            return
    raise KeyError(agent_id)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    keys = fieldnames or sorted({k for r in rows for k in r})
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run_cmd(
    cmd: List[str],
    *,
    cwd: Optional[Path] = None,
    timeout: int = 600,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
        return 124, out + "\n[TIMEOUT]"
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def git_ls_remote(url: str) -> bool:
    code, _ = run_cmd(["git", "ls-remote", "--heads", url], timeout=60)
    return code == 0


def repo_id_from_url(url: str) -> str:
    name = url.rstrip("/").split("/")[-1].replace(".git", "")
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", name).lower()
    return name[:48]


def scan_repo_features(repo: Path) -> Dict[str, Any]:
    text_blobs: List[str] = []
    endpoints: Dict[str, str] = {}
    patterns = {
        "docs": r'["\']/docs["\']',
        "health": r'["\']/(health|healthz)["\']',
        "openapi": r'["\']/openapi\.json["\']',
        "chat": r'["\']/(chat|conversation)["\']',
        "query": r'["\']/(query|ask|qa)["\']',
        "invoke": r'["\']/(invoke|agents/invoke)["\']',
        "ingest": r'["\']/(ingest|index|add_document)["\']',
        "upload": r'["\']/(upload|upload_file)["\']',
        "documents": r'["\']/(documents|docs_upload)["\']',
    }

    py_files = list(repo.rglob("*.py"))[:400]
    req_files = list(repo.rglob("requirements*.txt"))
    pyproject = list(repo.rglob("pyproject.toml"))
    dockerfiles = list(repo.rglob("Dockerfile*"))

    combined = ""
    for p in py_files:
        try:
            if p.stat().st_size > 200_000:
                continue
            t = p.read_text(encoding="utf-8", errors="ignore")
            combined += t + "\n"
            text_blobs.append(t)
        except OSError:
            pass

    for key, pat in patterns.items():
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            endpoints[key] = m.group(0).strip("'\"")

    lc = combined.lower()
    return {
        "has_requirements_txt": bool(req_files),
        "has_pyproject_toml": bool(pyproject),
        "has_dockerfile": bool(dockerfiles),
        "has_fastapi": "fastapi" in lc or "from fastapi" in lc,
        "has_flask": "flask" in lc and "fastapi" not in lc,
        "has_langchain": "langchain" in lc,
        "has_langgraph": "langgraph" in lc,
        "has_llamaindex": "llama_index" in lc or "llamaindex" in lc,
        "has_chroma": "chromadb" in lc or "chroma" in lc,
        "has_faiss": "faiss" in lc,
        "has_qdrant": "qdrant" in lc,
        "likely_endpoints": endpoints,
        "requires_docker": bool(dockerfiles) and "docker-compose" in lc,
        "requires_database": any(
            x in lc for x in ("postgres", "redis", "mongodb", "sqlalchemy")
        ),
        "requires_frontend": any(
            x in lc for x in ("react", "next.js", "vue", "streamlit")
        ),
    }


def apply_api_dependency_fields(agent: Dict[str, Any], repo: Path) -> None:
    """Classify external API dependencies without modifying third-party repos."""
    from utils.deepseek_env import classify_api_dependency, scan_repo_external_services

    aid = agent.get("id", "")
    install_ok = bool(agent.get("install_success"))
    status, sample_type, ext_missing = classify_api_dependency(
        aid, repo, install_success=install_ok
    )
    if ext_missing:
        agent["external_service_missing"] = True
        agent["sample_type"] = sample_type
        agent["poison_test_supported"] = False
        if status:
            agent["status"] = status
        markers = scan_repo_external_services(repo)
        agent["api_dependency_notes"] = ",".join(markers[:6]) if markers else "known_api_dependent_agent"
    elif agent.get("clone_success") and install_ok:
        agent["sample_type"] = "external_github_agent"
        agent["external_service_missing"] = False
        agent["poison_test_supported"] = bool(
            agent.get("rag_capable")
            and agent.get("http_api_success")
            and not agent.get("install_skipped")
        )


def assign_grade(agent: Dict[str, Any]) -> str:
    if agent.get("poison_tested"):
        return "A"
    if agent.get("rag_capable") and agent.get("http_api_success"):
        return "A"
    if agent.get("http_api_success") and (
        agent.get("chat_endpoint") or agent.get("query_endpoint")
    ):
        return "B"
    if agent.get("startup_success") or agent.get("install_success"):
        return "C"
    return "D"


def compute_summary(registry: Dict[str, Any]) -> Dict[str, Any]:
    agents = registry.get("agents", [])
    for a in agents:
        a["grade"] = assign_grade(a)

    def cnt(pred):
        return sum(1 for a in agents if pred(a))

    frameworks: Dict[str, int] = {}
    for a in agents:
        fw = a.get("framework") or "unknown"
        frameworks[fw] = frameworks.get(fw, 0) + 1

    errors: Dict[str, int] = {}
    for a in agents:
        stage = a.get("error_stage") or "none"
        if stage and stage != "none":
            errors[stage] = errors.get(stage, 0) + 1

    return {
        "generated_at": now_iso(),
        "candidate_count": len(agents),
        "clone_success_count": cnt(lambda a: a.get("clone_success")),
        "install_success_count": cnt(lambda a: a.get("install_success")),
        "startup_success_count": cnt(lambda a: a.get("startup_success")),
        "http_api_success_count": cnt(lambda a: a.get("http_api_success")),
        "rag_capable_count": cnt(lambda a: a.get("rag_capable")),
        "poison_tested_count": cnt(lambda a: a.get("poison_tested")),
        "poison_test_supported_count": cnt(lambda a: a.get("poison_test_supported")),
        "external_github_count": cnt(lambda a: a.get("sample_type") == "external_github_agent"),
        "api_dependent_count": cnt(lambda a: a.get("sample_type") == "api_dependent_agent"),
        "local_variant_count": cnt(lambda a: a.get("local_variant")),
        "grade_a_count": cnt(lambda a: a.get("grade") == "A"),
        "grade_b_count": cnt(lambda a: a.get("grade") == "B"),
        "grade_c_count": cnt(lambda a: a.get("grade") == "C"),
        "grade_d_count": cnt(lambda a: a.get("grade") == "D"),
        "failure_by_stage": errors,
        "framework_distribution": frameworks,
        "successful_agents": [
            a["id"] for a in agents if a.get("startup_success")
        ],
        "http_agents": [a["id"] for a in agents if a.get("http_api_success")],
        "rag_capable_agents": [
            a["id"] for a in agents if a.get("rag_capable")
        ],
        "poison_tested_agents": [
            a["id"] for a in agents if a.get("poison_tested")
        ],
    }
