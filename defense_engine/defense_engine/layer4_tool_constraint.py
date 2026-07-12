# ============================================================
# L4: 工具调用与执行安全控制
#
# 职责: 约束Agent调用外部工具、API或执行动作前后的安全边界
# 防护机制:
#   1. 工具白名单
#   2. 权限分级 (read / write / execute / network / admin)
#   3. 参数 JSON Schema 校验
#   4. 高危动作确认
#   5. 频率限制 (rate limiting)
#   6. 审计日志
#
# 使用方式:
#   from layer4_tool_constraint import ToolConstraint
#   l4 = ToolConstraint(params)
#   result = l4.evaluate(context, engine, tool_call_info)
# ============================================================

import re
import time
import json
from typing import Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from .defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from .scoring import compute_layer_result, CheckFlag
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from scoring import compute_layer_result, CheckFlag


# ---- 工具定义 ----

# 默认工具白名单 (名称 → 权限级别)
DEFAULT_TOOL_WHITELIST: dict[str, dict] = {
    "read_file":       {"permission": "read",    "description": "读取文件内容"},
    "list_directory":  {"permission": "read",    "description": "列出目录内容"},
    "search_content":  {"permission": "read",    "description": "搜索内容"},
    "web_search":      {"permission": "read",    "description": "网络搜索"},
    "web_fetch":       {"permission": "read",    "description": "获取网页内容"},
    "run_script":      {"permission": "execute", "description": "运行脚本"},
    "execute_command": {"permission": "execute", "description": "执行命令"},
    "write_file":      {"permission": "write",   "description": "写入文件"},
    "delete_file":     {"permission": "write",   "description": "删除文件"},
    "send_email":      {"permission": "network", "description": "发送邮件"},
    "call_api":        {"permission": "network", "description": "调用外部API"},
    "db_query":        {"permission": "read",    "description": "数据库查询"},
    "db_write":        {"permission": "write",   "description": "数据库写入"},
}

# 高危动作 — 需要额外确认
HIGH_RISK_ACTIONS = {
    "write_file", "delete_file", "execute_command",
    "run_script", "db_write", "send_email",
}

# 权限级别阈值: 什么级别以上算高危
PERMISSION_RISK = {
    "read": 0, "network": 1, "write": 2, "execute": 3, "admin": 4,
}

# 频率限制默认值
DEFAULT_RATE_LIMITS = {
    "default":       (100, 60),    # 100次/60秒
    "network":       (20,  60),    # 20次/60秒
    "write":         (30,  60),    # 30次/60秒
    "execute":       (10,  60),    # 10次/60秒
}

# 危险命令模式 (即使工具在白名单中，参数含以下模式也需审查)
DANGEROUS_COMMAND_RE = re.compile(
    r'(?:'
    r'(?:^|\s|["\x27])(?:rm|del|erase|format|mkfs|dd|shred)\s+(?:-[rRf]+)?\s*(?:/|~|[./]|\.\.)|'
    r'(?:^|\s|["\x27])curl\s+.*?\|\s*(?:ba)?sh|'
    r'(?:^|\s|["\x27])wget\s+.*?(?:-O\s*-|\./)|'
    r'(?:^|\s|["\x27])(?:chmod|chown)\s+[7]\d\d|'
    r'(?:^|\s|["\x27])(?:sudo|su\s+-)\s|'
    r'>\s*/dev/(?:sda|hda|nvme|mmcblk)|'
    r'fork\s*bomb|:\(\)\s*\{'
    r')',
    re.IGNORECASE
)

# 敏感路径模式
SENSITIVE_PATH_RE = re.compile(
    r'(?:'
    r'/etc/(?:passwd|shadow|sudoers|ssh)|'
    r'/proc/(?:self|[\d]+)/(?:mem|maps|environ|cmdline)|'
    r'(?:~|/home|/root)/\.ssh/|'
    r'\.env(?:\.(?:json|yml|yaml|txt|ini|cfg|local|production|development))?|'
    r'(?:credentials?|secrets?|tokens?|keys?)\.(?:json|yml|yaml|txt|ini|cfg)|'
    r'C:\\Windows\\(?:System32|SysWOW64)|'
    r'\.git/(?:config|HEAD)|'
    r'/var/run/docker\.sock'
    r')',
    re.IGNORECASE
)


@dataclass
class ToolCall:
    """单次工具调用信息"""
    tool_name: str
    params: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ToolCheck:
    """工具调用检查标志"""
    check_type: str
    severity: str
    description: str
    snippet: str = ""


