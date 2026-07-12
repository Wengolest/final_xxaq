#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/5 22:59
@Author  : alexanderwu
@File    : __init__.py
"""

from metagpt.provider.google_gemini_api import GeminiLLM
from metagpt.provider.ollama_api import OllamaLLM
from metagpt.provider.openai_api import OpenAILLM
from metagpt.provider.zhipuai_api import ZhiPuAILLM
from metagpt.provider.azure_openai_api import AzureOpenAILLM
from metagpt.provider.metagpt_api import MetaGPTLLM
from metagpt.provider.human_provider import HumanProvider
def _optional_import(module_path, name, default=None):
    """可选导入：依赖未安装或版本不兼容时返回 default，避免阻塞 OpenAI/DeepSeek 等核心 provider。"""
    try:
        mod = __import__(module_path, fromlist=[name])
        return getattr(mod, name)
    except (ModuleNotFoundError, ImportError, AttributeError):
        return default

SparkLLM = _optional_import("metagpt.provider.spark_api", "SparkLLM")
QianFanLLM = _optional_import("metagpt.provider.qianfan_api", "QianFanLLM")
DashScopeLLM = _optional_import("metagpt.provider.dashscope_api", "DashScopeLLM")
AnthropicLLM = _optional_import("metagpt.provider.anthropic_api", "AnthropicLLM")
BedrockLLM = _optional_import("metagpt.provider.bedrock_api", "BedrockLLM")
ArkLLM = _optional_import("metagpt.provider.ark_api", "ArkLLM")
OpenrouterReasoningLLM = _optional_import("metagpt.provider.openrouter_reasoning", "OpenrouterReasoningLLM")

__all__ = [
    "GeminiLLM",
    "OpenAILLM",
    "ZhiPuAILLM",
    "AzureOpenAILLM",
    "MetaGPTLLM",
    "OllamaLLM",
    "HumanProvider",
    "SparkLLM",
    "QianFanLLM",
    "DashScopeLLM",
    "AnthropicLLM",
    "BedrockLLM",
    "ArkLLM",
    "OpenrouterReasoningLLM",
]
