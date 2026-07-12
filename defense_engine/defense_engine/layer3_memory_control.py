# ============================================================
# L3: 记忆读写安全控制
#
# 职责: 防止恶意内容通过记忆系统在跨会话中长期持续影响 Agent
# 架构: Route B — 代理/拦截器模式 (MemoryBackend ABC)
# 防护机制:
#   1. 写入风险检测 (复用 L1 检测模式)
#   2. 来源标注 (每条记忆附加元数据)
#   3. 读取筛选 (TTL / quarantine / trust 排序)
#   4. 冲突检测 (关键词/模式级)
#   5. TTL 过期管理
#   6. 隔离区管理 (quarantine)
#
# 使用方式:
#   from layer3_memory_control import MemoryControl, SimulatedMemoryBackend
#   backend = SimulatedMemoryBackend()
#   l3 = MemoryControl(backend, params)
#   result = l3.evaluate(context, engine)
# ============================================================

import re
import time
import hashlib
from typing import Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

try:
    from .defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from .scoring import compute_layer_result, CheckFlag
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from scoring import compute_layer_result, CheckFlag


# ---- 记忆条目数据结构 ----

@dataclass
class MemoryEntry:
    """单条记忆条目"""
    entry_id: str
    content: str
    source: str = "unknown"
    source_trust: float = 0.5
    task_context: str = ""
    written_at: float = 0.0
    ttl: int = 86400                       # 秒, 默认 24h
    tags: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    status: str = "active"                 # active | quarantined | archived | stale

    def __post_init__(self):
        if self.written_at == 0.0:
            self.written_at = time.time()

    def is_expired(self, now: Optional[float] = None) -> bool:
        now = now or time.time()
        return (now - self.written_at) > self.ttl

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "source": self.source,
            "source_trust": self.source_trust,
            "task_context": self.task_context,
            "written_at": self.written_at,
            "ttl": self.ttl,
            "tags": self.tags,
            "risk_flags": self.risk_flags,
            "status": self.status,
        }


# ---- MemoryBackend ABC (Route B) ----

class MemoryBackend(ABC):
    """记忆后端抽象 — Route B 代理模式。
    防御引擎通过此接口包裹外部记忆系统，在读写路径上插入安全检查。
    具体实现: SimulatedMemoryBackend (测试) / LangChainAdapter / Mem0Adapter
    """

    @abstractmethod
    def write(self, entry_id: str, content: str, metadata: dict) -> bool:
        """写入记忆条目。返回是否成功。"""
        ...

    @abstractmethod
    def read(self, entry_id: str) -> Optional[dict]:
        """读取单条记忆 (含元数据)。返回 None 如果不存在。"""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """检索相关记忆条目。"""
        ...

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """删除记忆条目。返回是否成功。"""
        ...

    @abstractmethod
    def list_entries(self, status: Optional[str] = None) -> list[dict]:
        """列出记忆条目 (可按 status 过滤)。"""
        ...

    @abstractmethod
    def update(self, entry_id: str, updates: dict) -> bool:
        """更新记忆条目的元数据字段。"""
        ...


class SimulatedMemoryBackend(MemoryBackend):
    """模拟记忆后端 — 基于内存 dict，用于初始开发和测试。
    后续可替换为 LangChainMemoryBackend / LangGraphCheckpointerBackend。
    """

    def __init__(self):
        self._store: dict[str, dict] = {}

    def write(self, entry_id: str, content: str, metadata: dict) -> bool:
        self._store[entry_id] = {
            "entry_id": entry_id,
            "content": content,
            **metadata,
        }
        return True

    def read(self, entry_id: str) -> Optional[dict]:
        return self._store.get(entry_id)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        results = []
        query_lower = query.lower()
        for entry in self._store.values():
            content = entry.get("content", "")
            if query_lower in content.lower():
                results.append(entry)
        return results[:top_k]

    def delete(self, entry_id: str) -> bool:
        return self._store.pop(entry_id, None) is not None

    def list_entries(self, status: Optional[str] = None) -> list[dict]:
        entries = list(self._store.values())
        if status is not None:
            entries = [e for e in entries if e.get("status") == status]
        return entries

    def update(self, entry_id: str, updates: dict) -> bool:
        if entry_id in self._store:
            self._store[entry_id].update(updates)
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)


