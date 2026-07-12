# ============================================================
# 防御引擎 — Python 端类型定义
# 与 TypeScript src/api/types.ts 保持一一对应
# 注意: 文件名为 defense_types.py 以避免与 Python 标准库 types 冲突
# ============================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

# --------------------- 枚举定义 ---------------------


class DefenseLayer(Enum):
    """五层防御体系"""
    SOURCE_GOVERNANCE = "source_governance"       # L1: 源头数据与供应链治理
    MODEL_INTERACTION = "model_interaction"       # L2: 模型交互与上下文约束
    MEMORY_CONTROL = "memory_control"             # L3: 记忆读写安全控制
    TOOL_CONSTRAINT = "tool_constraint"           # L4: 工具调用与执行安全控制
    DECISION_SUPERVISION = "decision_supervision" # L5: 决策监督与多源验证


class RuleAction(Enum):
    """规则命中后的动作"""
    BLOCK = "block"           # 直接阻断
    WARN = "warn"             # 警告 + 放行
    LOG = "log"               # 仅记录日志
    QUARANTINE = "quarantine" # 隔离 (记忆/工具返回值)
    FILTER = "filter"         # 过滤 (静默移除)
    REWRITE = "rewrite"       # 改写后放行


class PatternType(Enum):
    """规则匹配模式类型"""
    REGEX = "regex"           # 正则表达式
    KEYWORD = "keyword"       # 关键词列表
    SEMANTIC = "semantic"     # 语义检测 (ML 模型)
    STRUCTURAL = "structural" # 结构校验 (JSON Schema)
    COMPOSITE = "composite"   # 复合条件
    CONDITION = "condition"   # 纯条件表达式


class DefenseMode(Enum):
    """防御编排模式"""
    STRICT = "strict"         # 全局拦截: 任何层的 block → 立即返回
    BALANCED = "balanced"     # 逐层衰减: 累积风险分超过阈值才拦截
    PERMISSIVE = "permissive" # 标记传递: 仅 block 动作拦截，其他放行


class AttackFamily(Enum):
    """12 攻击族 (与前端 constants.ts 对齐)"""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    ENCODING_OBFUSCATION = "encoding_obfuscation"
    PAYLOAD_SPLIT = "payload_split"
    RAG_POISONING = "rag_poisoning"
    MEMORY_POISONING = "memory_poisoning"
    TOOL_OUTPUT_POISONING = "tool_output_poisoning"
    SKILL_MCP_POISONING = "skill_mcp_poisoning"
    CHAIN_OF_THOUGHT_ATTACK = "chain_of_thought_attack"
    OPINION_POISONING = "opinion_poisoning"
    MULTI_AGENT_POISONING = "multi_agent_poisoning"
    SUPPLY_CHAIN = "supply_chain"


# --------------------- 数据类 ---------------------


@dataclass
class DefenseRule:
    """单条防御规则"""
    rule_id: str
    name: str
    description: str
    enabled: bool = True
    action: RuleAction = RuleAction.LOG
    priority: int = 99                         # 1-99, 越小越优先
    pattern_type: PatternType = PatternType.REGEX
    pattern: str = ""                          # 匹配模式 (regex / keyword列表 / 条件表达式)
    condition: Optional[str] = None            # 额外条件, e.g. "trust_level < 0.5"
    target_fields: list[str] = field(default_factory=lambda: ["content"])
    # 统计
    hit_count: int = 0
    last_hit_at: Optional[str] = None
    # 版本
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DefenseLayerConfig:
    """单层防御配置"""
    layer: DefenseLayer
    label: str
    enabled: bool
    description: str
    rules: list[DefenseRule] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    # 统计 (运行时填充)
    stats: Optional[dict] = None               # total_checks, total_blocked, block_rate, last_check_at


@dataclass
class LayerCheckResult:
    """单层检查结果"""
    layer: DefenseLayer
    passed: bool
    action: str                                # "pass" | "block" | "warn" | "quarantine" | "rewrite"
    flags: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    matched_rules: list[str] = field(default_factory=list)  # 命中的 rule_id 列表
    processing_time_ms: float = 0.0
    trust_level: float = 1.0                   # 经过此层后的可信度
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DefenseContext:
    """贯穿五层防御的运行时上下文"""
    content: str                               # 待检查内容
    source: str                                # 来源标识
    task_description: str = ""                 # 任务描述
    run_id: str = ""                           # 实验 ID
    target_id: str = ""                        # 目标 Agent ID

    # 元数据
    trust_level: float = 1.0
    content_type: str = "text"                 # text | file | api_response | tool_output

    # 各层结果
    layer_results: dict[str, LayerCheckResult] = field(default_factory=dict)
    risk_scores: dict[str, float] = field(default_factory=dict)

    # 最终决策
    final_verdict: str = "pending"             # pending | passed | blocked | warned
    final_risk_score: float = 0.0
    events: list[dict] = field(default_factory=list)


@dataclass
class DefenseEvent:
    """防御事件日志"""
    event_id: str
    timestamp: str
    run_id: str
    target_id: str
    attack_family: Optional[str] = None        # AttackFamily value
    case_id: Optional[str] = None
    variant_id: Optional[str] = None
    layer: Optional[str] = None                # DefenseLayer value
    rule_id: Optional[str] = None
    action: str = ""                           # block | warn | log | quarantine | filter | rewrite
    content_snippet: str = ""                  # 匹配内容片段 (截断至 200 字符)
    risk_score: float = 0.0


@dataclass
class DefenseTestResult:
    """POST /api/defenses/test 响应"""
    passed: bool
    final_action: str                          # block | warn | pass
    layer_results: dict[str, Optional[dict]]   # layer_name → result dict or None
    risk_score: float
    processing_time_ms: float


@dataclass
class LayerStats:
    """单层防御统计"""
    checks: int = 0
    blocked: int = 0
    rate: float = 0.0


@dataclass
class RuleHit:
    """规则命中统计"""
    rule_id: str
    hits: int
    rule_name: str


@dataclass
class DefenseStats:
    """GET /api/defenses/stats 响应数据"""
    total_checks: int = 0
    total_blocked: int = 0
    overall_block_rate: float = 0.0
    by_layer: dict[str, LayerStats] = field(default_factory=dict)
    top_rules: list[RuleHit] = field(default_factory=list)


@dataclass
class DefenseStrategy:
    """预置防御策略"""
    name: str
    description: str
    layers: dict[str, bool]                    # layer_name → enabled
    mode: str = "balanced"                     # strict | balanced | permissive
