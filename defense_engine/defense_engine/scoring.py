# ============================================================
# 防御评分引擎 — 共享打分逻辑 + AI 语义检测预留接口
#
# 职责:
#   1. 统一的风险分/信任度计算 (各层复用)
#   2. SemanticScorer 抽象接口 — 预留 Llama Guard / 自训练模型集成
#   3. 可配置权重 (按层微调)
#
# 使用方式:
#   from scoring import compute_layer_result, DEFAULT_WEIGHTS
#   result = compute_layer_result(layer, checks, rule_matches, t_start, trust_in)
# ============================================================

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

try:
    from .defense_types import DefenseLayer, LayerCheckResult
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult


# ============================================================
# 一、权重配置
# ============================================================

@dataclass
class LayerWeights:
    """单层风险权重配置"""
    check_block: float = 0.25       # 程序化检查 block → 风险加分量
    check_warn: float = 0.08        # 程序化检查 warn
    check_log: float = 0.00         # 程序化检查 log
    rule_block: float = 0.30        # 规则引擎 block/quarantine
    rule_warn: float = 0.10         # 规则引擎 warn
    rule_log: float = 0.00          # 规则引擎 log
    semantic_block: float = 0.40    # AI 语义检测 block (预留)
    semantic_warn: float = 0.15     # AI 语义检测 warn (预留)


# 默认权重
DEFAULT_WEIGHTS = LayerWeights()

# L4 工具约束层权重 (check_warn 从 0.10 降至 0.05: 避免每次 execute_command 累积 0.20,
# 降低 BALANCED 模式下因 LLM 生成无害工具调用而触发误拦截的概率)
TOOL_LAYER_WEIGHTS = LayerWeights(
    check_block=0.30,
    check_warn=0.05,
    rule_block=0.35,
    rule_warn=0.12,
)

# L3 记忆控制层权重 (记忆污染影响持久，block 权重高，warn 适中)
MEMORY_LAYER_WEIGHTS = LayerWeights(
    check_block=0.28,
    check_warn=0.08,
    rule_block=0.32,
    rule_warn=0.10,
)

# L5 决策监督层权重 (最终仲裁，block 权重适中，预留语义权重)
DECISION_LAYER_WEIGHTS = LayerWeights(
    check_block=0.25,
    check_warn=0.08,
    rule_block=0.30,
    rule_warn=0.10,
    semantic_block=0.40,
    semantic_warn=0.15,
)

# 按层查权重表
LAYER_WEIGHTS_MAP = {
    DefenseLayer.SOURCE_GOVERNANCE: DEFAULT_WEIGHTS,
    DefenseLayer.MODEL_INTERACTION: DEFAULT_WEIGHTS,
    DefenseLayer.MEMORY_CONTROL: MEMORY_LAYER_WEIGHTS,
    DefenseLayer.TOOL_CONSTRAINT: TOOL_LAYER_WEIGHTS,
    DefenseLayer.DECISION_SUPERVISION: DECISION_LAYER_WEIGHTS,
}


def get_layer_weights(layer: DefenseLayer) -> LayerWeights:
    return LAYER_WEIGHTS_MAP.get(layer, DEFAULT_WEIGHTS)


# ============================================================
# 二、统一打分逻辑
# ============================================================

@dataclass
class CheckFlag:
    """通用检查标志 (程序化检查 & 规则命中统一表示)"""
    check_type: str       # 检查类型标识
    severity: str         # "block" | "warn" | "log" | "pass"
    description: str
    source: str = ""      # "programmatic" | "rule" | "semantic"
    rule_id: str = ""

    def is_blocking(self) -> bool:
        return self.severity in ("block", "quarantine")