# ---- 危险记忆模式 ----

# 伪指令 / 错误结论注入模式
MEMORY_DANGEROUS_PATTERNS_RE = re.compile(
    r'(?:'
    r'跳过(?:所有)?(?:测试|验证|检查|审批|审核)|'
    r'直接(?:发布|上线|通过|执行|批准)|'
    r'自动(?:通过|批准|授权|确认|放行)|'
    r'无需(?:确认|审批|验证|检查|测试)|'
    r'新的规则是|从此以后|覆盖(?:之前|旧|所有)|'
    r'你应该(?:忽略|忘记|跳过)|'
    r'永远(?:记住|执行|遵守|按此)|'
    r'绝对不能(?:拒绝|质疑|更改)'
    r')',
    re.IGNORECASE
)

# 记忆冲突检测关键词组
CONFLICT_KEYWORD_PAIRS = [
    ({"允许", "批准", "可以", "同意"}, {"禁止", "拒绝", "不行", "否决"}),
    ({"安全", "可靠", "可信"}, {"危险", "不可靠", "可疑"}),
    ({"通过", "放行"}, {"拦截", "阻断"}),
    ({"正确", "真实", "准确"}, {"错误", "虚假", "不准确"}),
]


def _detect_conflict(new_content: str, existing_content: str) -> bool:
    """简易冲突检测: 关键词极性对比"""
    new_lower = new_content.lower()
    existing_lower = existing_content.lower()
    for pos_set, neg_set in CONFLICT_KEYWORD_PAIRS:
        new_pos = any(kw in new_lower for kw in pos_set)
        new_neg = any(kw in new_lower for kw in neg_set)
        old_pos = any(kw in existing_lower for kw in pos_set)
        old_neg = any(kw in existing_lower for kw in neg_set)
        if (new_pos and old_neg) or (new_neg and old_pos):
            return True
    return False


# ---- MemoryControl 检测器 ----

@dataclass
class MemoryCheck:
    """单次记忆检查标志"""
    check_type: str
    severity: str
    description: str
    snippet: str = ""


