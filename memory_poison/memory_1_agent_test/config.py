# -*- coding: utf-8 -*-
"""单 Agent MEMORY 投毒验证实验配置。"""

from pathlib import Path

# 本目录
TEST_ROOT = Path(__file__).resolve().parent
# 项目根目录（复用 plugin 模块）
PROJECT_ROOT = TEST_ROOT.parent

DATA_DIR = TEST_ROOT / "data"
RESULTS_DIR = TEST_ROOT / "results"
AGENT_DB_DIR = TEST_ROOT / "agent_databases"

# 固定使用 1 个 Agent：CI 流水线（主实验中 MEMORY 投毒命中率较高，便于验证）
TARGET_AGENT_ID = "ci_pipeline_agent"

# 样本文件
SAMPLES_PATH = DATA_DIR / "validation_samples.json"

# DeepSeek（与主实验 plugin 一致）
DEEPSEEK_API_KEY = "sk-0f73786025e74c0c809d4fdeeb4fad02"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
