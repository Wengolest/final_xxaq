# -*- coding: utf-8 -*-
"""实验结果输出目录管理：每次运行独立子目录 + latest.json 指针。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def create_run_directory(results_root: Path) -> Path:
    """为单次实验创建带时间戳的输出目录。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = results_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_latest_pointer(results_root: Path, run_dir: Path, meta: dict[str, Any]) -> None:
    """写入 latest.json，指向最近一次实验目录及元信息。"""
    pointer = {
        "latest_run_dir": str(run_dir),
        "updated_at": datetime.now().isoformat(),
        **meta,
    }
    latest_path = results_root / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(pointer, f, ensure_ascii=False, indent=2)
