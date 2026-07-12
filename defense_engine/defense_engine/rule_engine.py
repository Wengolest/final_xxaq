# ============================================================
# 防御规则引擎 — 核心脊柱
#
# 职责:
#   1. 规则优先级排序 (升序, priority 越小越优先)
#   2. 正则预编译与缓存
#   3. 条件表达式求值 (简化版)
#   4. 短路求值 (block/quarantine 立即返回)
#   5. 规则 CRUD (增删改查 + 启用/禁用)
#   6. 命中统计
#
# 使用方式:
#   engine = RuleEngine(rules)
#   matches = engine.evaluate(content="...", context={"trust_level": 0.5})
#   for m in matches:
#       if m.action == "block":
#           return False  # 被拦截
# ============================================================

import re
import time
from typing import Any, Optional
from dataclasses import dataclass, field

try:
    from .defense_types import DefenseRule, RuleAction, PatternType
except ImportError:
    from defense_types import DefenseRule, RuleAction, PatternType


@dataclass
class RuleMatch:
    """规则匹配结果"""
    rule_id: str
    matched: bool
    action: str
    reason: str
    priority: int
    content_snippet: str = ""     # 命中的内容片段
    processing_time_us: float = 0.0


class RuleEngine:
    """优先级排序 + 短路求值的规则匹配引擎"""

    # 动作优先级 (用于短路判断: block 和 quarantine 立即返回)
    SHORT_CIRCUIT_ACTIONS = {"block", "quarantine"}

    def __init__(self, rules: list[dict]):
        """
        初始化规则引擎
        Args:
            rules: 规则字典列表, 每条包含 rule_id, pattern_type, pattern, action, priority 等
        """
        self._rules: list[dict] = sorted(rules, key=lambda r: r.get("priority", 99))
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._hit_counts: dict[str, int] = {}          # rule_id → hit count
        self._last_hit_at: dict[str, float] = {}       # rule_id → last hit timestamp
        self._precompile()

    # ---- 初始化 ----

    def _precompile(self):
        """预编译所有 regex 类型规则的 pattern"""
        for rule in self._rules:
            rid = rule.get("rule_id", "")
            if rule.get("pattern_type") in ("regex", "structural") and rule.get("pattern", "").strip():
                try:
                    self._compiled_patterns[rid] = re.compile(
                        rule["pattern"], re.IGNORECASE | re.DOTALL
                    )
                except re.error:
                    # 跳过无效正则，不中断整个引擎初始化
                    self._compiled_patterns[rid] = None

    # ---- 核心匹配 ----

    def evaluate(self, content: str, context: Optional[dict] = None,
                 layer_prefix: Optional[str] = None) -> list[RuleMatch]:
        """
        按优先级依次评估所有启用的规则，支持短路求值。

        Args:
            content: 待检测的文本内容
            context: 上下文变量 (e.g. {"trust_level": 0.5, "source": "user_upload", ...})
            layer_prefix: 可选层前缀过滤 ("SG"|"MI"|"MC"|"TC"|"DS"), 仅评估匹配的规则

        Returns:
            命中的规则匹配列表。block/quarantine 类型命中时立即短路返回单元素列表。
        """
        ctx = context or {}
        matches: list[RuleMatch] = []

        for rule in self._rules:
            # 层前缀过滤
            if layer_prefix and not rule.get("rule_id", "").startswith(layer_prefix):
                continue
            if not rule.get("enabled", True):
                continue

            t_start = time.perf_counter_ns()

            # 1. 条件检查 (condition 字段)
            if rule.get("condition") and not self._eval_condition(rule["condition"], ctx):
                continue

            # 2. 模式匹配
            matched, snippet = self._match_rule(rule, content, ctx)

            elapsed_us = (time.perf_counter_ns() - t_start) / 1000

            if matched:
                rid = rule.get("rule_id", "unknown")
                match = RuleMatch(
                    rule_id=rid,
                    matched=True,
                    action=rule.get("action", "log"),
                    reason=self._build_reason(rule),
                    priority=rule.get("priority", 99),
                    content_snippet=snippet[:200],
                    processing_time_us=elapsed_us,
                )
                matches.append(match)

                # 更新命中统计
                self._hit_counts[rid] = self._hit_counts.get(rid, 0) + 1
                self._last_hit_at[rid] = time.time()

                # 短路: block 和 quarantine 动作立即返回
                if rule.get("action") in self.SHORT_CIRCUIT_ACTIONS:
                    return [match]

        return matches

    def _match_rule(self, rule: dict, content: str, context: dict) -> tuple[bool, str]:
        """对单条规则执行模式匹配。返回 (是否命中, 命中片段)"""
        pattern_type = rule.get("pattern_type", "regex")
        pattern = rule.get("pattern", "")

        try:
            if pattern_type == "regex":
                return self._match_regex(rule["rule_id"], content)
            elif pattern_type == "keyword":
                return self._match_keyword(pattern, content)
            elif pattern_type == "condition":
                # 纯条件规则，condition 已在 evaluate 中评估
                return True, ""
            elif pattern_type == "structural":
                return self._match_regex(rule["rule_id"], content)
            elif pattern_type == "composite":
                # 复合: 先检查 condition，再尝试 regex
                matched, snippet = self._match_regex(rule["rule_id"], content) if rule["rule_id"] in self._compiled_patterns else (False, "")
                return matched, snippet
            elif pattern_type == "semantic":
                # 语义检测预留接口 — 由外部 ML 检测器处理
                return False, ""
            else:
                return False, ""
        except (ValueError, TypeError, KeyError):
            return False, ""

    def _match_regex(self, rule_id: str, content: str) -> tuple[bool, str]:
        """正则匹配"""
        pat = self._compiled_patterns.get(rule_id)
        if pat is None:
            return False, ""
        m = pat.search(content)
        if m:
            start = max(0, m.start() - 20)
            end = min(len(content), m.end() + 20)
            return True, content[start:end]
        return False, ""

    @staticmethod
    def _match_keyword(pattern: str, content: str) -> tuple[bool, str]:
        """关键词匹配 (逗号分隔的关键词列表)"""
        keywords = [kw.strip() for kw in pattern.split(",") if kw.strip()]
        for kw in keywords:
            pos = content.find(kw)
            if pos != -1:
                start = max(0, pos - 10)
                end = min(len(content), pos + len(kw) + 10)
                return True, content[start:end]
        return False, ""

    @staticmethod
    def _build_reason(rule: dict) -> str:
        """构造命中原因的简短描述"""
        ptype = rule.get("pattern_type", "regex")
        pattern = rule.get("pattern", "")
        short = pattern[:80].replace("\n", " ")
        return f"[{rule.get('rule_id')}] {rule.get('name', '')} — {ptype}: {short}"

    # ---- 条件表达式求值 ----

    @staticmethod
    def _eval_condition(condition: str, context: dict) -> bool:
        """
        简化版条件表达式求值器。
        支持的表达式: 简单比较和逻辑运算
          e.g. "trust_level < 0.5"
               "source != 'internal_db'"
               "trust_level < 0.5 AND source != 'internal_db'"
               "file_size > 52428800"
        """
        try:
            expr = condition
            # 变量替换 — 将 context 中的 key 替换为 Python 字面量
            for key, value in sorted(context.items(), key=lambda x: -len(x[0])):
                if isinstance(value, str):
                    expr = expr.replace(key, repr(value))
                elif isinstance(value, bool):
                    expr = expr.replace(key, str(value))
                elif isinstance(value, (int, float)):
                    expr = expr.replace(key, str(value))

            # 将 SQL 风格的 AND/OR/NOT 转为 Python 风格
            expr = expr.replace(" AND ", " and ")
            expr = expr.replace(" OR ", " or ")
            expr = expr.replace(" NOT ", " not ")

            # 安全求值 (仅允许内置常量)
            result = eval(expr, {"__builtins__": {}}, {})
            return bool(result)
        except (ValueError, SyntaxError, TypeError, NameError):
            # 条件解析失败时默认跳过该规则 (fail-safe: 不因错误配置而阻断)
            return False

    # ---- 规则 CRUD ----

    def add_rule(self, rule: dict):
        """添加规则并重新排序"""
        rule.setdefault("enabled", True)
        rule.setdefault("priority", 99)
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.get("priority", 99))
        # 预编译 (如果是 regex 类型)
        rid = rule.get("rule_id", "")
        if rule.get("pattern_type") in ("regex", "structural") and rid:
            try:
                self._compiled_patterns[rid] = re.compile(
                    rule["pattern"], re.IGNORECASE | re.DOTALL
                )
            except re.error:
                self._compiled_patterns[rid] = None

    def remove_rule(self, rule_id: str) -> bool:
        """删除规则。返回是否成功"""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.get("rule_id") != rule_id]
        self._compiled_patterns.pop(rule_id, None)
        self._hit_counts.pop(rule_id, None)
        self._last_hit_at.pop(rule_id, None)
        return len(self._rules) < before

    def update_rule(self, rule_id: str, updates: dict) -> bool:
        """更新规则的部分字段"""
        for rule in self._rules:
            if rule.get("rule_id") == rule_id:
                rule.update(updates)
                # 如果 pattern 变了，重新编译
                if "pattern" in updates and rule.get("pattern_type") in ("regex", "structural"):
                    try:
                        self._compiled_patterns[rule_id] = re.compile(
                            rule["pattern"], re.IGNORECASE | re.DOTALL
                        )
                    except re.error:
                        self._compiled_patterns[rule_id] = None
                # 如果 priority 变了，重新排序
                if "priority" in updates:
                    self._rules.sort(key=lambda r: r.get("priority", 99))
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        return self._set_enabled(rule_id, True)

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        return self._set_enabled(rule_id, False)

    def _set_enabled(self, rule_id: str, enabled: bool) -> bool:
        for rule in self._rules:
            if rule.get("rule_id") == rule_id:
                rule["enabled"] = enabled
                return True
        return False

    # ---- 查询 ----

    def get_rule(self, rule_id: str) -> Optional[dict]:
        """获取单条规则"""
        for rule in self._rules:
            if rule.get("rule_id") == rule_id:
                return rule.copy()
        return None

    def get_all_rules(self) -> list[dict]:
        """获取所有规则 (按优先级排序)"""
        return [r.copy() for r in self._rules]

    def get_rules_by_layer(self, layer_prefix: str) -> list[dict]:
        """
        按层过滤规则 (根据 rule_id 前缀匹配)
        layer_prefix: "SG" | "MI" | "MC" | "TC" | "DS"
        """
        return [r.copy() for r in self._rules if r.get("rule_id", "").startswith(layer_prefix)]

    # ---- 统计 ----

    def get_hit_stats(self) -> dict[str, dict]:
        """获取规则命中统计"""
        return {
            rid: {
                "hits": self._hit_counts.get(rid, 0),
                "last_hit_at": self._last_hit_at.get(rid),
            }
            for rid in self._hit_counts
        }

    def reset_stats(self):
        """重置统计"""
        self._hit_counts.clear()
        self._last_hit_at.clear()

    @property
    def rule_count(self) -> int:
        """规则总数"""
        return len(self._rules)

    @property
    def enabled_rule_count(self) -> int:
        """启用的规则数"""
        return sum(1 for r in self._rules if r.get("enabled", True))