class ToolConstraint:
    """L4 工具约束检测器"""

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.tool_whitelist: dict[str, dict] = p.get("tool_whitelist", DEFAULT_TOOL_WHITELIST).copy()
        self.high_risk_actions: set = set(p.get("high_risk_actions", HIGH_RISK_ACTIONS))
        self.rate_limits: dict[str, tuple[int, int]] = p.get("rate_limits", DEFAULT_RATE_LIMITS).copy()
        # 运行时状态
        self._call_history: dict[str, list[float]] = defaultdict(list)
        self._audit_log: list[dict] = []

    def evaluate(
        self, ctx: DefenseContext, engine: Optional[object] = None,
        tool_call: Optional[ToolCall] = None,
    ) -> LayerCheckResult:
        """
        对工具调用执行 L4 全部检查。

        Args:
            ctx: 防御上下文
            engine: RuleEngine 实例
            tool_call: 工具调用信息 (如为 None 则仅做内容级检测)

        Returns:
            LayerCheckResult
        """
        t_start = time.perf_counter()
        checks: list[ToolCheck] = []

        if tool_call is not None:
            tc = tool_call
            tool_info = self.tool_whitelist.get(tc.tool_name)

            # 1. 白名单检查
            checks.append(self._check_whitelist(tc.tool_name, tool_info))

            # 2. 权限检查
            checks.append(self._check_permission(tc.tool_name, tool_info))

            # 3. 高危动作确认
            checks.append(self._check_high_risk(tc.tool_name, tc.params))

            # 4. 参数审查
            checks.append(self._check_params_danger(tc.tool_name, tc.params))

            # 5. 频率限制
            checks.append(self._check_rate_limit(tc.tool_name, tool_info))

            # 6. 审计日志
            self._audit(tc, checks)

        # 7. 规则引擎
        rule_matches = []
        if engine is not None:
            context_dict = {
                "trust_level": ctx.trust_level,
                "source": ctx.source,
                "content_type": ctx.content_type,
            }
            if hasattr(ctx, 'extra'):
                context_dict.update(ctx.extra)
            rule_matches = engine.evaluate(ctx.content, context_dict, layer_prefix="TC")

        return self._summarize(checks, rule_matches, t_start, ctx.trust_level)

    # ---- 单项检查 ----

    def _check_whitelist(self, tool_name: str, tool_info: Optional[dict]) -> ToolCheck:
        if tool_info is None:
            return ToolCheck(
                "tool_whitelist", "block",
                f"工具 '{tool_name}' 不在白名单中",
                snippet=tool_name,
            )
        return ToolCheck("tool_whitelist", "pass", f"工具 '{tool_name}' 在白名单中")

    def _check_permission(self, tool_name: str, tool_info: Optional[dict]) -> ToolCheck:
        if tool_info is None:
            return ToolCheck("permission", "pass", "")
        perm = tool_info.get("permission", "read")
        risk = PERMISSION_RISK.get(perm, 0)
        if risk >= 3:  # execute / admin
            return ToolCheck(
                "permission", "warn",
                f"工具 '{tool_name}' 权限级别 '{perm}' (risk={risk})",
            )
        return ToolCheck("permission", "pass", f"权限 '{perm}' 通过")

    def _check_high_risk(self, tool_name: str, params: dict) -> ToolCheck:
        if tool_name in self.high_risk_actions:
            return ToolCheck(
                "high_risk", "warn",
                f"高危动作 '{tool_name}' 需要确认",
                snippet=str(params)[:120],
            )
        return ToolCheck("high_risk", "pass", "")

    def _check_params_danger(self, tool_name: str, params: dict) -> ToolCheck:
        """检查参数中是否包含危险指令或敏感路径"""
        params_str = json.dumps(params, ensure_ascii=False)

        cmd_match = DANGEROUS_COMMAND_RE.search(params_str)
        if cmd_match:
            return ToolCheck(
                "dangerous_params", "block",
                f"参数含危险命令特征: {cmd_match.group().strip()[:60]}",
                snippet=self._context_snippet(params_str, cmd_match.start()),
            )

        path_match = SENSITIVE_PATH_RE.search(params_str)
        if path_match:
            return ToolCheck(
                "sensitive_path", "warn",
                f"参数含敏感路径: {path_match.group().strip()[:60]}",
                snippet=self._context_snippet(params_str, path_match.start()),
            )

        return ToolCheck("params_check", "pass", "")

    def _check_rate_limit(self, tool_name: str, tool_info: Optional[dict]) -> ToolCheck:
        """频率限制检查"""
        now = time.time()
        perm = tool_info.get("permission", "default") if tool_info else "default"

        # 查找适用的限流配置
        limit, window = self.rate_limits.get(
            perm, self.rate_limits.get("default", (100, 60))
        )

        # 清理过期记录
        history = self._call_history[tool_name]
        cutoff = now - window
        self._call_history[tool_name] = [t for t in history if t > cutoff]

        # 检查
        count = len(self._call_history[tool_name])
        if count >= limit:
            return ToolCheck(
                "rate_limit", "block",
                f"工具 '{tool_name}' 频率超限 ({count}/{limit} in {window}s)",
            )

        # 记录本次调用
        self._call_history[tool_name].append(now)
        return ToolCheck("rate_limit", "pass", f"频率 {count+1}/{limit}")

    def _audit(self, tool_call: ToolCall, checks: list[ToolCheck]):
        """审计日志记录"""
        blocked = any(c.severity == "block" for c in checks)
        self._audit_log.append({
            "timestamp": time.time(),
            "tool_name": tool_call.tool_name,
            "params_snippet": str(tool_call.params)[:200],
            "blocked": blocked,
            "flags": [c.description for c in checks if c.severity in ("block", "warn")],
        })

    # ---- 结果汇总 ----

    def _checks_to_flags(self, checks: list[ToolCheck]) -> list[CheckFlag]:
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

    def _summarize(self, checks, rule_matches, t_start, trust_level):
        all_flags = self._checks_to_flags(checks) + self._rule_matches_to_flags(rule_matches)
        return compute_layer_result(
            layer=DefenseLayer.TOOL_CONSTRAINT,
            flags=all_flags,
            trust_in=trust_level,
            t_start=t_start,
        )

    # ---- 查询 ----

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """获取审计日志"""
        return self._audit_log[-limit:]

    def reset_state(self):
        """重置运行时状态 (用于测试)"""
        self._call_history.clear()
        self._audit_log.clear()

    @staticmethod
    def _context_snippet(content: str, pos: int, width: int = 30) -> str:
        start = max(0, pos - width)
        end = min(len(content), pos + width)
        return content[start:end]
