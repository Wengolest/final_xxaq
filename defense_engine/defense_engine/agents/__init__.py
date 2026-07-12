# Agents package — LLM Agent 接入 defense_proxy
#
# 每个 Agent 都通过 PROXY_URL=http://localhost:8200/v1 接入防御引擎。
# defense_proxy 在输入侧执行 L1+L2，在输出侧执行 L2+L4+L5。
#
# Agent A: 纯对话 (OpenAI SDK)
# Agent B: 工具调用 (OpenAI SDK + function calling)
# Agent C: RAG (OpenAI SDK + 本地关键词检索)
# Agent D: Langroid RAG (Langroid OpenAIGPTConfig + ChromaDB)  — NEW
# Agent E: Autogen Tool (Autogen AssistantAgent + 3 tools)     — NEW

from .agent_a_chat import ChatAgent
from .agent_b_tool import ToolAgent
from .agent_c_rag import RAGAgent

# Agent D/E 需要 defense_venv (langroid/chromadb/autogen)
try:
    from .agent_langroid_rag import LangroidRAGAgent
except ImportError:
    LangroidRAGAgent = None  # type: ignore

try:
    from .agent_autogen_tool import AutogenToolAgent
except ImportError:
    AutogenToolAgent = None  # type: ignore

__all__ = [
    "ChatAgent",
    "ToolAgent",
    "RAGAgent",
    "LangroidRAGAgent",
    "AutogenToolAgent",
]
