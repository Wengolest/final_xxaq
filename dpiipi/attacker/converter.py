"""AttackResult → ExperimentRecord 转换器.

将单轮 DPI 攻击结果转换为 AgentAuditor 兼容的交互轨迹格式。
当攻击器未来支持多轮工具调用时，此转换器也应升级以生成完整的多轮轨迹。
"""

from __future__ import annotations

import re
from typing import Any

from shared.trajectory import ExperimentRecord, TrajectoryTurn

# ── Scenario 映射 ───────────────────────────────────────────

_AGENT_TO_SCENARIO: dict[str, str] = {
    "system_admin_agent": "system",
    "financial_analyst_agent": "finance",
    "academic_search_agent": "search",
    "legal_consultant_agent": "legal",
    "medical_advisor_agent": "medical",
    "info_security_agent": "privacy",
}

# 从 tool_name 推断 scenario 的关键词 fallback
_TOOL_KEYWORD_SCENARIO: dict[str, str] = {
    "access": "authorization",
    "resource": "system",
    "transaction": "finance",
    "data": "privacy",
    "exfil": "privacy",
    "citation": "search",
    "precedent": "legal",
    "diagnosis": "medical",
    "sensitive": "privacy",
    "disclosure": "privacy",
}

# 中文目标描述到 scenario 的映射
_GOAL_KEYWORD_SCENARIO: dict[str, str] = {
    "系统": "system",
    "资源": "system",
    "权限": "authorization",
    "交易": "finance",
    "支付": "finance",
    "财务": "finance",
    "学术": "search",
    "引文": "search",
    "法律": "legal",
    "判例": "legal",
    "诊断": "medical",
    "医疗": "medical",
    "敏感": "privacy",
    "泄露": "privacy",
    "数据": "privacy",
}


def map_to_scenario(tool_name: str = "", attack_goal: str = "", corresponding_agent: str = "") -> str:
    """将攻击工具信息映射为 scenario 分类.

    优先级: corresponding_agent > tool_name 关键词 > attack_goal 关键词 > "general"
    """
    if corresponding_agent and corresponding_agent in _AGENT_TO_SCENARIO:
        return _AGENT_TO_SCENARIO[corresponding_agent]

    combined = f"{tool_name} {attack_goal}".lower()
    for keyword, scenario in _TOOL_KEYWORD_SCENARIO.items():
        if keyword in combined:
            return scenario

    for keyword, scenario in _GOAL_KEYWORD_SCENARIO.items():
        if keyword in attack_goal:
            return scenario

    return "general"


# ── 转换逻辑 ────────────────────────────────────────────────


def _extract_thought_and_action(response_text: str) -> tuple[str, str]:
    """从模型响应文本中尽可能提取 thought 和 action.

    当前目标模型 (qwen2:0.5b) 不返回 CoT/工具调用，因此:
    - thought: 简略描述 agent 收到了注入指令
    - action: 将整个 response 作为 Final Answer

    当目标模型升级为支持 tool-calling 的 ReAct agent 时，此函数应升级
    以解析 thought/action/observation 等多轮结构。
    """
    text = (response_text or "").strip()

    # 尝试检测 ReAct 风格: "Thought: ... Action: ..."
    thought_match = re.search(r"(?:Thought|思考|分析)[：:]\s*(.+?)(?=(?:Action|行动|操作)[：:]|\Z)", text, re.DOTALL | re.IGNORECASE)
    action_match = re.search(r"(?:Action|行动|操作)[：:]\s*(.+)", text, re.DOTALL | re.IGNORECASE)

    if thought_match and action_match:
        return thought_match.group(1).strip(), action_match.group(1).strip()

    # 尝试检测 JSON 工具调用格式
    tool_match = re.search(r'"tool_name"\s*:\s*"(\w+)"', text)
    if tool_match:
        tool_name = tool_match.group(1)
        params_match = re.search(r'"parameters"\s*:\s*(\{.+?\})', text, re.DOTALL)
        params = params_match.group(1) if params_match else "{}"
        thought = f"Agent decided to call tool '{tool_name}'."
        action = f"{tool_name}{params}"
        return thought, action

    # Fallback: 整个响应视为 Final Answer
    thought = "Agent received the user request (which may contain injected instructions) and generated a response."
    action = f"Final Answer: {text}"
    return thought, action


