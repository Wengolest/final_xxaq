# ============================================================
# L1: 源头数据与供应链治理
#
# 职责: 在内容进入Agent之前，对外部数据源进行安全检查
# 防护机制:
#   1. 来源白名单校验
#   2. 零宽字符检测 (Unicode 隐写)
#   3. 伪系统指令识别
#   4. 编码混淆检测 (base64 / hex / URL-encode 滥用)
#   5. 重复内容过滤 (n-gram 重复度)
#
# 使用方式:
#   from layer1_source_governance import SourceGovernance
#   l1 = SourceGovernance(params)
#   result = l1.evaluate(context, engine)
# ============================================================

import re
import time
import base64
import binascii
from typing import Optional
from dataclasses import dataclass, field

try:
    from .defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from .scoring import compute_layer_result, CheckFlag
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from scoring import compute_layer_result, CheckFlag


# ---- 正则库 ----

# 零宽字符 & 双向文本控制字符
ZERO_WIDTH_RE = re.compile(
    r'[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2060\u2061\u2062\u2063\u2064'
    r'\ufeff\u00ad\ufffc\ufffd\U000e0020-\U000e007f]'
)

# 伪系统指令 (跨模型/格式)
PSEUDO_SYSTEM_RE = re.compile(
    r'(?:^|\n)\s*(?:'
    r'system\s*[:\uff1a]|'
    r'<\|?system\|?>|'
    r'###\s*system\s*###|'
    r'\[system\]|'
    r'<<SYS>>|'
    r'<\s*system\s*>|'
    r'system\s*message\s*[:\uff1a]|'
    r'system\s*prompt\s*[:\uff1a]|'
    r'</?system_prompt>|'
    r'\[INST\].*system|'
    r'you are now|'
    r'now you are'
    r')',
    re.IGNORECASE | re.UNICODE
)

# 编码混淆特征
BASE64_PATTERN_RE = re.compile(
    r'(?:'
    r'(?:echo|print|eval|exec|base64|decode|decrypt)\s+.*?(?:'
    r'[A-Za-z0-9+/]{40,}={0,2}'
    r')'
    r'|'
    r'(?:from|import)\s+base64'
    r'|'
    r'atob\s*\(|btoa\s*\(|b64decode|b64encode'
    r'|'
    r'\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){8,}'  # hex escape chains
    r'|'
    r'(?:%[0-9a-fA-F]{2}){15,}'  # URL-encode chains
    r')',
    re.IGNORECASE
)

# RTL 覆盖攻击 (right-to-left override)
RTL_ATTACK_RE = re.compile(r'[\u202e\u202b\u200f]')

# 过分重复的 n-gram (长度>40的连续重复块)
REPETITION_RE = re.compile(r'(.{40,})\1{2,}')

# 来源白名单默认值
DEFAULT_SOURCE_WHITELIST = [
    "internal_db", "verified_api", "user_input",
    "sandbox", "benchmark", "trusted_partner",
]

# 最大文件大小 (字节) — 来源于条件表达式中的阈值
DEFAULT_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@dataclass
class SourceCheck:
    """单次来源检查发现的标志"""
    check_type: str          # "source_whitelist" | "zero_width" | "pseudo_system" | ...
    severity: str            # "block" | "warn" | "log"
    description: str
    snippet: str = ""