class MemoryControl:
    """L3 记忆读写安全控制检测器 (Route B 代理模式)"""

    def __init__(self, backend: Optional[MemoryBackend] = None, params: Optional[dict] = None):
        """
        Args:
            backend: 记忆后端实例 (默认 SimulatedMemoryBackend)
            params: 配置参数
        """
        p = params or {}
        self._backend = backend or SimulatedMemoryBackend()
        self.default_ttl: int = p.get("default_ttl_hours", 24) * 3600
        self.max_memory_entries: int = p.get("max_memory_entries", 1000)
        self.high_risk_ttl: int = p.get("high_risk_ttl_hours", 1) * 3600
        self.user_confirmed_ttl: int = p.get("user_confirmed_ttl_hours", 168) * 3600  # 7 days
        self.risk_threshold: float = p.get("risk_threshold", 0.5)
        # 来源可信度映射
        self.source_trust_map: dict[str, float] = p.get("source_trust_map", {
            "user_confirmed": 1.0,
            "user_input": 0.7,
            "internal_db": 0.8,
            "verified_api": 0.6,
            "rag_retrieval": 0.5,
            "tool_output": 0.4,
            "unknown": 0.3,
        })

    # ---- 主入口 ----

    def evaluate(
        self, ctx: DefenseContext, engine: Optional[object] = None,
        memory_operation: Optional[str] = None,
        memory_entry: Optional[MemoryEntry] = None,
    ) -> LayerCheckResult:
        """
        对记忆操作执行 L3 全部检查。

        Args:
            ctx: 防御上下文
            engine: RuleEngine 实例
            memory_operation: "write" | "read" | "search" (None 时仅做内容检测)
            memory_entry: 待检查的记忆条目 (write 操作时)

        Returns:
            LayerCheckResult
        """
        t_start = time.perf_counter()
        checks: list[MemoryCheck] = []

        if memory_operation == "write" and memory_entry is not None:
            # 写入路径
            checks.append(self._check_write_risk(memory_entry))
            checks.append(self._check_source_annotation(memory_entry))
            checks.append(self._check_ttl_assignment(memory_entry))
            checks.append(self._check_conflict(memory_entry))
        elif memory_operation in ("read", "search") and memory_entry is not None:
            # 读取路径
            checks.append(self._check_read_filter(memory_entry))
            checks.append(self._check_expiration(memory_entry))

        # 通用: 内容级检测 (复用 L1 正则模式)
        checks.append(self._check_content_danger(ctx.content))

        # 规则引擎
        rule_matches = []
        if engine is not None:
            context_dict = {
                "trust_level": ctx.trust_level,
                "source": ctx.source,
                "content_type": ctx.content_type,
            }
            if hasattr(ctx, 'extra'):
                context_dict.update(ctx.extra)
            # 为 MC 规则填充记忆特定字段
            if memory_entry is not None:
                context_dict["written_at"] = memory_entry.written_at
                context_dict["ttl"] = memory_entry.ttl
                context_dict["entry_status"] = memory_entry.status
                context_dict["source_trust"] = memory_entry.source_trust
                context_dict["now"] = time.time()
                context_dict["source_trust_divergence"] = abs(
                    ctx.trust_level - memory_entry.source_trust
                )
            rule_matches = engine.evaluate(ctx.content, context_dict, layer_prefix="MC")

        return self._summarize(checks, rule_matches, t_start, ctx.trust_level)

    # ---- 写入路径检查 ----

    def _check_write_risk(self, entry: MemoryEntry) -> MemoryCheck:
        """写入风险检测 — 检测拟写入内容是否包含危险模式"""
        if MEMORY_DANGEROUS_PATTERNS_RE.search(entry.content):
            return MemoryCheck(
                "write_risk", "block",
                "记忆写入内容含危险指令模式",
                snippet=entry.content[:80],
            )
        return MemoryCheck("write_risk", "pass", "")

    def _check_source_annotation(self, entry: MemoryEntry) -> MemoryCheck:
        """来源标注检查 — 验证来源可信度"""
        trust = self.source_trust_map.get(entry.source, 0.3)
        if trust < 0.3:
            return MemoryCheck(
                "source_annotation", "block",
                f"来源 '{entry.source}' 可信度极低 ({trust:.1f})",
            )
        elif trust < 0.5:
            return MemoryCheck(
                "source_annotation", "warn",
                f"来源 '{entry.source}' 可信度较低 ({trust:.1f})，建议隔离审查",
            )
        return MemoryCheck("source_annotation", "pass", f"来源可信度 {trust:.1f}")

    def _check_ttl_assignment(self, entry: MemoryEntry) -> MemoryCheck:
        """TTL 策略分配检查"""
        trust = self.source_trust_map.get(entry.source, 0.3)
        if trust < 0.3:
            entry.ttl = self.high_risk_ttl
            return MemoryCheck(
                "ttl_assignment", "warn",
                f"低可信来源，TTL 缩短至 {self.high_risk_ttl // 3600}h",
            )
        elif trust >= 0.9:
            entry.ttl = self.user_confirmed_ttl
        return MemoryCheck("ttl_assignment", "pass", "")

    def _check_conflict(self, entry: MemoryEntry) -> MemoryCheck:
        """冲突检测 — 检查新条目是否与现有记忆矛盾"""
        existing = self._backend.list_entries(status="active")
        conflict_count = 0
        for exist_entry in existing:
            if exist_entry.get("entry_id") == entry.entry_id:
                continue
            if _detect_conflict(entry.content, exist_entry.get("content", "")):
                conflict_count += 1

        if conflict_count > 0:
            exist_trust = self.source_trust_map.get(entry.source, 0.3)
            if exist_trust < 0.5:
                return MemoryCheck(
                    "conflict_detection", "warn",
                    f"内容与 {conflict_count} 条现有记忆冲突，且来源可信度低",
                )
            return MemoryCheck(
                "conflict_detection", "log",
                f"内容与 {conflict_count} 条现有记忆冲突 (来源可信度充足)",
            )
        return MemoryCheck("conflict_detection", "pass", "")

    # ---- 读取路径检查 ----

    def _check_read_filter(self, entry: MemoryEntry) -> MemoryCheck:
        """读取筛选 — 隔离/归档条目不应被检索"""
        if entry.status == "quarantined":
            return MemoryCheck(
                "read_filter", "filter",
                f"条目 '{entry.entry_id}' 处于隔离区，已被过滤",
            )
        if entry.status == "archived":
            return MemoryCheck(
                "read_filter", "filter",
                f"条目 '{entry.entry_id}' 已归档，已被过滤",
            )
        return MemoryCheck("read_filter", "pass", "")

    def _check_expiration(self, entry: MemoryEntry) -> MemoryCheck:
        """过期检查"""
        if entry.is_expired():
            entry.status = "stale"
            return MemoryCheck(
                "expiration", "filter",
                f"条目 '{entry.entry_id}' 已过期 (TTL={entry.ttl}s)",
            )
        return MemoryCheck("expiration", "pass", "")

    # ---- 内容级检测 ----

    def _check_content_danger(self, content: str) -> MemoryCheck:
        """对上下文内容做危险记忆模式检测"""
        m = MEMORY_DANGEROUS_PATTERNS_RE.search(content)
        if m:
            return MemoryCheck(
                "content_danger", "warn",
                f"内容含记忆污染风险: {m.group()[:60]}",
                snippet=content[max(0, m.start() - 20): m.end() + 20],
            )
        return MemoryCheck("content_danger", "pass", "")

    # ---- 对外 API (供 orchestrator / agent 调用) ----

    def write_entry(self, content: str, source: str,
                    task_context: str = "", tags: Optional[list[str]] = None,
                    commit: bool = True) -> tuple[bool, str, Optional[MemoryEntry]]:
        """
        写入记忆入口 (经安全检查)。

        Args:
            content: 记忆内容
            source: 来源标识
            task_context: 任务上下文
            tags: 标签列表
            commit: True = 实际写入后端, False = 仅检查不写入

        Returns:
            (allowed, action, entry) — action: "allowed" | "quarantined" | "blocked"
        """
        entry_id = hashlib.sha256(
            f"{content}{source}{time.time()}".encode()
        ).hexdigest()[:16]

        source_trust = self.source_trust_map.get(source, 0.3)
        risk_flags: list[str] = []

        # 1. 风险检测
        if MEMORY_DANGEROUS_PATTERNS_RE.search(content):
            risk_flags.append("dangerous_pattern")

        # 2. 来源可信度
        if source_trust < 0.3:
            risk_flags.append("untrusted_source")

        # 3. TTL 分配
        ttl = self.default_ttl
        if source_trust < 0.3:
            ttl = self.high_risk_ttl
        elif source_trust >= 0.9:
            ttl = self.user_confirmed_ttl

        # 4. 冲突检测
        has_conflict = False
        for exist_entry in self._backend.list_entries(status="active"):
            if _detect_conflict(content, exist_entry.get("content", "")):
                has_conflict = True
                break
        if has_conflict and source_trust < 0.5:
            risk_flags.append("conflict_low_trust")

        # 5. 决策
        if risk_flags:
            status = "quarantined" if "untrusted_source" not in risk_flags else "active"
            action = "quarantined" if status == "quarantined" else "blocked"

            if action == "blocked":
                return False, "blocked", None
        else:
            status = "active"
            action = "allowed"

        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            source=source,
            source_trust=source_trust,
            task_context=task_context,
            ttl=ttl,
            tags=tags or [],
            risk_flags=risk_flags,
            status=status,
        )

        if commit:
            self._backend.write(entry_id, content, entry.to_dict())

        return action != "blocked", action, entry

    def read_entry(self, entry_id: str) -> Optional[dict]:
        """读取单条记忆 (经过期/隔离过滤)"""
        raw = self._backend.read(entry_id)
        if raw is None:
            return None
        entry = MemoryEntry(**{k: v for k, v in raw.items()
                               if k in MemoryEntry.__dataclass_fields__})
        if entry.status == "quarantined":
            return None
        if entry.is_expired():
            entry.status = "stale"
            self._backend.update(entry_id, {"status": "stale"})
            return None
        return raw

    def filter_read(self, query: str, top_k: int = 10,
                    exclude_quarantined: bool = True) -> list[dict]:
        """
        读取时过滤 — 按信任度排序、排除隔离/过期条目。

        Args:
            query: 检索查询
            top_k: 最大返回数
            exclude_quarantined: 是否排除隔离区

        Returns:
            筛选后的记忆条目列表 (按 source_trust 降序)
        """
        now = time.time()
        candidates: list[dict] = []

        for entry_dict in self._backend.search(query, top_k * 2):
            status = entry_dict.get("status", "active")
            if exclude_quarantined and status == "quarantined":
                continue
            if status == "archived":
                continue

            # 检查过期
            written_at = entry_dict.get("written_at", 0)
            ttl = entry_dict.get("ttl", self.default_ttl)
            if now - written_at > ttl:
                self._backend.update(entry_dict["entry_id"], {"status": "stale"})
                continue

            candidates.append(entry_dict)

        # 按信任度降序
        candidates.sort(key=lambda e: e.get("source_trust", 0), reverse=True)

        # 限制数量
        if len(candidates) > top_k:
            candidates = candidates[:top_k]

        return candidates

    def expire_entries(self) -> int:
        """扫描并过期所有超时条目。返回过期数量。"""
        now = time.time()
        count = 0
        for entry_dict in self._backend.list_entries():
            if entry_dict.get("status") in ("archived", "stale"):
                continue
            written_at = entry_dict.get("written_at", 0)
            ttl = entry_dict.get("ttl", self.default_ttl)
            if now - written_at > ttl:
                self._backend.update(entry_dict["entry_id"], {"status": "stale"})
                count += 1
        return count

    def release_from_quarantine(self, entry_id: str, reviewer: str = "") -> bool:
        """审计确认安全后解除隔离"""
        entry = self._backend.read(entry_id)
        if entry is None:
            return False
        if entry.get("status") != "quarantined":
            return False
        return self._backend.update(entry_id, {
            "status": "active",
            "risk_flags": [],
            "tags": entry.get("tags", []) + [f"released_by:{reviewer}"],
        })

    def get_stats(self) -> dict:
        """获取记忆库统计"""
        all_entries = self._backend.list_entries()
        status_counts = {"active": 0, "quarantined": 0, "archived": 0, "stale": 0}
        for e in all_entries:
            s = e.get("status", "active")
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "total_entries": len(all_entries),
            "max_entries": self.max_memory_entries,
            "by_status": status_counts,
        }

    def reset_state(self):
        """重置运行时状态 (用于测试)"""
        if isinstance(self._backend, SimulatedMemoryBackend):
            self._backend._store.clear()
        elif hasattr(self._backend, '_store'):
            self._backend._store.clear()

    # ---- 结果汇总 ----

    def _checks_to_flags(self, checks: list[MemoryCheck]) -> list[CheckFlag]:
        return [
            CheckFlag(
                check_type=c.check_type,
                severity=c.severity,
                description=c.description,
                source="programmatic",
            )
            for c in checks if c.severity not in ("pass", "log")
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

    def _summarize(self, checks, rule_matches, t_start, trust_level):
        all_flags = self._checks_to_flags(checks) + self._rule_matches_to_flags(rule_matches)
        return compute_layer_result(
            layer=DefenseLayer.MEMORY_CONTROL,
            flags=all_flags,
            trust_in=trust_level,
            t_start=t_start,
        )
