# ============================================================
# 防御编排器 — 五层串联执行引擎
#
# 职责:
#   1. 按 L1 → L2 → L3 → L4 → L5 顺序串联执行
#   2. 传递 DefenseContext (含 trust_level 逐层衰减)
#   3. 根据 DefenseMode 决定短路策略
#   4. 汇总最终裁决和逐层结果
#
# DefenseMode:
#   strict:    任何层 block → 立即短路返回
#   balanced:  累积风险分 > 阈值(0.7) → 拦截
#   permissive: 仅 block 动作拦截，warn 放行
#
# 使用方式:
#   from orchestrator import DefenseOrchestrator
#   orch = DefenseOrchestrator(engine, mode=DefenseMode.BALANCED)
#   result = orch.run(context)
# ============================================================

import time
from typing import Optional

try:
    from .defense_types import (
        DefenseLayer, DefenseMode, DefenseContext, LayerCheckResult,
        DefenseTestResult, LayerStats,
    )
    from .layer1_source_governance import SourceGovernance
    from .layer2_model_interaction import ModelInteraction
    from .layer3_memory_control import MemoryControl, SimulatedMemoryBackend, MemoryBackend
    from .layer4_tool_constraint import ToolConstraint
    from .layer5_decision_supervision import DecisionSupervision
except ImportError:
    from defense_types import (
        DefenseLayer, DefenseMode, DefenseContext, LayerCheckResult,
        DefenseTestResult, LayerStats,
    )
    from layer1_source_governance import SourceGovernance
    from layer2_model_interaction import ModelInteraction
    from layer3_memory_control import MemoryControl, SimulatedMemoryBackend, MemoryBackend
    from layer4_tool_constraint import ToolConstraint
    from layer5_decision_supervision import DecisionSupervision


# 默认层执行顺序
DEFAULT_LAYER_ORDER = [
    DefenseLayer.SOURCE_GOVERNANCE,
    DefenseLayer.MODEL_INTERACTION,
    DefenseLayer.MEMORY_CONTROL,
    DefenseLayer.TOOL_CONSTRAINT,
    DefenseLayer.DECISION_SUPERVISION,
]

# balanced 模式下的风险阈值
BALANCED_THRESHOLD = 0.7

# 各层默认参数
DEFAULT_LAYER_PARAMS = {
    DefenseLayer.SOURCE_GOVERNANCE: {
        "source_whitelist": ["internal_db", "verified_api", "user_input", "sandbox", "benchmark", "trusted_partner"],
        "max_file_size_mb": 50,
    },
    DefenseLayer.MODEL_INTERACTION: {
        "context_separation": True,
        "max_context_tokens": 16000,
    },
    DefenseLayer.MEMORY_CONTROL: {
        "default_ttl_hours": 24,
        "max_memory_entries": 1000,
    },
    DefenseLayer.TOOL_CONSTRAINT: {
        "high_risk_actions": ["write_file", "delete_file", "execute_command", "run_script", "db_write", "send_email"],
    },
    DefenseLayer.DECISION_SUPERVISION: {
        "audit_threshold": 0.7,
        "vote_threshold": 0.6,
    },
}


