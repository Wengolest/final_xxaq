"""ASB 攻击器 — DPI (直接) + IPI (间接) Prompt 注入，自动评分，HTTP 接口，轨迹导出."""

from .variants import INJECTION_VARIANTS, build_injection_prompt
from .tools import AttackTool, get_default_tools
from .scorer import BaseScorer, DeepSeekScorer, OllamaScorer, create_scorer
from .ipi_scenarios import IPIScenario, get_scenario, list_scenarios, get_default_scenario
from .orchestrator import AttackResult, DPIAttackOrchestrator, IPIAttackResult, IPIAttackOrchestrator
from .converter import attack_result_to_record, ipi_result_to_record

__all__ = [
    # 注入变体
    "INJECTION_VARIANTS",
    "build_injection_prompt",
    # 工具定义
    "AttackTool",
    "get_default_tools",
    # 评分器
    "BaseScorer",
    "DeepSeekScorer",
    "OllamaScorer",
    "create_scorer",
    # IPI 场景
    "IPIScenario",
    "get_scenario",
    "list_scenarios",
    "get_default_scenario",
    # DPI 编排器
    "AttackResult",
    "DPIAttackOrchestrator",
    # IPI 编排器
    "IPIAttackResult",
    "IPIAttackOrchestrator",
    # 轨迹转换
    "attack_result_to_record",
    "ipi_result_to_record",
]
