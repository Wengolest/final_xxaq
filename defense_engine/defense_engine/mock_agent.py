# ============================================================
# Mock Agent — 模拟 Agent，用于防御引擎端到端验证
#
# 零外部依赖。模拟 3 种角色的 Agent 行为：
#   - assistant:  个人助手（问答 + 记忆）
#   - devops:     运维 Agent（文件/命令/配置 + 工具调用）
#   - research:   研究 Agent（RAG 检索 + 长记忆）
#
# 4 个拦截点对应防御引擎 5 层：
#   1. receive_input()   → L1 (源头) + L2 (交互输入)
#   2. tool_call()       → L4 (工具约束)
#   3. memory_write/read → L3 (记忆控制)
#   4. produce_output()  → L2 (输出审查) + L5 (决策监督)
#
# 使用方式：
#   from mock_agent import MockAgent
#   agent = MockAgent(role="devops")
#   response = agent.receive_input("deploy to production")
# ============================================================

import time
import hashlib
from typing import Optional, Any
from dataclasses import dataclass, field


# ---- 角色定义 ----

ROLE_DEFINITIONS = {
    "assistant": {
        "name": "PersonalAssistant",
        "allowed_tools": ["web_search", "calculator", "read_file"],
        "has_memory": True,
        "has_rag": False,
        "has_file_write": False,
        "has_system_command": False,
        "system_prompt": "You are a helpful personal assistant.",
    },
    "devops": {
        "name": "DevOpsAgent",
        "allowed_tools": ["read_file", "write_file", "execute_command",
                          "db_query", "db_write", "send_email", "call_api"],
        "has_memory": True,
        "has_rag": False,
        "has_file_write": True,
        "has_system_command": True,
        "system_prompt": "You are a DevOps automation agent. You can manage files, "
                         "run commands, and deploy services.",
    },
    "research": {
        "name": "ResearchAgent",
        "allowed_tools": ["web_search", "web_fetch", "read_file",
                          "search_content", "list_directory"],
        "has_memory": True,
        "has_rag": True,
        "has_file_write": False,
        "has_system_command": False,
        "system_prompt": "You are a research assistant with access to "
                         "knowledge bases and web search.",
    },
}


# ---- 数据结构 ----

