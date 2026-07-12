# ============================================================
# OpenAI 兼容防御代理 (Defense Proxy)
#
# 在 Agent 和 LLM 后端之间插入五层防御检测。
# 任意 OpenAI-compatible Agent 只需改 base_url 即可接入。
#
# 启动:
#   SET DEFENSE_BACKEND_API_KEY=sk-xxx
#   uvicorn defense_proxy:app --host 0.0.0.0 --port 8200
#
# Agent 侧:
#   client = OpenAI(base_url="http://localhost:8200/v1", api_key="no-needed")
# ============================================================

import json
import os
import sys
import time
import logging
from typing import Optional, Any

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# 确保可以导入同目录的防御模块
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---- 日志 ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s [PROXY] %(message)s")
logger = logging.getLogger("defense_proxy")


# ============================================================
# 配置
# ============================================================

def _get_mode(value: str):
    from defense_types import DefenseMode
    value = value.lower().strip()
    if value == "strict":
        return DefenseMode.STRICT
    if value == "permissive":
        return DefenseMode.PERMISSIVE
    return DefenseMode.BALANCED


class ProxyConfig:
    """从环境变量读取代理配置"""

    def __init__(self):
        # 修改此处填写你的 API Key（环境变量优先级更高）
        self.backend_url = os.getenv("DEFENSE_BACKEND_URL", "https://api.deepseek.com")
        self.backend_api_key = os.getenv("DEFENSE_BACKEND_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.backend_api_key:
            raise RuntimeError("Set DEFENSE_BACKEND_API_KEY or DEEPSEEK_API_KEY before starting defense_proxy")
        self.defense_mode = _get_mode(os.getenv("DEFENSE_MODE", "balanced"))
        self.request_timeout = float(os.getenv("DEFENSE_REQUEST_TIMEOUT", "120"))

    def __repr__(self):
        return (
            f"ProxyConfig(backend={self.backend_url!r}, mode={self.defense_mode.value}, "
            f"timeout={self.request_timeout}s)"
        )


# ============================================================
# 防御代理核心
# ============================================================

class DefenseProxy:
    """在 Agent ↔ LLM 之间插入五层防御检测的反向代理"""

    def __init__(self, config: ProxyConfig):
        self.config = config

        # 加载预设规则 (42 条)
        rules_path = os.path.join(ROOT, "config", "defense_rules.json")
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
        rules = [r for r in rules_data["rules"] if "rule_id" in r]

        from rule_engine import RuleEngine
        from orchestrator import DefenseOrchestrator

        self.engine = RuleEngine(rules)
        self.orchestrator = DefenseOrchestrator(self.engine, mode=config.defense_mode)

        logger.info("DefenseProxy initialized: %d rules, mode=%s",
                     self.engine.rule_count, config.defense_mode.value)

    # ---- 公开方法 ----

    def check_input(self, messages: list[dict]) -> dict:
        """逐条检查输入消息 → 返回 {passed, action, risk_score, reasons, layer_results}"""
        from defense_types import DefenseContext

        total_risk = 0.0
        reasons = []
        blocked = False
        all_layer_results = []

        for i, msg in enumerate(messages):
            content = self._extract_content(msg)
            if not content:
                continue

            role = msg.get("role", "unknown")

            ctx = DefenseContext(
                content=str(content),
                source="verified_api",  # 代理是受信任的中间层
                content_type="text",
                trust_level=1.0,
            )
            result = self.orchestrator.run(ctx)

            total_risk = max(total_risk, result.risk_score)

            # 收集该消息的逐层详情
            msg_layers = self._simplify_layers(result.layer_results)
            all_layer_results.append({
                "msg_index": i,
                "role": role,
                "content_preview": str(content)[:80],
                "layers": msg_layers,
                "overall_risk": result.risk_score,
                "overall_passed": result.passed,
            })

            if not result.passed:
                blocked = True
                blocked_layer = self._find_blocking_layer(result.layer_results)
                reasons.append(
                    f"[{role}] msg#{i} blocked by {blocked_layer}: "
                    f"{self._extract_flags(result.layer_results)}"
                )
            elif result.risk_score > 0:
                flags = self._extract_flags(result.layer_results)
                if flags:
                    reasons.append(f"[{role}] msg#{i} warned: {flags}")

        return {
            "passed": not blocked,
            "action": "block" if blocked else ("warn" if total_risk > 0 else "pass"),
            "risk_score": min(total_risk, 1.0),
            "reasons": reasons,
            "layer_results": all_layer_results,
        }

    def check_output(self, response_body: dict) -> dict:
        """检查 LLM 响应 (content + tool_calls) → 返回 {passed, action, risk_score, reasons, layer_results}"""
        from defense_types import DefenseContext
        from layer4_tool_constraint import ToolCall

        reasons = []
        cumulative_risk = 0.0
        blocked = False
        all_layer_results = []

        choices = response_body.get("choices", [])
        if not choices:
            return {"passed": True, "action": "pass", "risk_score": 0.0, "reasons": [], "layer_results": []}

        message = choices[0].get("message", {}) or choices[0].get("delta", {})

        # 1. 检查输出文本
        content = message.get("content")
        if content and isinstance(content, str) and content.strip():
            ctx = DefenseContext(
                content=content,
                source="verified_api",
                content_type="agent_output",
                trust_level=1.0,
            )
            result = self.orchestrator.run(ctx)
            cumulative_risk = max(cumulative_risk, result.risk_score)
            all_layer_results.append({
                "check": "output_content",
                "content_preview": str(content)[:80],
                "layers": self._simplify_layers(result.layer_results),
                "overall_risk": result.risk_score,
                "overall_passed": result.passed,
            })
            if not result.passed:
                blocked = True
                reasons.append(f"output content blocked: {self._extract_flags(result.layer_results)}")
            elif result.risk_score > 0:
                f = self._extract_flags(result.layer_results)
                if f:
                    reasons.append(f"output content warned: {f}")

        # 2. 检查工具调用
        tool_calls = message.get("tool_calls") or []
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "unknown")
            tool_args = func.get("arguments", "{}")

            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    tool_args = {"raw": tool_args}

            tool_call_obj = ToolCall(tool_name=tool_name, params=tool_args)
            content_str = json.dumps(
                {"tool": tool_name, "params": tool_args}, ensure_ascii=False
            )

            ctx = DefenseContext(
                content=content_str,
                source="verified_api",
                content_type="tool_call",
                trust_level=1.0,
            )
            result = self.orchestrator.run(ctx, tool_call=tool_call_obj)
            cumulative_risk = max(cumulative_risk, result.risk_score)
            all_layer_results.append({
                "check": f"tool_call:{tool_name}",
                "content_preview": content_str[:120],
                "layers": self._simplify_layers(result.layer_results),
                "overall_risk": result.risk_score,
                "overall_passed": result.passed,
            })
            if not result.passed:
                blocked = True
                reasons.append(f"tool_call '{tool_name}' blocked by L4")
            elif result.risk_score > 0:
                reasons.append(f"tool_call '{tool_name}' warned (risk={result.risk_score:.2f})")

        return {
            "passed": not blocked,
            "action": "block" if blocked else ("warn" if cumulative_risk > 0 else "pass"),
            "risk_score": min(cumulative_risk, 1.0),
            "reasons": reasons,
            "layer_results": all_layer_results,
        }

    async def forward(self, body: dict, headers: dict) -> httpx.Response:
        """将请求转发到后端 LLM"""
        url = f"{self.config.backend_url}/v1/chat/completions"

        # 构建转发请求头 (透传部分头, 注入正确的 API Key)
        forward_headers = {
            "Content-Type": "application/json",
        }
        if self.config.backend_api_key:
            forward_headers["Authorization"] = f"Bearer {self.config.backend_api_key}"

        async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
            return await client.post(url, json=body, headers=forward_headers)

    # ---- 内部方法 ----

    @staticmethod
    def _extract_content(msg: dict) -> Optional[str]:
        """从消息中提取文本内容 (兼容 string 和数组格式)"""
        content = msg.get("content", "")
        if content is None:
            return None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(str(part.get("text", "")))
                    elif "text" in part:
                        parts.append(str(part["text"]))
            return " ".join(parts) if parts else None
        return str(content)

    @staticmethod
    def _find_blocking_layer(layer_results: dict) -> str:
        order = ["source_governance", "model_interaction", "memory_control",
                 "tool_constraint", "decision_supervision"]
        for name in order:
            lr = layer_results.get(name)
            if lr and isinstance(lr, dict) and not lr.get("passed", True):
                return name
        return "unknown"

    @staticmethod
    def _extract_flags(layer_results: dict) -> str:
        parts = []
        for name, lr in layer_results.items():
            if lr and isinstance(lr, dict):
                flags = lr.get("flags", [])
                if flags:
                    parts.append(f"{name}:[{', '.join(flags[:3])}]")
        return "; ".join(parts)

    @staticmethod
    def _simplify_layers(layer_results: dict) -> list[dict]:
        """提取逐层关键信息，用于 API 响应"""
        order = ["source_governance", "model_interaction", "memory_control",
                 "tool_constraint", "decision_supervision"]
        simplified = []
        for name in order:
            lr = layer_results.get(name)
            if lr is None:
                simplified.append({
                    "layer": name, "status": "disabled",
                    "passed": True, "action": "pass", "risk_score": 0.0,
                    "flags": [], "matched_rules": [], "trust_level": 1.0, "processing_ms": 0,
                })
                continue
            if isinstance(lr, dict):
                simplified.append({
                    "layer": name,
                    "passed": lr.get("passed", True),
                    "action": lr.get("action", "pass"),
                    "risk_score": lr.get("risk_score", 0.0),
                    "flags": lr.get("flags", []),
                    "matched_rules": lr.get("matched_rules", []),
                    "trust_level": lr.get("trust_level", 1.0),
                    "processing_ms": lr.get("processing_time_ms", 0),
                })
        return simplified

    @staticmethod
    def print_layer_table(label: str, layer_results_list: list[dict]):
        """将逐层结果以表格形式打印到控制台"""
        SEP = "=" * 70
        SUB = "-" * 70

        print(f"\n{SEP}")
        print(f"  [DEFENSE LAYERS] {label}")
        print(SEP)

        for entry in layer_results_list:
            # 每条消息/检查点
            if "msg_index" in entry:
                print(f"  Message #{entry['msg_index']} [{entry['role']}]: "
                      f"\"{entry['content_preview'][:60]}\"")
            else:
                print(f"  Check: {entry.get('check', '?')} | "
                      f"\"{entry.get('content_preview', '')[:60]}\"")
            print(f"  Overall: {'BLOCK' if not entry['overall_passed'] else 'PASS'} | "
                  f"risk={entry['overall_risk']:.2f}")
            print(SUB)

            layers = entry.get("layers", [])
            if not layers:
                print("  (no layer results)")
                continue

            # 表头
            print(f"  {'Layer':<24s} {'Action':<8s} {'Risk':<6s} {'Trust':<7s} {'Rules'}")

            for lr in layers:
                name = lr.get("layer", "?")
                action = lr.get("action", "pass")
                risk = lr.get("risk_score", 0.0)
                trust = lr.get("trust_level", 1.0)
                rules = ", ".join(lr.get("matched_rules", [])[:3]) or "-"
                flags = lr.get("flags", [])
                flag_str = f" [{', '.join(flags[:2])}]" if flags else ""

                status_icon = {
                    "block": "BLOCK", "quarantine": "QUAR",
                    "warn": "WARN", "pass": "pass", "log": "log",
                }.get(action, action)

                print(f"  {name:<24s} {status_icon:<8s} {risk:<6.2f} {trust:<7.2f} {rules}{flag_str}")

            print(SUB)

