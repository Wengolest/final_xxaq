# ============================================================
# Agent E — Smolagents 代码执行 Agent (替代 Autogen)
#
# 角色: 运维/数据分析 Agent, 使用 HuggingFace Smolagents CodeAgent
# 测试: L1(源头治理) + L2(模型交互) + L4(工具约束)
# 攻击: 工具滥用、危险命令注入、权限绕过
#
# 接入: OpenAIServerModel.api_base → defense_proxy (:8200)
# ============================================================

import sys
import io
import httpx
from smolagents import CodeAgent
from smolagents.models import OpenAIServerModel

PROXY_URL = "http://localhost:8200/v1"


class SmolToolAgent:
    """基于 HuggingFace Smolagents CodeAgent 的工具调用 Agent"""

    def __init__(
        self,
        model_id: str = "deepseek-chat",
        api_base: str = PROXY_URL,
    ):
        self.model_id = model_id
        self.api_base = api_base

        self.model = OpenAIServerModel(
            model_id=model_id,
            api_base=api_base,
            api_key="no-needed",
        )
        self.agent = CodeAgent(
            tools=[],
            model=self.model,
            additional_authorized_imports=["json", "math", "re", "datetime"],
        )

    def run(self, user_input: str) -> dict:
        """执行用户请求, 经 defense_proxy 转发, 返回 verdict 兼容格式"""
        try:
            result = self.agent.run(user_input)

            # Smolagents 不暴露 defense 元数据 → 直接发一份到 proxy 拿 defense
            try:
                body = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": user_input}],
                    "max_tokens": 1,  # 只要 defense, 不要 LLM 生成
                }
                raw = httpx.post(
                    self.api_base + "/chat/completions",
                    json=body, timeout=30.0,
                )
                resp_body = raw.json()
                defense = resp_body.get("defense", {})
                # 检查是否被拦截
                if raw.status_code == 400 and "content_filter" in str(
                    resp_body.get("error", {}).get("type", "")
                ):
                    return {
                        "status": "blocked",
                        "agent": "smol_tool",
                        "model": self.model_id,
                        "defense_risk_score": resp_body.get("defense_risk_score", 0.7),
                        "defense_layer_details": resp_body.get("defense_layer_details", []),
                        "error": resp_body.get("error", {}).get("message", ""),
                    }
            except Exception:
                defense = {}

            return {
                "status": "ok",
                "reply": str(result) if result else "",
                "model": self.model_id,
                "agent": "smol_tool",
                "defense": defense,
            }
        except Exception as e:
            error_str = str(e)
            is_blocked = any(
                kw in error_str.lower()
                for kw in ["content_filter", "blocked", "defense", "400"]
            )
            return {
                "status": "blocked" if is_blocked else "error",
                "agent": "smol_tool",
                "model": self.model_id,
                "error_type": type(e).__name__,
                "error": error_str,
            }
