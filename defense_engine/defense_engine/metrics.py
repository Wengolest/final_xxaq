# ============================================================
# 防御指标引擎 — DSR / FPR / FNR / 拦截率统计
#
# 职责:
#   1. 记录每次防御检测结果
#   2. 计算防御成功率 (DSR)
#   3. 计算误报率 (FPR) 和漏报率 (FNR)
#   4. 各层拦截率
#   5. 规则命中分布
#   6. 攻击族覆盖度
#   7. 延迟统计
#
# 指标定义 (参考设计文档 §9):
#   DSR = 成功拦截的攻击数 / 总攻击数
#   FPR = 误拦截的正常请求数 / 总正常请求数
#   FNR = 漏过的攻击数 / 总攻击数
#   Layer Intercept Rate = 该层拦截数 / 总通过该层的请求数
#
# 使用方式:
#   from metrics import DefenseMetrics
#   metrics = DefenseMetrics()
#   metrics.record(result, is_attack=True, attack_family="prompt_injection")
#   summary = metrics.summary()
# ============================================================

import time
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class MetricRecord:
    """单次检测记录"""
    timestamp: float
    is_attack: bool                        # 是否已知攻击样本
    attack_family: str                     # attack family or "benign"
    verdict: str                           # passed | blocked | warned
    risk_score: float
    blocking_layer: str                    # 哪个层拦截的 (空=放行)
    matched_rules: list[str]
    processing_time_ms: float
    layers_hit: dict[str, bool]            # 哪些层触发了检查


@dataclass
class MetricsSummary:
    """指标汇总"""
    total_samples: int = 0
    attack_samples: int = 0
    benign_samples: int = 0

    # DSR / FPR / FNR
    dsr: float = 0.0                       # Defense Success Rate
    fpr: float = 0.0                       # False Positive Rate
    fnr: float = 0.0                       # False Negative Rate

    # 各层
    layer_intercept_rates: dict[str, float] = field(default_factory=dict)
    layer_block_counts: dict[str, int] = field(default_factory=dict)

    # 规则
    rule_hit_counts: dict[str, int] = field(default_factory=dict)
    top_rules: list[tuple[str, int]] = field(default_factory=list)

    # 攻击族
    attack_family_dsr: dict[str, float] = field(default_factory=dict)
    attack_family_counts: dict[str, int] = field(default_factory=dict)

    # 延迟
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


