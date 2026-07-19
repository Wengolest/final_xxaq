"""Load API credentials from env or local secret files (never logged)."""

import os
from pathlib import Path
from typing import Iterable, Optional


def _parse_env_line(line: str) -> Optional[tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if not parsed:
            continue
        key, value = parsed
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


# Lower index = lower priority; later files override earlier ones.
_ENV_FILE_PRIORITY = [
    Path(r"D:\AI\Awesome-Rag-Attacks\.env"),
    Path(r"D:\AI\rag_poison_exp\.env"),
    Path(__file__).resolve().parent.parent / ".env",
]


def bootstrap_api_env(extra_paths: Optional[Iterable[Path]] = None) -> None:
    """Populate DEEPSEEK/OPENAI keys without printing secret values."""
    candidate_files = list(_ENV_FILE_PRIORITY)
    if extra_paths:
        candidate_files.extend(extra_paths)

    for index, env_file in enumerate(candidate_files):
        _load_env_file(env_file, override=index > 0)

    deepseek = os.environ.get("DEEPSEEK_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")
    if deepseek and not openai:
        os.environ.setdefault("OPENAI_API_KEY", deepseek)


def require_llm_credentials() -> None:
    bootstrap_api_env()
    if not (
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    ):
        raise RuntimeError(
            "Missing LLM credentials. Set DEEPSEEK_API_KEY (preferred) or "
            "OPENAI_API_KEY in your shell, or place them in (highest priority first): "
            "rag_poison_platform\\.env, rag_poison_exp\\.env, Awesome-Rag-Attacks\\.env"
        )


def mask_api_key(key: str) -> str:
    """Mask secret for logs/CSV; never print raw keys."""
    if not key:
        return ""
    key = key.strip()
    if len(key) <= 4:
        return "****"
    return f"ds-****{key[-4:]}"


def llm_env_status() -> dict[str, bool | list[str]]:
    """Report whether expected LLM env vars are set (never log values)."""
    bootstrap_api_env()
    keys = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "OPENAI_API_KEY")
    status: dict[str, bool | list[str]] = {
        key: bool(os.environ.get(key)) for key in keys
    }
    status["env_files_found"] = [
        str(path) for path in _ENV_FILE_PRIORITY if path.is_file()
    ]
    return status


def deepseek_env_rows() -> list[dict[str, str]]:
    """Rows for agent_api_env_check.csv (DeepSeek-only)."""
    bootstrap_api_env()
    rows = []
    notes = {
        "DEEPSEEK_API_KEY": "primary LLM credential",
        "DEEPSEEK_BASE_URL": "OpenAI-compatible API base",
        "DEEPSEEK_MODEL": "chat model id",
    }
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        val = os.environ.get(key, "")
        rows.append(
            {
                "key_name": key,
                "present": "true" if bool(val) else "false",
                "masked_preview": mask_api_key(val) if key.endswith("_KEY") else (val[:40] if val else ""),
                "notes": notes[key],
            }
        )
    return rows