# 创建代理实例
_proxy_config = ProxyConfig()
_proxy = DefenseProxy(_proxy_config)

app = FastAPI(
    title="LLM Agent Defense Proxy",
    description="OpenAI-compatible reverse proxy with 5-layer defense interception",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 错误响应 ----

def _blocked_response(reasons: list[str], risk_score: float,
                      layer_results: list[dict] | None = None) -> JSONResponse:
    """OpenAI 兼容的内容过滤错误响应"""
    detail = "; ".join(reasons) if reasons else "Content blocked by defense engine"
    logger.warning("BLOCKED (risk=%.2f): %s", risk_score, detail)
    content = {
        "error": {
            "message": detail,
            "type": "content_filter",
            "code": "content_filter",
            "param": None,
        },
        "defense_risk_score": risk_score,
    }
    if layer_results:
        content["defense_layer_details"] = layer_results
    return JSONResponse(status_code=400, content=content)


# ---- 核心端点 ----

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI 兼容的聊天补全端点，经过五层防御检测。

    输入侧: 提取 messages → L1(源头治理) + L2(模型交互)
    输出侧: 提取 content + tool_calls → L4(工具约束) + L2 + L5(决策监督)
    """
    body = await request.json()
    messages = body.get("messages", [])
    is_stream = body.get("stream", False)

    t_start = time.perf_counter()

    # ---- 1. 输入防御 ----
    input_result = _proxy.check_input(messages)

    # 控制台打印逐层详情
    input_layers = input_result.get("layer_results", [])
    if input_layers:
        _proxy.print_layer_table(f"INPUT ({len(messages)} messages)", input_layers)

    if not input_result["passed"]:
        logger.info("Input blocked (%.1fms)", (time.perf_counter() - t_start) * 1000)
        return _blocked_response(input_result["reasons"], input_result["risk_score"],
                                input_result.get("layer_results"))

    if input_result["reasons"]:
        logger.info("Input warnings: %s", "; ".join(input_result["reasons"]))

    # ---- 2. 转发到后端 ----
    try:
        backend_resp = await _proxy.forward(body, dict(request.headers))
    except httpx.TimeoutException:
        logger.error("Backend timeout after %.1fs", _proxy.config.request_timeout)
        raise HTTPException(504, "Backend LLM timeout")
    except httpx.ConnectError as e:
        logger.error("Backend connection failed: %s", e)
        raise HTTPException(502, f"Cannot connect to backend: {_proxy.config.backend_url}")

    # ---- 3. 输出防御 ----
    if is_stream:
        return await _handle_streaming(backend_resp, t_start)

    # 非流式 — 直接解析响应 JSON 并检查
    try:
        response_body = backend_resp.json()
    except json.JSONDecodeError:
        logger.error("Backend returned non-JSON: %s", backend_resp.text[:200])
        raise HTTPException(502, "Backend returned invalid JSON")

    # 检查后端是否返回了错误
    if "error" in response_body:
        logger.warning("Backend error: %s", response_body["error"])
        return JSONResponse(status_code=backend_resp.status_code, content=response_body)

    output_result = _proxy.check_output(response_body)

    # 控制台打印逐层详情
    output_layers = output_result.get("layer_results", [])
    if output_layers:
        _proxy.print_layer_table("OUTPUT", output_layers)

    if not output_result["passed"]:
        logger.info("Output blocked (%.1fms)", (time.perf_counter() - t_start) * 1000)
        return _blocked_response(output_result["reasons"], output_result["risk_score"],
                                output_result.get("layer_results"))

    if output_result["reasons"]:
        logger.info("Output warnings: %s", "; ".join(output_result["reasons"]))

    # 附加防御元数据到响应
    response_body["defense"] = {
        "risk_score": max(input_result["risk_score"], output_result["risk_score"]),
        "input_verdict": input_result["action"],
        "output_verdict": output_result["action"],
        "processing_ms": round((time.perf_counter() - t_start) * 1000, 1),
        "input_layers": input_result.get("layer_results", []),
        "output_layers": output_result.get("layer_results", []),
    }

    elapsed = (time.perf_counter() - t_start) * 1000
    logger.info("PASS (%.1fms, risk=%.2f)", elapsed,
                max(input_result["risk_score"], output_result["risk_score"]))

    return JSONResponse(status_code=backend_resp.status_code, content=response_body)


# ---- 流式处理 ----

async def _handle_streaming(backend_resp: httpx.Response, t_start: float):
    """缓冲流式响应 → 拼装 → 输出防御 → 重新流式输出或拦截"""

    chunks: list[bytes] = []
    accumulated_content = ""
    accumulated_tool_calls: dict[int, dict] = {}

    # 1. 读取所有 SSE 分块
    async for chunk in backend_resp.aiter_bytes():
        chunks.append(chunk)
        try:
            text = chunk.decode("utf-8", errors="replace")
            for line in text.split("\n"):
                if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                    try:
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})

                        # 累积文本
                        if "content" in delta and delta["content"]:
                            accumulated_content += delta["content"]

                        # 累积 tool_calls
                        for tc in delta.get("tool_calls", []):
                            idx = tc.get("index", 0)
                            if idx not in accumulated_tool_calls:
                                accumulated_tool_calls[idx] = {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            entry = accumulated_tool_calls[idx]
                            if "id" in tc and tc["id"]:
                                entry["id"] = tc["id"]
                            if tc.get("function", {}).get("name"):
                                entry["function"]["name"] += tc["function"]["name"]
                            if tc.get("function", {}).get("arguments"):
                                entry["function"]["arguments"] += tc["function"]["arguments"]
                    except (json.JSONDecodeError, KeyError):
                        pass
        except UnicodeDecodeError:
            pass

    # 2. 构造模拟的非流式响应用于检测
    simulated_response = {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": accumulated_content or None,
                "tool_calls": (
                    [accumulated_tool_calls[k] for k in sorted(accumulated_tool_calls)]
                    if accumulated_tool_calls else None
                ),
            },
        }],
    }

    output_result = _proxy.check_output(simulated_response)
    if not output_result["passed"]:
        logger.info("Stream output blocked (%.1fms)", (time.perf_counter() - t_start) * 1000)
        # 返回一个 SSE 格式的错误
        error_data = {
            "error": {
                "message": "; ".join(output_result["reasons"]),
                "type": "content_filter",
                "code": "content_filter",
            },
            "defense_risk_score": output_result["risk_score"],
        }

        async def error_stream():
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    if output_result["reasons"]:
        logger.info("Stream output warnings: %s", "; ".join(output_result["reasons"]))

    # 3. 安全 → 重新输出原始分块
    elapsed = (time.perf_counter() - t_start) * 1000
    logger.info("PASS STREAM (%.1fms, risk=%.2f)", elapsed, output_result["risk_score"])

    async def safe_stream():
        for chunk in chunks:
            yield chunk

    return StreamingResponse(safe_stream(), media_type="text/event-stream")


# ---- 兼容性端点 ----

@app.get("/v1/models")
async def list_models():
    """透传到后端获取模型列表 (兼容性)"""
    url = f"{_proxy_config.backend_url}/v1/models"
    headers = {}
    if _proxy_config.backend_api_key:
        headers["Authorization"] = f"Bearer {_proxy_config.backend_api_key}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        logger.warning("GET /v1/models failed: %s", e)
        # 返回一个基本模型列表作为降级
        return {"object": "list", "data": [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
        ]}


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "defense_proxy",
        "backend": _proxy_config.backend_url,
        "mode": _proxy_config.defense_mode.value,
        "rules_loaded": _proxy.engine.rule_count,
        "rules_enabled": _proxy.engine.enabled_rule_count,
    }


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("DEFENSE_PROXY_PORT", "8200"))
    logger.info("Starting Defense Proxy on port %d", port)
    logger.info("Config: %s", _proxy_config)
    uvicorn.run(app, host="0.0.0.0", port=port)