def attack_result_to_record(
    result: Any,  # AttackResult
    system_prompt: str = "You are a helpful assistant.",
    scenario: str = "",
) -> ExperimentRecord:
    """将单次 DPI 攻击结果转换为 ExperimentRecord.

    Args:
        result: AttackResult 对象 (from attacker.orchestrator)
        system_prompt: 目标模型的 system prompt
        scenario: 场景分类，空字符串则自动推断

    Returns: ExperimentRecord
    """
    # 推断 scenario
    if not scenario:
        # 尝试从 AttackResult 的属性推断
        tool_name = getattr(result, "tool_name", "")
        attack_goal = getattr(result, "attack_goal", "")
        scenario = map_to_scenario(tool_name=tool_name, attack_goal=attack_goal)

    # 构建轨迹
    user_content = getattr(result, "injected_prompt", "")
    response_text = getattr(result, "response_text", "")

    thought, action = _extract_thought_and_action(response_text)

    turns = [
        TrajectoryTurn(role="user", content=user_content),
        TrajectoryTurn(role="agent", thought=thought, action=action),
    ]

    # 判断 label
    attack_successful = getattr(result, "attack_successful", False)
    label = 1 if attack_successful else 0

    # 构建 risk_description
    scorer_reasoning = getattr(result, "scorer_reasoning", "")
    attack_goal = getattr(result, "attack_goal", "")
    tool_name = getattr(result, "tool_name", "")
    variant = getattr(result, "variant", "")

    if scorer_reasoning:
        risk_description = scorer_reasoning
    elif attack_successful:
        risk_description = (
            f"Agent followed the injected instruction via '{tool_name}' "
            f"(variant: {variant}). Attack goal: {attack_goal}"
        )
    else:
        risk_description = (
            f"Agent did NOT follow the injected instruction via '{tool_name}' "
            f"(variant: {variant}). Attack was unsuccessful."
        )

    return ExperimentRecord(
        id=str(getattr(result, "case_id", "")),
        scenario=scenario,
        profile=system_prompt,
        contents=[turns],
        label=label,
        risk_description=risk_description,
    )


# ═══════════════════════════════════════════════════════════════
# IPI 结果 → ExperimentRecord 转换
# ═══════════════════════════════════════════════════════════════


def ipi_result_to_record(
    result: Any,  # IPIAttackResult
    system_prompt: str = "You are a helpful assistant.",
    scenario: str = "",
) -> ExperimentRecord:
    """将 IPI 攻击结果转换为 ExperimentRecord — 生成完整的 4 轮轨迹.

    IPI 轨迹结构:
        user → agent(thought + tool_call) → environment(contaminated output) → agent(thought + final action)

    这与 experiment_20.json 的格式一致——注入点在 environment（工具返回值）中，
    而非 user prompt 中。这是 DPI 和 IPI 的本质区别。

    Args:
        result: IPIAttackResult 对象 (from attacker.orchestrator)
        system_prompt: 目标模型的 system prompt
        scenario: 场景分类，空字符串则自动推断

    Returns: ExperimentRecord（含 4 轮轨迹）
    """
    user_task = getattr(result, "user_task", "")
    thought_1 = getattr(result, "thought_1", "")
    tool_call_name = getattr(result, "tool_call_name", "")
    tool_call_args = getattr(result, "tool_call_args", "{}")
    observation = getattr(result, "observation", "")
    thought_2 = getattr(result, "thought_2", "")
    final_action = getattr(result, "final_action", "")

    # 构造 action 字符串（仿 experiment_20.json 格式）
    action_1 = f"{tool_call_name}{tool_call_args}"

    # 推断 scenario
    if not scenario:
        scenario = getattr(result, "scenario", "general") or "general"

    turns = [
        TrajectoryTurn(role="user", content=user_task),
        TrajectoryTurn(role="agent", thought=thought_1, action=action_1),
        TrajectoryTurn(role="environment", content=observation),
        TrajectoryTurn(role="agent", thought=thought_2, action=final_action),
    ]

    # 判断 label
    attack_successful = getattr(result, "attack_successful", False)
    label = 1 if attack_successful else 0

    # risk_description
    scorer_reasoning = getattr(result, "scorer_reasoning", "")
    attack_goal = getattr(result, "attack_goal", "")

    if scorer_reasoning:
        risk_description = scorer_reasoning
    elif attack_successful:
        risk_description = (
            f"Agent followed the injected instruction from tool output "
            f"(scenario: {scenario}). Attack goal: {attack_goal}"
        )
    else:
        risk_description = (
            f"Agent did NOT follow the injected instruction from tool output "
            f"(scenario: {scenario}). IPI attack was unsuccessful."
        )

    return ExperimentRecord(
        id=str(getattr(result, "case_id", "")),
        scenario=scenario,
        profile=system_prompt,
        contents=[turns],
        label=label,
        risk_description=risk_description,
    )
