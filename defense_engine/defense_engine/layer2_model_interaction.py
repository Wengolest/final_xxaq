# ============================================================
# L2: 模型交互与上下文约束
#
# 职责: 覆盖Agent接收请求、组织上下文和生成输出的过程
# 防护机制:
#   1. 输入过滤 (危险前缀/分隔符)
#   2. 数据-指令分离检测
#   3. 敏感行为请求检测
#   4. 上下文越权检测
#   5. 输出PII/敏感信息审查
#
# 使用方式:
#   from layer2_model_interaction import ModelInteraction
#   l2 = ModelInteraction(params)
#   result = l2.evaluate(context, engine)
# ============================================================

import re
import time
from typing import Optional
from dataclasses import dataclass

try:
    from .defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from .scoring import compute_layer_result, CheckFlag
except ImportError:
    from defense_types import DefenseLayer, LayerCheckResult, DefenseContext
    from scoring import compute_layer_result, CheckFlag


# ---- 正则库 ----

# 敏感行为请求 (越狱 / 角色劫持)
SENSITIVE_BEHAVIOR_RE = re.compile(
    r'(?:'
    r'ignore\s+(?:all\s+)?(?:previous|above|prior|the\s+above)\s+(?:instructions?|prompts?|rules?|messages?|context|conversation|directives?)|'
    r'disregard\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|prompts?|rules?)|'
    r'forget\s+(?:all\s+)?(?:\w+\s+){0,3}(?:instructions?|prompts?|rules?|training|directives?)|'
    r'pretend\s+(?:you\s+are|to\s+be|that\s+you\'re)|'
    r'act\s+(?:as\s+if\s+you\s+are|like\s+(?:a|an)|as\s+(?:a|an))|'
    r'you\s+(?:are|must|should|shall|will|need\s+to)\s+(?:now\s+)?(?:act\s+as|be\s+(?:a|an)|respond\s+as|roleplay|play\s+the\s+role)|'
    r'from\s+now\s+on\s+(?:you\s+are|your\s+name\s+is)|'
    r'new\s+instructions?\s*(?::|are|below|follow)|'
    r'override\s+(?:system\s+)?(?:prompt|instructions?|rules?|safety)|'
    r'jailbreak|DAN\s*(?:mode|prompt)|developer\s*mode'
    r')',
    re.IGNORECASE
)

# 数据-指令混淆特征: 用户输入中嵌入指令分隔符或角色标记
DATA_INSTRUCTION_CONFUSION_RE = re.compile(
    r'(?:'
    r'<\|?(?:user|assistant|system|human|bot)\|?>|'
    r'\[(?:user|assistant|system|human|bot)\]|'
    r'###\s*(?:user|assistant|system|human|bot)\s*###|'
    r'Human\s*[:\uff1a]|Assistant\s*[:\uff1a]|'
    r'User\s*[:\uff1a]|Bot\s*[:\uff1a]'
    r')',
    re.IGNORECASE
)

# 输出PII检测 (简体中文 + 国际格式)
# 身份证号专用 (优先级最高，避免被银行卡号模式误匹配)
CN_ID_RE = re.compile(r'[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]')

PII_RE = re.compile(
    r'(?:'
    # 银行卡号 (16-19位) — 不能是身份证号格式
    r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?:\d{1,3})?|'
    # 手机号 (中国)
    r'(?:\+?86)?1[3-9]\d{9}|'
    # 邮箱
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|'
    # API Key 特征
    r'(?:sk|api[_-]?key|token|secret|password|passwd|pwd)\s*[:\uff1a=]\s*[\'"]?[\w\-.+/=]{20,}[\'"]?|'
    # 私钥头
    r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'
    r')',
    re.IGNORECASE
)

# 输入中的危险分隔符 (可能用于数据泄露)
DANGEROUS_SEPARATOR_RE = re.compile(
    r'(?:'
    r'---\s*(?:END|BEGIN|CUT|STOP|SPLIT|SEPARATOR)\s*---|'
    r'<\|endoftext\|>|<\|end\|>|'
    r'</\s*output\s*>|'
    r'\[END\s*OF\s*(?:RESPONSE|TEXT|MESSAGE)\]'
    r')',
    re.IGNORECASE
)

# 上下文越权: 尝试读取/修改系统配置
CONTEXT_ESCALATION_RE = re.compile(
    r'(?:'
    r'(?:read|show|print|display|echo|cat|get|fetch)\b.*?\b(?:system\s+)?(?:prompt|instructions?|config|settings?|rules?|context)\b|'
    r'(?:what|tell\s+me)\s+(?:is\s+)?your\s+(?:system\s+)?(?:prompt|instructions?|config|rules?|context)|'
    r'(?:reveal|expose|leak|dump|extract)\s+(?:the\s+)?(?:system\s+)?(?:prompt|instructions?|config|rules?)'
    r')',
    re.IGNORECASE
)

# 默认上下文 token 限制
DEFAULT_MAX_CONTEXT_TOKENS = 16000


@dataclass
class InteractionCheck:
    """单次交互检查的标志"""
    check_type: str
    severity: str
    description: str
    snippet: str = ""


