# ============================================================
# Agent 适配层 — 防御引擎与真实 Agent 之间的桥梁
#
# 职责:
#   1. 包裹任意 Agent，在关键拦截点插入防御检查
#   2. 将 Agent 事件转为 DefenseContext
#   3. 根据防御结果决定 pass/block/warn
#
# 5 个拦截点 → 防御层映射:
#   wrap_input()        → L1 (源头治理) + L2 (输入过滤)
#   wrap_tool_call()    → L4 (工具约束)
#   wrap_memory_write() → L3 (记忆写入控制)
#   wrap_memory_read()  → L3 (记忆读取控制)
#   wrap_output()       → L2 (输出审查) + L5 (决策监督)
#
# 使用方式:
#   from agent_adapter import DefenseWrapper
#   wrapper = DefenseWrapper(agent, orchestrator)
#   result = wrapper.run_with_defense(user_input)
# ============================================================

import time
from typing import Optional, Any
from dataclasses import dataclass, field

try:
    from .defense_types import DefenseContext, DefenseMode, DefenseLayer
    from .layer4_tool_constraint import ToolCall
    from .orchestrator import DefenseOrchestrator
    from .mock_agent import MockAgent, AgentResponse
except ImportError:
    from defense_types import DefenseContext, DefenseMode, DefenseLayer
    from layer4_tool_constraint import ToolCall
    from orchestrator import DefenseOrchestrator
    from mock_agent import MockAgent, AgentResponse


@dataclass
class GuardedResponse:
    """被防御包装后的 Agent 响应"""
    success: bool
    content: str
    action: str                            # pass | warn | block
    blocked_by: str = ""                   # 哪个层拦截的
    blocked_reason: str = ""
    original_response: Optional[Any] = None  # 原始 AgentResponse (如果未拦截)
    layer_results: dict = field(default_factory=dict)
    risk_score: float = 0.0
    elapsed_ms: float = 0.0


