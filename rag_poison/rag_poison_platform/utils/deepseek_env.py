"""DeepSeek-only credential helpers for bulk agent deployment (never log raw keys)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.env_bootstrap import bootstrap_api_env

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_ENV = PLATFORM_ROOT / ".env"

DEEPSEEK_KEYS = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")

# Agents known to require services beyond DeepSeek (no third-party repo edits).
API_DEPENDENT_AGENT_IDS = frozenset(
    {
        "chat-langchain",
        "sample-app-aoai-chatgpt",
    }
)

EXTERNAL_SERVICE_PATTERNS = (
    "ANTHROPIC_API_KEY",
    "MINTLIFY_API_KEY",
    "PYLON_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "DASHSCOPE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "COHERE_API_KEY",
    "PINECONE_API_KEY",
    "MISTRAL_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
)

OPENAI_COMPAT_TARGETS = (
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "BASE_URL",
    "MODEL",
    "MODEL_NAME",
    "LLM_MODEL",
)


def mask_api_key(key: str) -> str:
    """Mask secret for logs/CSV; e.g. ds-****abcd."""
    if not key:
        return ""
    key = key.strip()
    if len(key) <= 4:
        return "****"
    return f"ds-****{key[-4:]}"


def load_deepseek_env() -> Dict[str, str]:
    """Load DeepSeek vars from platform .env (no printing)."""
    bootstrap_api_env([PLATFORM_ENV])
    out: Dict[str, str] = {}
    for name in DEEPSEEK_KEYS:
        val = os.environ.get(name, "")
        if val:
            out[name] = val
    if "DEEPSEEK_BASE_URL" not in out:
        out["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com"
    if "DEEPSEEK_MODEL" not in out:
        out["DEEPSEEK_MODEL"] = "deepseek-chat"
    return out


def deepseek_available() -> bool:
    return bool(load_deepseek_env().get("DEEPSEEK_API_KEY"))


def build_compat_env_map(deepseek: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Map DeepSeek credentials to common OpenAI-compat env names for child processes."""
    ds = deepseek or load_deepseek_env()
    key = ds.get("DEEPSEEK_API_KEY", "")
    base = ds.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = ds.get("DEEPSEEK_MODEL", "deepseek-chat")
    if not key:
        return {}
    return {
        "DEEPSEEK_API_KEY": key,
        "DEEPSEEK_BASE_URL": base,
        "DEEPSEEK_MODEL": model,
        "OPENAI_API_KEY": key,
        "OPENAI_API_BASE": base,
        "OPENAI_BASE_URL": base,
        "OPENAI_MODEL": model,
        "BASE_URL": base,
        "MODEL": model,
        "MODEL_NAME": model,
        "LLM_MODEL": model,
    }


def build_mock_env_map() -> Dict[str, str]:
    """Env for mock LLM backend (strip all LLM keys)."""
    return {"MODEL_BACKEND": "mock"}


def write_agent_env_file(agent_dir: Path, *, use_deepseek: bool = True) -> Path:
    """Write agent .env with DeepSeek-compat mapping (outer wrapper only)."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    out = agent_dir / ".env"
    if use_deepseek:
        mapping = build_compat_env_map()
        if not mapping:
            lines = ["# DEEPSEEK_API_KEY not set; agent may fail LLM calls\n"]
        else:
            lines = [f"{k}={v}" for k, v in mapping.items() if k in OPENAI_COMPAT_TARGETS or k.startswith("DEEPSEEK_")]
    else:
        lines = ["# mock backend: no LLM keys\n"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def merge_process_env(base: Optional[Dict[str, str]] = None, *, backend: str = "deepseek") -> Dict[str, str]:
    """Build subprocess env with DeepSeek compat or mock backend."""
    env = dict(base or os.environ)
    for k in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MINTLIFY_API_KEY",
        "PYLON_API_KEY",
        "GOOGLE_API_KEY",
        "DASHSCOPE_API_KEY",
    ):
        env.pop(k, None)
    if backend == "mock":
        env.update(build_mock_env_map())
        return env
    env.update(build_compat_env_map())
    return env


def scan_repo_external_services(repo: Path, *, max_files: int = 200) -> List[str]:
    """Detect required non-DeepSeek API keys from repo text (read-only scan)."""
    found: List[str] = []
    if not repo.is_dir():
        return found
    patterns = {p: re.compile(re.escape(p), re.I) for p in EXTERNAL_SERVICE_PATTERNS}
    checked = 0
    for path in repo.rglob("*"):
        if checked >= max_files:
            break
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".ts", ".js", ".env", ".example", ".md", ".yaml", ".yml", ".toml"}:
            continue
        try:
            if path.stat().st_size > 300_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        checked += 1
        for name, pat in patterns.items():
            if pat.search(text) and name not in found:
                found.append(name)
    return found


def classify_api_dependency(
    agent_id: str,
    repo: Path,
    *,
    install_success: bool = False,
) -> Tuple[str, str, bool]:
    """
    Return (status, sample_type, external_service_missing).
    status may be install_success_but_external_service_missing or external_service_missing.
    """
    if agent_id in API_DEPENDENT_AGENT_IDS:
        if agent_id == "chat-langchain" and install_success:
            return (
                "install_success_but_external_service_missing",
                "api_dependent_agent",
                True,
            )
        return ("external_service_missing", "api_dependent_agent", True)

    markers = scan_repo_external_services(repo)
    non_openai = [m for m in markers if m != "OPENAI_API_KEY"]
    if non_openai:
        note = ",".join(non_openai[:5])
        if install_success and agent_id == "chat-langchain":
            return ("install_success_but_external_service_missing", "api_dependent_agent", True)
        return ("external_service_missing", "api_dependent_agent", True)
    return ("", "external_github_agent", False)


def require_deepseek_credentials() -> None:
    """Raise if DEEPSEEK_API_KEY missing (DeepSeek-only policy)."""
    bootstrap_api_env([PLATFORM_ENV])
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError(
            "Missing DEEPSEEK_API_KEY. Set it in rag_poison_platform\\.env "
            "(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)."
        )