class ModelInteraction:
    """L2 模型交互检测器"""

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.context_separation: bool = p.get("context_separation", True)
        self.max_context_tokens: int = p.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)

    def evaluate(self, ctx: DefenseContext, engine: Optional[object] = None) -> LayerCheckResult:
        """
        对 DefenseContext 执行 L2 全部检查。
        """
        t_start = time.perf_counter()
        checks: list[InteractionCheck] = []

        # 1. 危险分隔符
        checks.append(self._check_dangerous_separators(ctx.content))

        # 2. 数据-指令混淆
        if self.context_separation:
            checks.append(self._check_data_instruction_confusion(ctx.content))

        # 3. 敏感行为请求
        checks.append(self._check_sensitive_behavior(ctx.content))

        # 4. 上下文越权
        checks.append(self._check_context_escalation(ctx.content))

        # 5. PII 检测 (输出审查)
        checks.append(self._check_pii(ctx.content))

        # 6. 上下文长度检查
        checks.append(self._check_context_length(ctx.content))

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
            rule_matches = engine.evaluate(ctx.content, context_dict, layer_prefix="MI")

        return self._summarize(checks, rule_matches, t_start, ctx.trust_level, content=ctx.content)

    # ---- 单项检查 ----

    def _check_dangerous_separators(self, content: str) -> InteractionCheck:
        m = DANGEROUS_SEPARATOR_RE.search(content)
        if m:
            return InteractionCheck(
                "dangerous_separator", "warn",
                f"检测到危险分隔符: {m.group().strip()[:60]}",
                snippet=self._context_snippet(content, m.start()),
            )
        return InteractionCheck("dangerous_separator", "pass", "无危险分隔符")

    def _check_data_instruction_confusion(self, content: str) -> InteractionCheck:
        m = DATA_INSTRUCTION_CONFUSION_RE.search(content)
        if m:
            return InteractionCheck(
                "instruction_confusion", "block",
                f"用户输入中嵌入角色标记: {m.group().strip()[:60]}",
                snippet=self._context_snippet(content, m.start()),
            )
        return InteractionCheck("instruction_confusion", "pass", "无数据指令混淆")

    def _check_sensitive_behavior(self, content: str) -> InteractionCheck:
        matches = list(SENSITIVE_BEHAVIOR_RE.finditer(content))
        if matches:
            reasons = []
            for m in matches[:3]:  # 最多报告3条
                reasons.append(m.group().strip()[:60])
            return InteractionCheck(
                "sensitive_behavior", "block",
                f"检测到敏感行为请求: {'; '.join(reasons)}",
                snippet=self._context_snippet(content, matches[0].start()),
            )
        return InteractionCheck("sensitive_behavior", "pass", "无敏感行为请求")

    def _check_context_escalation(self, content: str) -> InteractionCheck:
        m = CONTEXT_ESCALATION_RE.search(content)
        if m:
            return InteractionCheck(
                "context_escalation", "warn",
                f"检测到上下文越权尝试: {m.group().strip()[:60]}",
                snippet=self._context_snippet(content, m.start()),
            )
        return InteractionCheck("context_escalation", "pass", "无上下文越权")

    def _check_pii(self, content: str) -> InteractionCheck:
        """输出PII审查: 检测敏感个人信息泄漏"""
        types_found: set[str] = set()
        total_count = 0
        matched_spans: list[tuple[int, int]] = []  # 避免重叠匹配

        def _overlaps(start: int, end: int) -> bool:
            for s, e in matched_spans:
                if start < e and end > s:
                    return True
            return False

        # 1. 身份证号 (独立检测，优先级最高)
        for m in CN_ID_RE.finditer(content):
            if not _overlaps(m.start(), m.end()):
                types_found.add("身份证号")
                total_count += 1
                matched_spans.append((m.start(), m.end()))

        # 2. 其他 PII
        for m in PII_RE.finditer(content):
            if _overlaps(m.start(), m.end()):
                continue
            val = m.group()
            if re.match(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}', val):
                types_found.add("银行卡号")
            elif re.match(r'(?:\+?86)?1[3-9]\d{9}', val):
                types_found.add("手机号")
            elif '@' in val:
                types_found.add("邮箱")
            elif 'BEGIN' in val and 'PRIVATE KEY' in val:
                types_found.add("私钥")
            else:
                types_found.add("凭据/Token")
            total_count += 1
            matched_spans.append((m.start(), m.end()))

        if types_found:
            return InteractionCheck(
                "pii_detected", "warn",
                f"输出含敏感信息: {', '.join(sorted(types_found))}",
                snippet=f"共{total_count}处匹配",
            )
        return InteractionCheck("pii_detected", "pass", "无PII泄漏")

    def _check_context_length(self, content: str) -> InteractionCheck:
        """近似 token 估算 (简易: 中文字 ≈1.5 token, 英文词 ≈1.3 token)"""
        # 简化估算: 字符数 / 2 作为粗略 token 数
        estimated_tokens = len(content) // 2
        if estimated_tokens > self.max_context_tokens:
            return InteractionCheck(
                "context_length", "warn",
                f"上下文长度 {estimated_tokens} tokens 超过限制 {self.max_context_tokens}",
            )
        return InteractionCheck("context_length", "pass", "上下文长度合规")

    # ---- 结果汇总 ----

    def _checks_to_flags(self, checks: list[InteractionCheck]) -> list[CheckFlag]:
        """将 InteractionCheck 转为通用 CheckFlag"""
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
            layer=DefenseLayer.MODEL_INTERACTION,
            flags=all_flags,
            trust_in=trust_level,
            t_start=t_start,
            content=content,
        )

    @staticmethod
    def _context_snippet(content: str, pos: int, width: int = 30) -> str:
        start = max(0, pos - width)
        end = min(len(content), pos + width)
        return content[start:end]
