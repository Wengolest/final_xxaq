# ============================================================
# L5: 决策监督与多源验证
#
# 职责: 在所有其他防御层之后，对 Agent 的最终决策进行审计和仲裁
# 防护机制:
#   1. 多源交叉验证 (对比多数据源的一致性)
#   2. 逐层结果审计 (汇总前四层的风险信号)
#   3. 熔断机制 (连续阻断 / 高风险比率)
#   4. 异常行为检测 (行为模式偏离基线)
#   5. 最终决策仲裁 (block / warn / pass)
#
# 使用方式:
#   from layer5_decision_supervision import DecisionSupervision
#   l5 = DecisionSupervision(params)
#   result = l5.evaluate(context, engine, layer_results=prior_results)
# ============================================================

import time
from typing import Optional, Any
from dataclasses import dataclass, field
from collections import deque

try:
    from .defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from .scoring import compute_layer_result, CheckFlag
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from scoring import compute_layer_result, CheckFlag


# ---- 默认参数 ----

DEFAULT_AUDIT_THRESHOLD = 0.7       # 审计风险分阈值
DEFAULT_VOTE_THRESHOLD = 0.6       # 多源一致性阈值
DEFAULT_CONSECUTIVE_BLOCK_MAX = 3  # 连续阻断熔断限
DEFAULT_HIGH_RISK_WINDOW = 10      # 高风险比率滑动窗口
DEFAULT_HIGH_RISK_RATIO = 0.5      # 高风险比率阈值


@dataclass
class DecisionCheck:
    """单次决策检查标志"""
    check_type: str
    severity: str
    description: str
    snippet: str = ""


@dataclass
class AuditRecord:
    """审计记录"""
    timestamp: float
    run_id: str
    risk_score: float
    action: str
    prior_blocks: int
    prior_warns: int
    layers_triggered: list[str]