def compute_layer_result(
    layer: DefenseLayer,
    flags: list[CheckFlag],
    trust_in: float,
    t_start: float,
    weights: Optional[LayerWeights] = None,
) -> LayerCheckResult:
    """
    统一的逐层结果计算。

    Args:
        layer: 当前防御层
        flags: 所有检查标志 (程序化 + 规则引擎 + 语义)
        trust_in: 进入此层时的信任度
        t_start: 本层开始时间戳 (time.perf_counter())
        weights: 权重配置 (默认按 layer 自动选取)

    Returns:
        LayerCheckResult 含 passed / action / risk_score / trust_level / flags
    """
    w = weights or get_layer_weights(layer)

    blocked = False
    action = "pass"
    risk = 0.0
    matched_rules: list[str] = []
    output_flags: list[str] = []

    for f in flags:
        # 分类处理
        if f.source == "rule":
            matched_rules.append(f.rule_id)
            if f.severity in ("block", "quarantine"):
                risk += w.rule_block
            elif f.severity == "warn":
                risk += w.rule_warn
            else:
                risk += w.rule_log
        elif f.source == "semantic":
            matched_rules.append(f.rule_id or "semantic")
            if f.severity in ("block", "quarantine"):
                risk += w.semantic_block
            elif f.severity == "warn":
                risk += w.semantic_warn
        else:
            # programmatic
            if f.severity == "block":
                risk += w.check_block
            elif f.severity == "warn":
                risk += w.check_warn
            else:
                risk += w.check_log

        # 构建可读 flag 字符串
        prefix = {"rule": f"[{layer.value}-rule:{f.rule_id}]",
                  "semantic": f"[{layer.value}-AI:{f.check_type}]"}
        prefix_str = prefix.get(f.source, f"[{layer.value}-{f.check_type}]")
        output_flags.append(f"{prefix_str} {f.description}")

        if f.is_blocking():
            blocked = True
            action = f.severity

    elapsed = (time.perf_counter() - t_start) * 1000
    risk = min(risk, 1.0)
    new_trust = max(0.0, trust_in - risk)

    return LayerCheckResult(
        layer=layer,
        passed=not blocked,
        action=action,
        flags=output_flags,
        risk_score=risk,
        matched_rules=matched_rules,
        processing_time_ms=elapsed,
        trust_level=new_trust,
    )


# ============================================================
# 三、语义检测预留接口
# ============================================================

@dataclass
class SemanticScore:
    """AI 语义检测结果"""
    label: str                          # 分类标签: "safe" | "prompt_injection" | "jailbreak" | ...
    confidence: float                   # 置信度 0.0-1.0
    severity: str = "warn"              # 建议动作: "block" | "warn" | "log"
    reason: str = ""                    # 可解释原因
    model_name: str = ""                # 模型名 (e.g. "llama-guard-3")
    latency_ms: float = 0.0             # 推理耗时
    extra: dict = field(default_factory=dict)


class SemanticScorer(ABC):
    """
    语义检测器抽象基类 [预留 ML 接口]。

    当前阶段为预留接口，暂不接入真实模型。未来可集成:
      - Llama Guard 3 / Prompt Guard
      - 自训练 ONNX/Transformers 分类模型
      - 远程安全审核 API

    LayerWeights 中的 semantic_block / semantic_warn 权重为这些预留接口设计，
    在当前 PassThroughScorer 实现下始终不会被触发（返回 severity="log"）。
    接入真实 SemanticScorer 实现后，权重即可生效。

    实现方式:
      - 本地模型: 加载 onnx / transformers 模型
      - 远程 API: HTTP 调用 Llama Guard 服务
      - Mock: 返回固定 SemanticScore 用于测试

    示例:
      class LlamaGuardScorer(SemanticScorer):
          def score(self, content, context=None):
              response = self.client.classify(content)
              return SemanticScore(
                  label=response.label,
                  confidence=response.confidence,
                  severity="block" if response.label != "safe" else "log",
                  model_name="llama-guard-3",
              )
    """

    @abstractmethod
    def score(self, content: str, context: Optional[dict] = None) -> SemanticScore:
        """
        对内容进行语义安全检测。

        Args:
            content: 待检测文本
            context: 上下文 (e.g. {"source": "user_input", "trust_level": 0.5})

        Returns:
            SemanticScore 检测结果
        """
        ...

    def to_check_flag(self, score: SemanticScore) -> CheckFlag:
        """将 SemanticScore 转为统一的 CheckFlag"""
        return CheckFlag(
            check_type=f"semantic_{score.label}",
            severity=score.severity,
            description=f"[{score.model_name}] {score.label} (conf={score.confidence:.2f}) {score.reason}",
            source="semantic",
            rule_id=score.model_name or "semantic",
        )


class PassThroughScorer(SemanticScorer):
    """
    默认语义检测器: 始终放行。
    在未接入真实 AI 模型时作为占位实现，不影响现有检测流程。
    """
    def score(self, content: str, context: Optional[dict] = None) -> SemanticScore:
        return SemanticScore(
            label="safe",
            confidence=1.0,
            severity="log",
            reason="pass-through (no AI scorer configured)",
            model_name="none",
        )

    def to_check_flag(self, score: SemanticScore) -> CheckFlag:
        return CheckFlag(
            check_type="semantic",
            severity="log",
            description="语义检测: 未配置 (放行)",
            source="semantic",
            rule_id="semantic_pass",
        )