class DefenseWrapper:
    """防御包装器 — 在 Agent 每次动作前后插入安全检查"""

    def __init__(
        self,
        agent: Any,
        orchestrator: DefenseOrchestrator,
        mode: DefenseMode = DefenseMode.BALANCED,
        verbose: bool = False,
    ):
        self.agent = agent
        self.orchestrator = orchestrator
        self.mode = mode
        self.verbose = verbose
        self._block_count = 0
        self._pass_count = 0
        self._warn_count = 0

    # ---- 主入口 ----

    def run_with_defense(
        self, user_input: str, source: str = "user_input"
    ) -> GuardedResponse:
        """
        完整防御流程：输入过滤 → Agent 执行 → 输出审查。
        这是最简单的使用方式，覆盖 L1+L2+L5。
        """
        t_start = time.perf_counter()

        # 1. 输入防御
        input_guard = self.wrap_input(user_input, source)
        if not input_guard.success:
            return input_guard

        # 2. 执行 Agent
        try:
            agent_resp = self.agent.receive_input(user_input, source)
        except Exception as e:
            return GuardedResponse(
                success=False,
                content=f"Agent error: {e}",
                action="block",
                blocked_by="agent_error",
            )

        # 2.5 检查 Agent 自身是否拒绝
        if not agent_resp.success:
            elapsed = (time.perf_counter() - t_start) * 1000
            self._block_count += 1
            return GuardedResponse(
                success=False,
                content=agent_resp.content,
                action="block",
                blocked_by="agent_internal",
                blocked_reason=f"Agent refused: {agent_resp.content[:100]}",
                original_response=agent_resp,
                elapsed_ms=elapsed,
            )

        # 3. 输出防御
        output_guard = self.wrap_output(agent_resp.content, source)
        if not output_guard.success:
            output_guard.original_response = agent_resp
            return output_guard

        elapsed = (time.perf_counter() - t_start) * 1000
        self._pass_count += 1

        return GuardedResponse(
            success=True,
            content=agent_resp.content,
            action="pass",
            original_response=agent_resp,
            layer_results=output_guard.layer_results,
            risk_score=output_guard.risk_score,
            elapsed_ms=elapsed,
        )

    def run_with_tools(
        self, user_input: str, source: str = "user_input"
    ) -> GuardedResponse:
        """
        完整防御流程 + 工具调用拦截。
        覆盖 L1+L2+L4+L5。
        """
        t_start = time.perf_counter()

        # 1. 输入防御
        input_guard = self.wrap_input(user_input, source)
        if not input_guard.success:
            return input_guard

        # 2. 执行 Agent
        try:
            agent_resp = self.agent.receive_input(user_input, source)
        except Exception as e:
            return GuardedResponse(
                success=False, content=f"Agent error: {e}",
                action="block", blocked_by="agent_error",
            )

        # 2.5 检查 Agent 自身是否拒绝
        if not agent_resp.success:
            elapsed = (time.perf_counter() - t_start) * 1000
            self._block_count += 1
            return GuardedResponse(
                success=False,
                content=agent_resp.content,
                action="block",
                blocked_by="agent_internal",
                blocked_reason=f"Agent refused: {agent_resp.content[:100]}",
                original_response=agent_resp,
                elapsed_ms=elapsed,
            )

        # 3. 如果 Agent 要调用工具 → 工具防御
        if agent_resp.action == "tool_call" and agent_resp.tool_name:
            tool_guard = self.wrap_tool_call(
                agent_resp.tool_name, agent_resp.tool_params, source
            )
            if not tool_guard.success:
                tool_guard.original_response = agent_resp
                return tool_guard

        # 4. 输出防御
        output_guard = self.wrap_output(agent_resp.content, source)
        if not output_guard.success:
            output_guard.original_response = agent_resp
            return output_guard

        elapsed = (time.perf_counter() - t_start) * 1000
        self._pass_count += 1

        return GuardedResponse(
            success=True,
            content=agent_resp.content,
            action="pass",
            original_response=agent_resp,
            layer_results=output_guard.layer_results,
            risk_score=output_guard.risk_score,
            elapsed_ms=elapsed,
        )

    # ---- 5 个拦截点 ----

    def wrap_input(
        self, user_input: str, source: str = "user_input"
    ) -> GuardedResponse:
        """
        拦截点 A: 输入过滤 → L1 + L2
        """
        ctx = DefenseContext(
            content=user_input,
            source=source,
            content_type="text",
            trust_level=1.0,
        )
        result = self.orchestrator.run(ctx)
        return self._to_guarded(result, "input")

    def wrap_tool_call(
        self, tool_name: str, params: dict, source: str = "agent_core"
    ) -> GuardedResponse:
        """
        拦截点 B: 工具调用 → L4
        """
        tc = ToolCall(tool_name=tool_name, params=params)
        # 将 params 序列化为 content 供规则引擎匹配
        import json
        content_str = json.dumps({"tool": tool_name, "params": params},
                                 ensure_ascii=False)
        ctx = DefenseContext(
            content=content_str,
            source=source,
            content_type="tool_call",
            trust_level=1.0,
        )
        result = self.orchestrator.run(ctx, tool_call=tc)
        return self._to_guarded(result, "tool_call")

    def wrap_memory_write(
        self, content: str, source: str = "user_input"
    ) -> GuardedResponse:
        """
        拦截点 C1: 记忆写入 → L3 + 实际持久化
        """
        ctx = DefenseContext(
            content=content,
            source=source,
            content_type="memory_write",
            trust_level=1.0,
        )
        result = self.orchestrator.run(ctx, memory_operation="write")
        guard = self._to_guarded(result, "memory_write")
        if not guard.success:
            return guard

        # 安全检查通过 → 实际写入后端
        l3 = self.orchestrator.get_layer(DefenseLayer.MEMORY_CONTROL)
        if l3 and hasattr(l3, 'write_entry'):
            allowed, action, entry = l3.write_entry(content, source)
            if not allowed:
                self._block_count += 1
                return GuardedResponse(
                    success=False,
                    content=f"Memory write rejected: {action}",
                    action="block",
                    blocked_by="memory_control",
                    blocked_reason=f"write_entry returned {action}",
                    risk_score=0.6,
                )
            guard.content = f"Remembered: {content[:80]}"
        return guard

    def wrap_memory_read(
        self, query: str, source: str = "user_input"
    ) -> GuardedResponse:
        """
        拦截点 C2: 记忆读取 → L3 + 实际检索
        """
        ctx = DefenseContext(
            content=query,
            source=source,
            content_type="memory_read",
            trust_level=1.0,
        )
        result = self.orchestrator.run(ctx, memory_operation="read")
        guard = self._to_guarded(result, "memory_read")
        if not guard.success:
            return guard

        # 安全检查通过 → 实际检索后端
        l3 = self.orchestrator.get_layer(DefenseLayer.MEMORY_CONTROL)
        if l3 and hasattr(l3, 'filter_read'):
            entries = l3.filter_read(query, top_k=5)
            if entries:
                contents = [e.get("content", "") for e in entries[:3]]
                guard.content = f"Recalled: {'; '.join(contents)}"
            else:
                guard.content = "No relevant memories found."
        return guard

    def wrap_output(
        self, output: str, source: str = "agent_core"
    ) -> GuardedResponse:
        """
        拦截点 D: 输出审查 → L2 + L5
        """
        ctx = DefenseContext(
            content=output,
            source=source,
            content_type="agent_output",
            trust_level=1.0,
        )
        result = self.orchestrator.run(ctx)
        return self._to_guarded(result, "output")

    # ---- 内部方法 ----

    def _to_guarded(self, result: Any, stage: str) -> GuardedResponse:
        """将 DefenseTestResult 转为 GuardedResponse"""
        if not result.passed:
            self._block_count += 1
            blocked_by = self._find_blocking_layer(result.layer_results)
            return GuardedResponse(
                success=False,
                content=f"[DEFENSE BLOCKED at {stage}] {result.final_action}",
                action="block",
                blocked_by=blocked_by or stage,
                blocked_reason=self._extract_reason(result.layer_results),
                layer_results={k: v for k, v in result.layer_results.items()
                               if v is not None},
                risk_score=result.risk_score,
            )

        if result.risk_score > 0:
            self._warn_count += 1
            return GuardedResponse(
                success=True,
                content="[DEFENSE WARN] Proceeding with warnings.",
                action="warn",
                layer_results={k: v for k, v in result.layer_results.items()
                               if v is not None},
                risk_score=result.risk_score,
            )

        self._pass_count += 1
        return GuardedResponse(
            success=True,
            content="",
            action="pass",
            layer_results={},
            risk_score=0.0,
        )

    @staticmethod
    def _find_blocking_layer(layer_results: dict) -> str:
        """找到第一个触发 block 的层"""
        order = ["source_governance", "model_interaction", "memory_control",
                 "tool_constraint", "decision_supervision"]
        for name in order:
            lr = layer_results.get(name)
            if lr and isinstance(lr, dict) and not lr.get("passed", True):
                return name
        return "unknown"

    @staticmethod
    def _extract_reason(layer_results: dict) -> str:
        """提取拦截原因"""
        reasons = []
        for name, lr in layer_results.items():
            if lr and isinstance(lr, dict):
                flags = lr.get("flags", [])
                if flags:
                    reasons.append(f"{name}: {'; '.join(flags[:2])}")
        return " | ".join(reasons[:3]) if reasons else "no details"

    # ---- 统计 ----

    def get_stats(self) -> dict:
        return {
            "pass_count": self._pass_count,
            "block_count": self._block_count,
            "warn_count": self._warn_count,
            "total": self._pass_count + self._block_count + self._warn_count,
            "block_rate": (self._block_count / max(1, self._pass_count + self._block_count + self._warn_count)),
        }

    def reset_stats(self):
        self._block_count = 0
        self._pass_count = 0
        self._warn_count = 0