class DecisionSupervision:
    """L5 决策监督与多源验证检测器"""

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.audit_threshold: float = p.get("audit_threshold", DEFAULT_AUDIT_THRESHOLD)
        self.vote_threshold: float = p.get("vote_threshold", DEFAULT_VOTE_THRESHOLD)
        self.consecutive_block_max: int = p.get("consecutive_block_max", DEFAULT_CONSECUTIVE_BLOCK_MAX)
        self.high_risk_window: int = p.get("high_risk_window", DEFAULT_HIGH_RISK_WINDOW)
        self.high_risk_ratio: float = p.get("high_risk_ratio", DEFAULT_HIGH_RISK_RATIO)

        # 运行时状态
        self._recent_decisions: deque[dict] = deque(maxlen=self.high_risk_window)
        self._consecutive_blocks: int = 0
        self._audit_log: list[AuditRecord] = []
        self._circuit_open: bool = False
        self._circuit_until: float = 0.0

    # ---- 主入口 ----

    def evaluate(
        self, ctx: DefenseContext, engine: Optional[object] = None,
        prior_layer_results: Optional[dict[str, LayerCheckResult]] = None,
    ) -> LayerCheckResult:
        """
        对全部前序防御层的结果进行审计和最终仲裁。

        Args:
            ctx: 防御上下文
            engine: RuleEngine 实例
            prior_layer_results: 前四层的检查结果 {layer_name: LayerCheckResult}

        Returns:
            LayerCheckResult
        """
        t_start = time.perf_counter()
        checks: list[DecisionCheck] = []

        # 收集中间结果
        prior = prior_layer_results or ctx.layer_results
        prior_flags: list[str] = []
        prior_blocks = 0
        prior_warns = 0
        cumulative_risk = 0.0

        for layer_name, result in prior.items():
            if result is None:
                continue
            if hasattr(result, 'flags'):
                prior_flags.extend(result.flags)
            if hasattr(result, 'risk_score'):
                cumulative_risk = min(1.0, cumulative_risk + result.risk_score)
            if hasattr(result, 'action'):
                if result.action in ("block", "quarantine"):
                    prior_blocks += 1
                elif result.action == "warn":
                    prior_warns += 1

        # 1. 熔断检查
        checks.append(self._check_circuit_breaker())

        # 2. 多源交叉验证
        checks.append(self._check_cross_validation(ctx, prior))

        # 3. 审计复核
        checks.append(self._check_audit(cumulative_risk, prior_blocks, prior_warns))

        # 4. 异常检测
        checks.append(self._check_anomaly(prior_blocks, prior_warns, prior_flags))

        # 5. 最终仲裁
        checks.append(self._check_final_arbitration(cumulative_risk, prior_blocks))

        # 6. 更新运行时状态
        self._update_state(cumulative_risk, prior_blocks, prior_warns, ctx)

        # 7. 规则引擎
        rule_matches = []
        if engine is not None:
            context_dict = {
                "trust_level": ctx.trust_level,
                "source": ctx.source,
                "content_type": ctx.content_type,
                "cumulative_risk": cumulative_risk,
                "prior_blocks": prior_blocks,
                "consecutive_blocks": self._consecutive_blocks,
                "high_risk_ratio": self._get_high_risk_ratio(),
                "audit_risk_score": cumulative_risk,
                "source_weight_divergence": max(0, cumulative_risk - ctx.trust_level),
            }
            if hasattr(ctx, 'extra'):
                context_dict.update(ctx.extra)
            rule_matches = engine.evaluate(ctx.content, context_dict, layer_prefix="DS")

        return self._summarize(checks, rule_matches, t_start, ctx.trust_level, content=ctx.content)

    # ---- 单项检查 ----

    def _check_circuit_breaker(self) -> DecisionCheck:
        """熔断检查 — 检查是否处于熔断状态"""
        if self._circuit_open:
            if time.time() < self._circuit_until:
                return DecisionCheck(
                    "circuit_breaker", "block",
                    f"熔断器开启中，剩余 {(self._circuit_until - time.time()):.0f}s 后恢复",
                )
            else:
                # 熔断恢复 — 进入半开状态
                self._circuit_open = False
                self._consecutive_blocks = 0
                return DecisionCheck(
                    "circuit_breaker", "warn",
                    "熔断器已恢复 (半开状态)",
                )

        # 检查连续阻断数
        if self._consecutive_blocks >= self.consecutive_block_max:
            self._open_circuit()
            return DecisionCheck(
                "circuit_breaker", "block",
                f"连续 {self._consecutive_blocks} 次阻断，触发熔断 60s",
            )

        return DecisionCheck("circuit_breaker", "pass", "")

    def _check_cross_validation(
        self, ctx: DefenseContext, prior: dict
    ) -> DecisionCheck:
        """
        多源交叉验证 — 检查不同层之间对同一内容的风险判断是否一致。

        当多层的风险判断高度分散时（有的阻断有的放行），提示需要人工审查。
        """
        actions: list[str] = []
        for result in prior.values():
            if result is not None and hasattr(result, 'action'):
                actions.append(result.action)

        if len(actions) < 2:
            return DecisionCheck("cross_validation", "pass", "层数不足，跳过多源验证")

        blocks = sum(1 for a in actions if a in ("block", "quarantine"))
        warns = sum(1 for a in actions if a == "warn")
        passes = sum(1 for a in actions if a == "pass")

        total = len(actions)
        if blocks > 0 and passes > 0:
            # 有层阻断有层放行 → 意见分裂
            return DecisionCheck(
                "cross_validation", "warn",
                f"多源意见分裂: {blocks} block, {warns} warn, {passes} pass",
            )
        elif blocks / total >= self.vote_threshold:
            return DecisionCheck(
                "cross_validation", "block",
                f"多源一致阻断 ({blocks}/{total})",
            )
        elif warns / total >= self.vote_threshold:
            return DecisionCheck(
                "cross_validation", "warn",
                f"多源一致告警 ({warns}/{total})",
            )

        return DecisionCheck("cross_validation", "pass",
                             f"多源一致通过 ({passes}/{total})")

    def _check_audit(self, cumulative_risk: float, prior_blocks: int,
                     prior_warns: int) -> DecisionCheck:
        """审计复核 — 高风险决策需要额外审计"""
        if cumulative_risk >= self.audit_threshold:
            return DecisionCheck(
                "audit_review", "block",
                f"累积风险 {cumulative_risk:.2f} 超过审计阈值 {self.audit_threshold}，"
                f"({prior_blocks} block, {prior_warns} warn)",
            )
        elif cumulative_risk >= self.audit_threshold * 0.7:
            return DecisionCheck(
                "audit_review", "warn",
                f"累积风险 {cumulative_risk:.2f} 接近审计阈值",
            )
        return DecisionCheck("audit_review", "pass", "")

    def _check_anomaly(self, prior_blocks: int, prior_warns: int,
                       prior_flags: list[str]) -> DecisionCheck:
        """异常行为检测 — 检测偏离历史基线的行为模式"""
        # 检查高风险比率
        ratio = self._get_high_risk_ratio()
        if len(self._recent_decisions) >= 5 and ratio >= self.high_risk_ratio:
            return DecisionCheck(
                "anomaly_detection", "warn",
                f"近期高风险比率异常: {ratio:.1%} (> {self.high_risk_ratio:.1%}) "
                f"in last {len(self._recent_decisions)} decisions",
            )

        # 检查是否出现全新的 flags 类型 (未见过的攻击模式)
        if len(self._recent_decisions) >= 10:
            known_flag_types: set[str] = set()
            for d in self._recent_decisions:
                known_flag_types.update(d.get("flag_types", []))
            new_flag_types = set(prior_flags) - known_flag_types
            if len(new_flag_types) >= 3:
                return DecisionCheck(
                    "anomaly_detection", "warn",
                    f"检测到 {len(new_flag_types)} 种新型风险标志: "
                    f"{', '.join(list(new_flag_types)[:3])}",
                )

        return DecisionCheck("anomaly_detection", "pass", "")

    def _check_final_arbitration(self, cumulative_risk: float,
                                  prior_blocks: int) -> DecisionCheck:
        """最终决策仲裁"""
        if self._circuit_open:
            return DecisionCheck(
                "final_arbitration", "block",
                "熔断器开启，拒绝所有请求",
            )
        if prior_blocks >= 2:
            return DecisionCheck(
                "final_arbitration", "block",
                f"多 {prior_blocks} 层触发阻断，最终判定: block",
            )
        if cumulative_risk >= self.audit_threshold:
            return DecisionCheck(
                "final_arbitration", "block",
                f"累积风险 {cumulative_risk:.2f} 超标，最终判定: block",
            )
        if cumulative_risk >= 0.3:
            return DecisionCheck(
                "final_arbitration", "warn",
                f"累积风险 {cumulative_risk:.2f}，最终判定: warn",
            )
        return DecisionCheck(
            "final_arbitration", "pass",
            f"累积风险 {cumulative_risk:.2f}，最终判定: pass",
        )

    # ---- 运行时状态 ----

    def _update_state(self, cumulative_risk: float, prior_blocks: int,
                      prior_warns: int, ctx: DefenseContext):
        """更新运行时统计状态"""
        action = "pass"
        if prior_blocks > 0:
            action = "block"
            self._consecutive_blocks += 1
        elif cumulative_risk >= 0.3:
            action = "warn"
            self._consecutive_blocks = 0
        else:
            self._consecutive_blocks = 0

        # 记录审计日志
        self._audit_log.append(AuditRecord(
            timestamp=time.time(),
            run_id=getattr(ctx, 'run_id', ''),
            risk_score=cumulative_risk,
            action=action,
            prior_blocks=prior_blocks,
            prior_warns=prior_warns,
            layers_triggered=[
                name for name, r in ctx.layer_results.items()
                if r is not None and getattr(r, 'action', 'pass') != 'pass'
            ],
        ))

        # 滑动窗口记录
        flag_types = []
        for r in ctx.layer_results.values():
            if r is not None and hasattr(r, 'flags'):
                for f in r.flags:
                    # 提取 flag 类型前缀 (如 "[SG-zero_width_char]")
                    if f.startswith('['):
                        flag_types.append(f.split(']')[0] if ']' in f else f[:30])
        self._recent_decisions.append({
            "risk_score": cumulative_risk,
            "action": action,
            "flag_types": flag_types,
        })

    def _get_high_risk_ratio(self) -> float:
        """计算近期高风险决策比例"""
        if not self._recent_decisions:
            return 0.0
        high_risk = sum(
            1 for d in self._recent_decisions
            if d["action"] in ("block", "quarantine")
        )
        return high_risk / len(self._recent_decisions)

    def _open_circuit(self, duration: float = 60.0):
        """开启熔断"""
        self._circuit_open = True
        self._circuit_until = time.time() + duration

    # ---- 查询 ----

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return [
            {
                "timestamp": a.timestamp,
                "run_id": a.run_id,
                "risk_score": a.risk_score,
                "action": a.action,
                "prior_blocks": a.prior_blocks,
                "prior_warns": a.prior_warns,
                "layers_triggered": a.layers_triggered,
            }
            for a in self._audit_log[-limit:]
        ]

    def get_state(self) -> dict:
        return {
            "circuit_open": self._circuit_open,
            "circuit_until": self._circuit_until,
            "consecutive_blocks": self._consecutive_blocks,
            "high_risk_ratio": self._get_high_risk_ratio(),
            "recent_decision_count": len(self._recent_decisions),
            "total_audits": len(self._audit_log),
        }

    def reset_state(self):
        """重置运行时状态 (用于测试)"""
        self._recent_decisions.clear()
        self._consecutive_blocks = 0
        self._audit_log.clear()
        self._circuit_open = False
        self._circuit_until = 0.0

    # ---- 结果汇总 ----

    def _checks_to_flags(self, checks: list[DecisionCheck]) -> list[CheckFlag]:
        return [
            CheckFlag(
                check_type=c.check_type,
                severity=c.severity,
                description=c.description,
                source="programmatic",
            )
            for c in checks if c.severity != "pass"
        ]

    def _rule_matches_to_flags(self, rule_matches: list) -> list[CheckFlag]:
        flags = []
        for m in rule_matches:
            flags.append(CheckFlag(
                check_type=m.rule_id,
                severity=m.action,
                description=m.reason,
                source="rule",
                rule_id=m.rule_id,
            ))
        return flags

    def _summarize(self, checks, rule_matches, t_start, trust_level, content=None):
        all_flags = self._checks_to_flags(checks) + self._rule_matches_to_flags(rule_matches)
        return compute_layer_result(
            layer=DefenseLayer.DECISION_SUPERVISION,
            flags=all_flags,
            trust_in=trust_level,
            t_start=t_start,
            content=content,
        )