@dataclass
class AgentResponse:
    success: bool
    content: str
    action: str = "respond"          # respond | tool_call | error
    tool_name: str = ""
    tool_params: dict = field(default_factory=dict)
    memory_updated: bool = False
    flags: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Agent 可被攻击者篡改的配置"""
    safety_enabled: bool = True
    max_tool_calls: int = 10
    allowed_paths: list[str] = field(default_factory=lambda: ["/var/data/", "/tmp/"])
    blocked_keywords: list[str] = field(default_factory=lambda: ["hack", "malware"])


class MockAgent:
    """模拟 Agent — 基于规则的确定性行为"""

    def __init__(self, role: str = "assistant"):
        if role not in ROLE_DEFINITIONS:
            raise ValueError(f"Unknown role: {role}. Choose from: {list(ROLE_DEFINITIONS)}")
        self.role = role
        self.defn = ROLE_DEFINITIONS[role]
        self.config = AgentConfig()
        self._memory: dict[str, Any] = {}        # 模拟记忆存储
        self._tools_history: list[dict] = []      # 工具调用历史
        self._input_history: list[str] = []       # 输入历史

        # 模拟 RAG 知识库
        self._rag_store: dict[str, str] = {
            "deploy": "部署流程: 1) 运行测试 2) 构建镜像 3) 推送到仓库 4) 滚动更新",
            "security": "安全规范: 所有部署需经过审批，禁止跳过安全扫描",
            "config": "配置文件位于 /etc/app/config.yaml，修改后需重启服务",
        }

        # 各角色的行为模式
        self._behavior = self._build_behavior()

    def _build_behavior(self) -> dict:
        """构建角色对应的行为规则"""
        if self.role == "assistant":
            return {
                "trigger_keywords": {
                    "weather": ("respond", "Today's weather is sunny, 22C."),
                    "time": ("respond", f"Current time: {time.ctime()}."),
                    "remember": ("memory_write", None),
                    "recall": ("memory_read", None),
                    "calculate": ("tool_call", "calculator"),
                    "search": ("tool_call", "web_search"),
                    "delete": ("respond", "I don't have permission to delete files."),
                    "hack": ("respond", "I cannot help with that."),
                },
                "fallback": ("respond", "I can help with that. What else do you need?"),
            }
        elif self.role == "devops":
            return {
                "trigger_keywords": {
                    "deploy": ("tool_call", "execute_command",
                               {"cmd": "kubectl apply -f deployment.yaml"}),
                    "deploy --force": ("tool_call", "execute_command",
                                       {"cmd": "kubectl apply -f deployment.yaml --force"}),
                    "status": ("tool_call", "execute_command",
                               {"cmd": "kubectl get pods"}),
                    "write": ("tool_call", "write_file", None),
                    "config": ("tool_call", "read_file",
                               {"path": "/etc/app/config.yaml"}),
                    "db query": ("tool_call", "db_query", None),
                    "db write": ("tool_call", "db_write", None),
                    "restart": ("tool_call", "execute_command",
                                {"cmd": "systemctl restart app"}),
                    "clean": ("tool_call", "execute_command",
                              {"cmd": "rm -rf /tmp/cache/*"}),
                    "delete": ("tool_call", "delete_file", None),
                    "log": ("tool_call", "read_file",
                            {"path": "/var/log/app.log"}),
                    "execute": ("tool_call", "execute_command", None),
                },
                "fallback": ("respond", "Command executed. What's next?"),
            }
        elif self.role == "research":
            return {
                "trigger_keywords": {
                    "search": ("tool_call", "web_search", None),
                    "fetch": ("tool_call", "web_fetch", None),
                    "rag": ("tool_call", "search_content", None),
                    "paper": ("respond", "Based on my research, the key findings are..."),
                    "remember": ("memory_write", None),
                    "recall": ("memory_read", None),
                    "summary": ("respond", "Here's a summary of my findings..."),
                },
                "fallback": ("respond", "Let me look into that. What specific aspect "
                                       "interests you?"),
            }

    # ---- 公共 API ----

    def receive_input(self, user_input: str, source: str = "user_input") -> AgentResponse:
        """处理用户输入 — 拦截点 A"""
        self._input_history.append(user_input)

        # 匹配行为规则: (action_type, arg, params)
        #   respond: arg=content_string, params=None
        #   tool_call: arg=tool_name, params=dict or None
        #   memory_write/read: arg=unused, params=None
        action_type, arg, params = self._match_behavior(user_input)

        if action_type == "respond":
            content = arg if isinstance(arg, str) else self._get_fallback()
            return AgentResponse(
                success=True,
                content=content,
                action="respond",
            )
        elif action_type == "tool_call":
            return self.tool_call(arg, params or self._build_params(user_input, arg))
        elif action_type == "memory_write":
            return self.memory_write(user_input)
        elif action_type == "memory_read":
            return self.memory_read(user_input)
        else:
            return AgentResponse(success=True, content=self._get_fallback(), action="respond")

    def tool_call(self, tool_name: str, params: Optional[dict] = None) -> AgentResponse:
        """执行工具调用 — 拦截点 B"""

        # 检查工具是否在允许列表中
        if tool_name not in self.defn["allowed_tools"]:
            return AgentResponse(
                success=False,
                content=f"Tool '{tool_name}' not allowed for {self.role} agent.",
                action="error",
                tool_name=tool_name,
            )

        params = params or {}
        self._tools_history.append({
            "tool_name": tool_name,
            "params": params,
            "timestamp": time.time(),
        })

        # 模拟工具执行
        if tool_name == "execute_command":
            cmd = params.get("cmd", "")
            # 模拟危险命令检测
            if any(d in cmd for d in ["rm -rf /", "format", "dd if=", "shred"]):
                return AgentResponse(
                    success=False,
                    content=f"Dangerous command blocked by agent: {cmd}",
                    action="error",
                    tool_name=tool_name,
                    tool_params=params,
                )
            result = f"Command executed: {cmd}\nOutput: success (simulated)"
        elif tool_name == "write_file":
            path = params.get("path", "/tmp/default.txt")
            content = params.get("content", "")
            result = f"File written: {path} ({len(content)} bytes)"
        elif tool_name == "read_file":
            path = params.get("path", "")
            if "config" in path:
                result = self._read_config_simulated(path)
            else:
                result = f"File content of {path}: [simulated content]"
        elif tool_name == "db_write":
            result = f"DB write: {params.get('query', 'unknown')[:50]}... (simulated)"
        elif tool_name == "send_email":
            result = f"Email sent to {params.get('to', 'unknown')} (simulated)"
        elif tool_name == "web_search":
            query = params.get("query", "")
            result = f"Search results for '{query}': [simulated results]"
        elif tool_name == "web_fetch":
            url = params.get("url", "")
            result = f"Fetched content from {url}: [simulated HTML]"
        else:
            result = f"Tool '{tool_name}' executed (simulated)"

        return AgentResponse(
            success=True,
            content=result,
            action="tool_call",
            tool_name=tool_name,
            tool_params=params,
        )

    def memory_write(self, content: str) -> AgentResponse:
        """写入记忆 — 拦截点 C1"""
        entry_id = hashlib.md5(content.encode()).hexdigest()[:12]
        self._memory[entry_id] = {
            "content": content,
            "timestamp": time.time(),
            "source": "user_input",
        }
        return AgentResponse(
            success=True,
            content=f"Remembered: {content[:80]}",
            action="memory_write",
            memory_updated=True,
        )

    def memory_read(self, query: str) -> AgentResponse:
        """读取记忆 — 拦截点 C2"""
        results = []
        for eid, entry in self._memory.items():
            if any(word in entry["content"].lower() for word in query.lower().split()):
                results.append(entry["content"])

        if results:
            return AgentResponse(
                success=True,
                content=f"Recalled: {'; '.join(results[:3])}",
                action="memory_read",
            )
        return AgentResponse(
            success=True,
            content="No relevant memories found.",
            action="memory_read",
        )

    def produce_output(self, content: str) -> AgentResponse:
        """生成最终输出 — 拦截点 D"""
        # 模拟输出 PII 泄漏
        return AgentResponse(
            success=True,
            content=content,
            action="respond",
        )

    def load_config(self, source: str = "user_input") -> str:
        """模拟读取配置文件 — 可能被投毒"""
        if source in self._rag_store:
            return self._rag_store[source]
        return self._rag_store.get("config", "")

    def rag_retrieve(self, query: str) -> str:
        """模拟 RAG 检索"""
        for key, value in self._rag_store.items():
            if key in query.lower():
                return value
        return f"No relevant documents found for '{query}'."

    # ---- 内部方法 ----

    def _match_behavior(self, user_input: str) -> tuple[str, Optional[str], Optional[dict]]:
        """匹配用户输入到行为规则。返回 (action_type, tool_name_or_content, params)"""
        lower = user_input.lower()
        triggers = self._behavior.get("trigger_keywords", {})

        # 按关键词长度降序匹配（优先长匹配）
        for keyword in sorted(triggers, key=len, reverse=True):
            if keyword.lower() in lower:
                action = triggers[keyword]
                if isinstance(action, tuple):
                    # 兼容 2-tuple 和 3-tuple
                    if len(action) == 3:
                        return action
                    elif len(action) == 2:
                        return (action[0], action[1], None)
        return ("respond", None, self._get_fallback())

    def _build_params(self, user_input: str, tool_name: str) -> dict:
        """根据工具类型构建模拟参数"""
        if tool_name in ("web_search", "search_content"):
            return {"query": user_input}
        elif tool_name == "execute_command":
            # 从输入中提取命令
            return {"cmd": user_input.split(":", 1)[-1].strip() if ":" in user_input
                    else f"echo '{user_input[:40]}'"}
        elif tool_name == "write_file":
            return {"path": "/tmp/output.txt", "content": user_input}
        elif tool_name == "read_file":
            return {"path": "/var/log/app.log"}
        elif tool_name == "db_query":
            return {"query": f"SELECT * FROM data WHERE content LIKE '%{user_input[:20]}%'"}
        elif tool_name == "db_write":
            return {"query": f"INSERT INTO logs VALUES ('{user_input[:30]}')"}
        elif tool_name == "send_email":
            return {"to": "admin@example.com", "subject": "Agent notification",
                    "body": user_input}
        return {}

    def _read_config_simulated(self, path: str) -> str:
        """模拟配置文件内容"""
        return (
            "# App Configuration\n"
            "safety_enabled: true\n"
            "max_tool_calls: 10\n"
            'allowed_paths: ["/var/data/", "/tmp/"]\n'
            "# END OF CONFIG"
        )

    def _get_fallback(self) -> str:
        fb = self._behavior.get("fallback", "")
        if isinstance(fb, tuple):
            return fb[1] if len(fb) > 1 else str(fb)
        return str(fb) if fb else "I understand. What should I do next?"

    # ---- 查询 ----

    def get_state(self) -> dict:
        return {
            "role": self.role,
            "tool_history": len(self._tools_history),
            "memory_entries": len(self._memory),
            "input_count": len(self._input_history),
        }

    def get_memory_contents(self) -> list[str]:
        return [e["content"] for e in self._memory.values()]

    def reset(self):
        self._memory.clear()
        self._tools_history.clear()
        self._input_history.clear()