class DefenseOrchestrator:
    """五层防御编排器"""

    def __init__(
        self,
        engine: Optional[object] = None,
        mode: DefenseMode = DefenseMode.BALANCED,
        enabled_layers: Optional[list[DefenseLayer]] = None,
        layer_params: Optional[dict] = None,
    ):
        """
        Args:
            engine: RuleEngine 实例 (共享规则引擎)
            mode: 防御编排模式
            enabled_layers: 启用的层列表 (默认全部)
            layer_params: 各层参数字典 {DefenseLayer: {key: value}}
        """
        self.engine = engine
        self.mode = mode

        # 合并参数
        params = dict(DEFAULT_LAYER_PARAMS)
        if layer_params:
            for layer, p in layer_params.items():
                if layer in params:
                    params[layer].update(p)
                else:
                    params[layer] = p

        # 初始化各层检测器
        self._layers: dict[DefenseLayer, object] = {}
        if enabled_layers is None:
            enabled_layers = list(DEFAULT_LAYER_ORDER)

        for layer in enabled_layers:
            lp = params.get(layer, {})
            if layer == DefenseLayer.SOURCE_GOVERNANCE:
                self._layers[layer] = SourceGovernance(lp)
            elif layer == DefenseLayer.MODEL_INTERACTION:
                self._layers[layer] = ModelInteraction(lp)
            elif layer == DefenseLayer.MEMORY_CONTROL:
                backend = lp.get("backend") or SimulatedMemoryBackend()
                self._layers[layer] = MemoryControl(backend, lp)
            elif layer == DefenseLayer.TOOL_CONSTRAINT:
                self._layers[layer] = ToolConstraint(lp)
            elif layer == DefenseLayer.DECISION_SUPERVISION:
                self._layers[layer] = DecisionSupervision(lp)

        self._layer_order = [l for l in DEFAULT_LAYER_ORDER if l in self._layers]
        self._enabled_layers: dict[str, bool] = {
            layer.value: True for layer in self._layers
        }

    # ---- 属性 ----

    @property
    def enabled_layers(self) -> dict[str, bool]:
        return dict(self._enabled_layers)

    def set_layer_enabled(self, layer: DefenseLayer, enabled: bool):
        """启用/禁用某层"""
        self._enabled_layers[layer.value] = enabled

    # ---- 主执行流程 ----

    def run(self, ctx: DefenseContext, tool_call: Optional[object] = None,
            memory_operation: Optional[str] = None) -> DefenseTestResult:
        """
        串联执行所有启用的层，返回最终结果。

        Args:
            ctx: 防御上下文 (含 content, source, trust_level 等)
            tool_call: L4 需要的工具调用对象
            memory_operation: "write" | "read" | "search" (L3 记忆操作类型)
        """
        t_start = time.perf_counter()
        layer_results: dict[str, Optional[dict]] = {}
        cumulative_risk = 0.0
        final_action = "pass"
        passed = True

        for layer in self._layer_order:
            layer_name = layer.value

            # 检查层是否启用
            if not self._enabled_layers.get(layer_name, False):
                layer_results[layer_name] = None
                continue

            detector = self._layers.get(layer)
            if detector is None:
                # 层尚未实现，跳过
                layer_results[layer_name] = None
                continue

            # 执行层检测
            # L3 (MEMORY_CONTROL): 传入 memory_operation
            if layer == DefenseLayer.MEMORY_CONTROL and memory_operation:
                # 推断 content_type 到 memory_operation
                mo = memory_operation or _content_type_to_memory_op(ctx.content_type)
                result = detector.evaluate(ctx, self.engine, memory_operation=mo)
            # L4 (TOOL_CONSTRAINT) 需要 tool_call 参数
            elif layer == DefenseLayer.TOOL_CONSTRAINT and tool_call is not None:
                result = detector.evaluate(ctx, self.engine, tool_call=tool_call)
            # L5 (DECISION_SUPERVISION) 需要前四层结果
            elif layer == DefenseLayer.DECISION_SUPERVISION:
                # 构建前序层结果字典 (排除 L5 自身)
                prior = {
                    name: r for name, r in ctx.layer_results.items()
                    if r is not None
                }
                result = detector.evaluate(ctx, self.engine, prior_layer_results=prior)
            else:
                result = detector.evaluate(ctx, self.engine)

            # 存储结果
            layer_results[layer_name] = self._result_to_dict(result)
            ctx.layer_results[layer_name] = result
            ctx.risk_scores[layer_name] = result.risk_score

            # 更新信任度
            ctx.trust_level = result.trust_level
            cumulative_risk = min(1.0, cumulative_risk + result.risk_score)

            # 根据模式判断是否短路
            if self._should_short_circuit(result, cumulative_risk):
                passed = False
                final_action = result.action if result.action in ("block", "quarantine") else "block"

                # 短路: 剩余层标为 None
                remaining = self._layer_order[self._layer_order.index(layer) + 1:]
                for rl in remaining:
                    layer_results.setdefault(rl.value, None)
                break

        # 更新最终状态
        ctx.final_risk_score = cumulative_risk
        if passed:
            ctx.final_verdict = "passed"
        elif final_action in ("block", "quarantine"):
            ctx.final_verdict = "blocked"
        else:
            ctx.final_verdict = "warned"

        total_elapsed = (time.perf_counter() - t_start) * 1000

        return DefenseTestResult(
            passed=passed,
            final_action=ctx.final_verdict,
            layer_results=layer_results,
            risk_score=min(cumulative_risk, 1.0),
            processing_time_ms=total_elapsed,
        )

    def _should_short_circuit(self, result: LayerCheckResult, cumulative_risk: float) -> bool:
        """判断是否应该短路"""
        if result.action in ("block", "quarantine"):
            if self.mode == DefenseMode.STRICT:
                return True
            if self.mode == DefenseMode.PERMISSIVE:
                return result.action == "block"
            # BALANCED: block 不单独短路，累积风险决定 → 继续检查累积风险

        if self.mode == DefenseMode.BALANCED and cumulative_risk >= BALANCED_THRESHOLD:
            return True

        return False

    # ---- 统计 ----

    def get_layer_stats(self) -> dict[str, LayerStats]:
        """获取各层统计 (需要层实现 stats 追踪)"""
        stats = {}
        for layer in self._layer_order:
            detector = self._layers.get(layer)
            if detector is not None:
                s = detector.get_stats() if hasattr(detector, 'get_stats') else None
                if s:
                    stats[layer.value] = s
        return stats

    # ---- 工具方法 ----

    @staticmethod
    def _result_to_dict(result: LayerCheckResult) -> dict:
        return {
            "layer": result.layer.value,
            "passed": result.passed,
            "action": result.action,
            "flags": result.flags,
            "risk_score": result.risk_score,
            "matched_rules": result.matched_rules,
            "processing_time_ms": result.processing_time_ms,
            "trust_level": result.trust_level,
        }

    def get_layer(self, layer: DefenseLayer) -> Optional[object]:
        """获取指定层的检测器实例 (供 adapter 调用 L3 API)"""
        return self._layers.get(layer)

    def reset(self):
        """重置所有层状态 (测试用)"""
        for detector in self._layers.values():
            if detector is not None and hasattr(detector, 'reset_state'):
                detector.reset_state()


def _content_type_to_memory_op(content_type: str) -> Optional[str]:
    """根据 content_type 推断 memory_operation"""
    mapping = {"memory_write": "write", "memory_read": "read", "memory_search": "search"}
    return mapping.get(content_type)
