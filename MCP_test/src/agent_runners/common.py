"""Agent 运行器共享工具：DeepSeek 环境变量与 Python 解释器路径。"""

from __future__ import annotations

import os
from pathlib import Path

# MCP_test 项目根目录（agent_runners 上两级）
ROOT = Path(__file__).resolve().parents[2]


def load_deepseek_env() -> dict[str, str]:
    """从 .env 加载 DeepSeek API 配置，供 MCP runner 与 worker 子进程使用。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY missing in MCP_test/.env")
    base = (os.getenv("DEEPSEEK_API_BASE") or "https://api.deepseek.com").rstrip("/")
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
    timeout = int(os.getenv("MCP_EVAL_TIMEOUT_SEC", "90"))
    return {"api_key": key, "base_url": base, "model": model, "timeout": str(timeout)}


def python_exe() -> str:
    """返回主 venv 的 python.exe，用于启动 MCP poison_server 子进程。"""
    return str(ROOT / "venv" / "Scripts" / "python.exe")