class DefenseMetrics:
    """防御指标收集器"""

    def __init__(self):
        self._records: list[MetricRecord] = []
        self._started_at: float = time.time()

    # ---- 记录 ----

    def record(
        self,
        result: any,                         # DefenseTestResult
        is_attack: bool = False,
        attack_family: str = "unknown",
    ):
        """
        记录一次防御检测结果。

        Args:
            result: DefenseTestResult from orchestrator.run()
            is_attack: 该样本是否已知为攻击
            attack_family: 攻击族 (e.g. "prompt_injection")
        """
        blocking_layer = self._find_blocking_layer(result)
        matched_rules: list[str] = []
        layers_hit: dict[str, bool] = {}

        for name, lr in result.layer_results.items():
            if lr is not None:
                layers_hit[name] = True
                if isinstance(lr, dict):
                    matched_rules.extend(lr.get("matched_rules", []))
                elif hasattr(lr, 'matched_rules'):
                    matched_rules.extend(lr.matched_rules)

        self._records.append(MetricRecord(
            timestamp=time.time(),
            is_attack=is_attack,
            attack_family=attack_family if is_attack else "benign",
            verdict=self._normalize_verdict(result.final_action),
            risk_score=result.risk_score,
            blocking_layer=blocking_layer,
            matched_rules=list(set(matched_rules)),
            processing_time_ms=result.processing_time_ms,
            layers_hit=layers_hit,
        ))

    def record_verdict(
        self, verdict: str, risk_score: float = 0.0,
        is_attack: bool = False, attack_family: str = "unknown",
        blocking_layer: str = "", matched_rules: Optional[list[str]] = None,
        processing_time_ms: float = 0.0,
    ):
        """直接记录判决结果 (用于手动标记)"""
        self._records.append(MetricRecord(
            timestamp=time.time(),
            is_attack=is_attack,
            attack_family=attack_family if is_attack else "benign",
            verdict=self._normalize_verdict(verdict),
            risk_score=risk_score,
            blocking_layer=blocking_layer,
            matched_rules=matched_rules or [],
            processing_time_ms=processing_time_ms,
            layers_hit={},
        ))

    # ---- 计算 ----

    @staticmethod
    def _normalize_verdict(verdict: str) -> str:
        """标准化判决值，映射 pass/block/warn → passed/blocked/warned"""
        mapping = {
            "pass": "passed", "block": "blocked", "warn": "warned",
            "quarantine": "blocked", "filter": "passed", "rewrite": "passed",
            "log": "passed",
        }
        return mapping.get(verdict, verdict)

    def summary(self) -> MetricsSummary:
        """计算全部指标"""
        s = MetricsSummary()
        attacks = [r for r in self._records if r.is_attack]
        benigns = [r for r in self._records if not r.is_attack]

        s.total_samples = len(self._records)
        s.attack_samples = len(attacks)
        s.benign_samples = len(benigns)

        # DSR: 攻击被拦截的比例
        if attacks:
            blocked_attacks = sum(1 for r in attacks
                                  if r.verdict in ("blocked", "quarantine"))
            s.dsr = blocked_attacks / len(attacks)

        # FPR: 正常请求被误拦截的比例
        if benigns:
            false_positives = sum(1 for r in benigns
                                  if r.verdict in ("blocked", "quarantine"))
            s.fpr = false_positives / len(benigns)

        # FNR: 攻击被漏过的比例 (= 1 - DSR)
        if attacks:
            missed_attacks = sum(1 for r in attacks
                                 if r.verdict == "passed")
            s.fnr = missed_attacks / len(attacks)

        # 各层拦截率
        s.layer_intercept_rates = self.layer_intercept_rates()

        # 各层阻断计数
        s.layer_block_counts = self.layer_block_counts()

        # 规则命中分布
        s.rule_hit_counts = self.rule_hit_distribution()
        s.top_rules = sorted(s.rule_hit_counts.items(),
                             key=lambda x: x[1], reverse=True)[:10]

        # 攻击族 DSR
        s.attack_family_dsr = self.attack_family_dsr()
        family_counts = defaultdict(int)
        for r in attacks:
            family_counts[r.attack_family] += 1
        s.attack_family_counts = dict(family_counts)

        # 延迟统计
        latencies = [r.processing_time_ms for r in self._records
                     if r.processing_time_ms > 0]
        if latencies:
            s.avg_latency_ms = sum(latencies) / len(latencies)
            sorted_l = sorted(latencies)
            s.p50_latency_ms = sorted_l[len(sorted_l) // 2]
            s.p99_latency_ms = sorted_l[int(len(sorted_l) * 0.99)]

        return s

    def layer_intercept_rates(self) -> dict[str, float]:
        """各层拦截率 = 该层拦截数 / 通过该层的总数"""
        layer_order = ["source_governance", "model_interaction",
                       "memory_control", "tool_constraint",
                       "decision_supervision"]
        rates = {}
        for name in layer_order:
            blocked = sum(1 for r in self._records
                          if r.blocking_layer == name)
            trigger_total = sum(1 for r in self._records
                                if name in r.layers_hit)
            if trigger_total > 0:
                rates[name] = blocked / trigger_total
            else:
                rates[name] = 0.0
        return rates

    def layer_block_counts(self) -> dict[str, int]:
        """各层阻断绝对计数"""
        counts = defaultdict(int)
        for r in self._records:
            if r.blocking_layer:
                counts[r.blocking_layer] += 1
        return dict(counts)

    def rule_hit_distribution(self) -> dict[str, int]:
        """规则命中分布"""
        dist = defaultdict(int)
        for r in self._records:
            for rule_id in r.matched_rules:
                dist[rule_id] += 1
        return dict(dist)

    def attack_family_dsr(self) -> dict[str, float]:
        """按攻击族的 DSR"""
        attacks = [r for r in self._records if r.is_attack]
        family_attacks = defaultdict(list)
        for r in attacks:
            family_attacks[r.attack_family].append(r)

        return {
            family: sum(1 for r in recs
                        if r.verdict in ("blocked", "quarantine")) / len(recs)
            for family, recs in family_attacks.items()
            if recs
        }

    def latency_stats(self) -> dict[str, float]:
        """延迟统计"""
        s = self.summary()
        return {
            "avg_ms": s.avg_latency_ms,
            "p50_ms": s.p50_latency_ms,
            "p99_ms": s.p99_latency_ms,
        }

    # ---- 查询 ----

    def get_records(self, limit: int = 100) -> list[MetricRecord]:
        return self._records[-limit:]

    def get_confusion_matrix(self) -> dict:
        """混淆矩阵"""
        tp = 0  # 攻击被拦截 (True Positive)
        fn = 0  # 攻击被放行 (False Negative)
        fp = 0  # 正常被拦截 (False Positive)
        tn = 0  # 正常被放行 (True Negative)

        for r in self._records:
            if r.is_attack:
                if r.verdict in ("blocked", "quarantine"):
                    tp += 1
                else:
                    fn += 1
            else:
                if r.verdict in ("blocked", "quarantine"):
                    fp += 1
                else:
                    tn += 1

        total = tp + fn + fp + tn
        return {
            "true_positive": tp,
            "false_negative": fn,
            "false_positive": fp,
            "true_negative": tn,
            "accuracy": (tp + tn) / max(1, total),
            "precision": tp / max(1, tp + fp),
            "recall": tp / max(1, tp + fn),
            "f1": 2 * tp / max(1, 2 * tp + fp + fn),
        }

    def reset(self):
        self._records.clear()
        self._started_at = time.time()

    @property
    def total(self) -> int:
        return len(self._records)

    # ---- 内部 ----

    @staticmethod
    def _find_blocking_layer(result: any) -> str:
        """找到第一个拦截层"""
        order = ["source_governance", "model_interaction", "memory_control",
                 "tool_constraint", "decision_supervision"]
        for name in order:
            lr = result.layer_results.get(name)
            if lr:
                if isinstance(lr, dict) and not lr.get("passed", True):
                    return name
                if hasattr(lr, 'passed') and not lr.passed:
                    return name
        return ""

    # ---- 命令行报表 ----

    def print_report(self):
        """打印可读的指标报告"""
        s = self.summary()
        cm = self.get_confusion_matrix()

        print("=" * 65)
        print("  DEFENSE METRICS REPORT")
        print("=" * 65)
        print(f"  Total samples:     {s.total_samples:>5d}  "
              f"(attacks: {s.attack_samples}, benign: {s.benign_samples})")
        print(f"  DSR (拦截率):       {s.dsr:>6.1%}")
        print(f"  FPR (误报率):       {s.fpr:>6.1%}")
        print(f"  FNR (漏报率):       {s.fnr:>6.1%}")
        print()
        print(f"  Accuracy:           {cm['accuracy']:>6.1%}")
        print(f"  Precision:          {cm['precision']:>6.1%}")
        print(f"  Recall:             {cm['recall']:>6.1%}")
        print(f"  F1 Score:           {cm['f1']:>6.1%}")
        print()
        print(f"  Confusion Matrix:")
        print(f"    TP={cm['true_positive']:>4d}  FN={cm['false_negative']:>4d}")
        print(f"    FP={cm['false_positive']:>4d}  TN={cm['true_negative']:>4d}")
        print()
        print(f"  Layer Intercept Rates:")
        for name, rate in s.layer_intercept_rates.items():
            count = s.layer_block_counts.get(name, 0)
            print(f"    {name:<25s}  {rate:>6.1%}  (blocks: {count})")
        print()
        print(f"  Top Rules:")
        for rule_id, count in s.top_rules[:5]:
            print(f"    {rule_id:<30s}  hits: {count}")
        print()
        print(f"  Latency:  avg={s.avg_latency_ms:.1f}ms  "
              f"p50={s.p50_latency_ms:.1f}ms  p99={s.p99_latency_ms:.1f}ms")
        print("=" * 65)