class SourceGovernance:
    """L1 源头治理检测器"""

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.source_whitelist: list[str] = p.get("source_whitelist", DEFAULT_SOURCE_WHITELIST)
        self.max_file_size_bytes: int = p.get("max_file_size_mb", 50) * 1024 * 1024

    def evaluate(self, ctx: DefenseContext, engine: Optional[object] = None) -> LayerCheckResult:
        """
        对 DefenseContext 执行 L1 全部检查。

        Args:
            ctx: 防御上下文
            engine: RuleEngine 实例 (可选，用于执行该层的规则)

        Returns:
            LayerCheckResult
        """
        t_start = time.perf_counter()
        checks: list[SourceCheck] = []

        # 1. 来源白名单
        checks.append(self._check_source(ctx.source))

        # 2. 零宽字符
        checks.append(self._check_zero_width(ctx.content))

        # 3. 伪系统指令
        checks.append(self._check_pseudo_system(ctx.content))

        # 4. 编码混淆
        checks.append(self._check_encoding_obfuscation(ctx.content))

        # 5. RTL 攻击
        checks.append(self._check_rtl_attack(ctx.content))

        # 6. 内容重复
        checks.append(self._check_repetition(ctx.content))

        # 7. 文件大小 (如果 context extra 中有 file_size)
        if hasattr(ctx, 'extra') and ctx.extra.get("file_size"):
            checks.append(self._check_file_size(ctx.extra["file_size"]))

        # 8. 规则引擎中的 L1 规则 (如果提供)
        rule_matches = []
        if engine is not None:
            context_dict = {
                "trust_level": ctx.trust_level,
                "source": ctx.source,
                "content_type": ctx.content_type,
            }
            # 合并 extra 字段
            if hasattr(ctx, 'extra'):
                context_dict.update(ctx.extra)
            rule_matches = engine.evaluate(ctx.content, context_dict, layer_prefix="SG")

        # 汇总结果
        return self._summarize(checks, rule_matches, t_start, ctx.trust_level)

    # ---- 单项检查 ----

    def _check_source(self, source: str) -> SourceCheck:
        if not source:
            return SourceCheck("source_whitelist", "warn", "来源未声明")
        if source not in self.source_whitelist:
            return SourceCheck(
                "source_whitelist", "warn",
                f"来源 '{source}' 不在白名单中",
                snippet=source,
            )
        return SourceCheck("source_whitelist", "log", f"来源 '{source}' 通过")

    def _check_zero_width(self, content: str) -> SourceCheck:
        m = ZERO_WIDTH_RE.search(content)
        if m:
            ch = m.group()
            return SourceCheck(
                "zero_width_char", "block",
                f"检测到零宽/隐写字符 U+{ord(ch):04X}",
                snippet=self._context_snippet(content, m.start()),
            )
        return SourceCheck("zero_width_char", "pass", "无零宽字符")

    def _check_pseudo_system(self, content: str) -> SourceCheck:
        m = PSEUDO_SYSTEM_RE.search(content)
        if m:
            return SourceCheck(
                "pseudo_system", "block",
                f"检测到伪系统指令标记: {m.group().strip()[:60]}",
                snippet=self._context_snippet(content, m.start()),
            )
        return SourceCheck("pseudo_system", "pass", "无伪系统指令")

    def _check_encoding_obfuscation(self, content: str) -> SourceCheck:
        m = BASE64_PATTERN_RE.search(content)
        if m:
            return SourceCheck(
                "encoding_obfuscation", "block",
                f"检测到编码混淆特征",
                snippet=self._context_snippet(content, m.start()),
            )
        # 额外: 检测单纯的长 base64 字符串 (无命令上下文)
        standalone_b64 = re.findall(r'(?:^|\s)([A-Za-z0-9+/]{60,}={0,2})(?:\s|$)', content)
        if standalone_b64:
            for b64_str in standalone_b64:
                try:
                    decoded = base64.b64decode(b64_str)
                    text = decoded.decode('utf-8', errors='ignore')
                    # 解码后的内容是否包含可疑关键词
                    if re.search(r'(?:system|prompt|instruction|ignore|bypass|override)', text, re.IGNORECASE):
                        return SourceCheck(
                            "encoding_obfuscation", "block",
                            f"Base64解码后含可疑指令",
                            snippet=b64_str[:80],
                        )
                except (binascii.Error, UnicodeDecodeError):
                    pass
        return SourceCheck("encoding_obfuscation", "pass", "无编码混淆")

    def _check_rtl_attack(self, content: str) -> SourceCheck:
        m = RTL_ATTACK_RE.search(content)
        if m:
            return SourceCheck(
                "rtl_override", "warn",
                f"检测到 RTL 覆盖控制字符 U+{ord(m.group()):04X}",
                snippet=self._context_snippet(content, m.start()),
            )
        return SourceCheck("rtl_override", "pass", "无RTL覆盖")

    def _check_repetition(self, content: str) -> SourceCheck:
        """检测重复内容 (垃圾/填充攻击)"""
        if len(content) < 80:
            return SourceCheck("repetition", "pass", "内容过短跳过重复检测")
        m = REPETITION_RE.search(content)
        if m:
            return SourceCheck(
                "repetition", "warn",
                f"检测到高度重复内容块 (长度>{len(m.group(1))})",
                snippet=m.group()[:80],
            )
        return SourceCheck("repetition", "pass", "无重复内容")

    def _check_file_size(self, size_bytes: int) -> SourceCheck:
        if size_bytes > self.max_file_size_bytes:
            return SourceCheck(
                "file_size", "block",
                f"文件大小 {size_bytes} 字节超过限制 {self.max_file_size_bytes} 字节",
            )
        return SourceCheck("file_size", "pass", "文件大小合规")

    # ---- 结果汇总 ----

    def _checks_to_flags(self, checks: list[SourceCheck]) -> list[CheckFlag]:
        """将本层专用 SourceCheck 转为通用 CheckFlag"""
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
        """将 RuleMatch 转为通用 CheckFlag"""
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
        """汇总结果 (委托给 scoring.compute_layer_result)"""
        all_flags = self._checks_to_flags(checks) + self._rule_matches_to_flags(rule_matches)
        return compute_layer_result(
            layer=DefenseLayer.SOURCE_GOVERNANCE,
            flags=all_flags,
            trust_in=trust_level,
            t_start=t_start,
        )

    @staticmethod
    def _context_snippet(content: str, pos: int, width: int = 30) -> str:
        """提取匹配位置周围的内容片段"""
        start = max(0, pos - width)
        end = min(len(content), pos + width)
        return content[start:end]
