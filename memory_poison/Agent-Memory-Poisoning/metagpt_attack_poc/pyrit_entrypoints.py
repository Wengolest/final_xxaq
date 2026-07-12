#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 PyRIT 集成提供的入口函数。

设计目标：
1. 让 PyRIT 的自定义 Target 可以简单地调用本文件的函数，
   而不需要关心 MetaGPT 的内部细节。
2. 保持与当前四个攻击实验兼容：既可以直接对 DataInterpreter 进行对话攻击，
   也可以通过子进程调用 exp1–exp4 实验脚本。
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from metagpt.roles.di.data_interpreter import DataInterpreter


PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def _arun_data_interpreter(prompt: str) -> str:
    """异步调用 DataInterpreter，返回字符串结果。"""
    agent = DataInterpreter()
    resp = await agent.run(prompt)
    return str(resp)


async def arun_data_interpreter(prompt: str) -> str:
    """公开的异步入口，供 async 场景直接 await 使用。"""
    return await _arun_data_interpreter(prompt)


def run_data_interpreter(prompt: str) -> str:
    """
    同步入口：给定一个 prompt，调用 MetaGPT 的 DataInterpreter，并返回字符串输出。

    供 PyRIT 的 Target 或其它脚本直接调用：

        from metagpt_attack_poc.pyrit_entrypoints import run_data_interpreter
        result = run_data_interpreter("你的攻击提示")
    """
    try:
        return asyncio.run(_arun_data_interpreter(prompt))
    except RuntimeError:
        # 兼容在已有事件循环中的场景（例如某些异步框架）
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_arun_data_interpreter(prompt))


def _run_exp_script(rel_path: str) -> str:
    """
    运行指定相对路径的实验脚本，并返回 stdout+stderr。

    rel_path 例如：
        "metagpt_attack_poc/experiments/exp1_schema_spoof.py"
    """
    # 直接使用 Path 拼接，Windows 会自动处理分隔符
    script_path = PROJECT_ROOT / rel_path
    cmd = [sys.executable, str(script_path)]
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return proc.stdout + "\n" + proc.stderr


def run_experiment(exp_name: str) -> str:
    """
    统一的实验运行入口，供 PyRIT 调用。

    参数:
        exp_name:
            - "exp1" / "schema_spoof"
            - "exp2" / "judge_jack"
            - "exp3" / "memory_graft"
            - "exp4" / "rag_vector_drift"

    返回:
        实验脚本的完整输出（stdout + stderr）。
    """
    exp_name = exp_name.lower().strip()

    if exp_name in {"exp1", "schema_spoof"}:
        rel = "metagpt_attack_poc/experiments/exp1_schema_spoof.py"
    elif exp_name in {"exp2", "judge_jack", "judge_jacking"}:
        rel = "metagpt_attack_poc/experiments/exp2_judge_jack.py"
    elif exp_name in {"exp3", "memory_graft"}:
        rel = "metagpt_attack_poc/experiments/exp3_memory_graft.py"
    elif exp_name in {"exp4", "rag_vector_drift", "rag_poison"}:
        rel = "metagpt_attack_poc/experiments/exp4_rag_vector_drift.py"
    else:
        return f"Unknown experiment name: {exp_name}"

    return _run_exp_script(rel)


__all__ = [
    "run_data_interpreter",
    "arun_data_interpreter",
    "run_experiment",
]

