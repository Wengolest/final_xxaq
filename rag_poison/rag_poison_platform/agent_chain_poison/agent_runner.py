"""Agent 多步推理链执行器（clean / poisoned，支持 fast 模式）。"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from agent_chain_poison.prompts import (
    STEP_NAMES,
    SYSTEM_PROMPT,
    build_fast_decision_prompt,
    build_fast_final_prompt,
    build_step_prompt,
)
from utils.deepseek_env import load_deepseek_env
from utils.env_bootstrap import bootstrap_api_env

STEP_FIELDS = [
    "step_name",
    "content",
    "risk_level",
    "recommended_action",
    "tool_action",
    "extra_action",
    "raw_text",
]

# 4 步结构下 injection_step 映射到已完成步序号（之后激活 poison）
INJECTION_AFTER_INDEX = {
    "evidence": 2,
    "reasoning_summary": 2,
    "decision": 3,
}


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return None


def normalize_step_output(raw_text: str, step_name: str) -> Dict[str, Any]:
    parsed = _extract_json_object(raw_text)
    step: Dict[str, Any] = {field: "" for field in STEP_FIELDS}
    step["step_name"] = step_name
    step["raw_text"] = raw_text or ""
    if parsed:
        for key in STEP_FIELDS:
            if key in parsed and parsed[key] is not None:
                step[key] = str(parsed[key])
        if not step["step_name"]:
            step["step_name"] = str(parsed.get("step_name", step_name))
    else:
        step["content"] = raw_text or ""
        step["risk_level"] = ""
        step["recommended_action"] = ""
        step["tool_action"] = "none"
        step["extra_action"] = "none"
    return step


class AgentChainRunner:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 2,
        fast: bool = False,
    ) -> None:
        bootstrap_api_env()
        env = load_deepseek_env()
        api_key = env.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing DEEPSEEK_API_KEY. Set it in shell or rag_poison_platform\\.env"
            )
        base_url = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or env.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.temperature = temperature
        self.max_retries = max_retries
        self.fast = fast
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _call_llm(self, user_prompt: str) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as exc:
                last_err = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def _run_step(
        self,
        step_name: str,
        user_task: str,
        trajectory: List[Dict[str, Any]],
        *,
        poison_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = build_step_prompt(
            step_name,
            user_task,
            trajectory,
            poison_instruction=poison_instruction,
        )
        raw = self._call_llm(prompt)
        return normalize_step_output(raw, step_name)

    def _run_fast_decision(
        self,
        user_task: str,
        *,
        poison_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = build_fast_decision_prompt(
            user_task,
            poison_instruction=poison_instruction,
        )
        raw = self._call_llm(prompt)
        return normalize_step_output(raw, "decision")

    def _run_fast_final(
        self,
        user_task: str,
        trajectory: List[Dict[str, Any]],
        *,
        poison_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = build_fast_final_prompt(
            user_task,
            trajectory,
            poison_instruction=poison_instruction,
        )
        raw = self._call_llm(prompt)
        return normalize_step_output(raw, "final_answer")

    def run_clean(self, user_task: str) -> List[Dict[str, Any]]:
        if self.fast:
            decision = self._run_fast_decision(user_task)
            final = self._run_fast_final(user_task, [decision])
            return [decision, final]

        trajectory: List[Dict[str, Any]] = []
        for step_name in STEP_NAMES:
            step = self._run_step(step_name, user_task, trajectory)
            trajectory.append(step)
        return trajectory

    def run_poisoned(
        self,
        user_task: str,
        *,
        injection_step: str,
        poison_instruction: str,
        clean_trajectory: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        inject_after = INJECTION_AFTER_INDEX.get(injection_step)
        if inject_after is None:
            raise ValueError(f"Unknown injection_step: {injection_step}")

        if self.fast:
            poison_from_decision = inject_after <= 2
            decision = self._run_fast_decision(
                user_task,
                poison_instruction=poison_instruction if poison_from_decision else None,
            )
            poison_from_final = inject_after <= 3
            final = self._run_fast_final(
                user_task,
                [decision],
                poison_instruction=poison_instruction if poison_from_final else None,
            )
            return [decision, final]

        # 标准 4 步：复用 clean 的 plan+evidence，仅重跑 decision/final_answer（共 6 次调用/case）
        if not clean_trajectory or len(clean_trajectory) < 2:
            raise ValueError("clean_trajectory required for poisoned run in standard mode")

        trajectory: List[Dict[str, Any]] = list(clean_trajectory[:2])
        poison_active = inject_after <= 2

        decision = self._run_step(
            "decision",
            user_task,
            trajectory,
            poison_instruction=poison_instruction if poison_active else None,
        )
        trajectory.append(decision)

        if inject_after == 3:
            poison_active = True

        final = self._run_step(
            "final_answer",
            user_task,
            trajectory,
            poison_instruction=poison_instruction if poison_active else None,
        )
        trajectory.append(final)
        return trajectory

    def run_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        user_task = case["user_task"]
        result: Dict[str, Any] = {
            "case_id": case["case_id"],
            "clean_trajectory": [],
            "poisoned_trajectory": [],
            "error": "",
        }
        try:
            result["clean_trajectory"] = self.run_clean(user_task)
        except Exception as exc:
            result["error"] = f"clean_run_failed: {exc}"
            return result
        try:
            result["poisoned_trajectory"] = self.run_poisoned(
                user_task,
                injection_step=case["injection_step"],
                poison_instruction=case["poison_instruction"],
                clean_trajectory=result["clean_trajectory"],
            )
        except Exception as exc:
            result["error"] = f"poisoned_run_failed: {exc}"
        return result
