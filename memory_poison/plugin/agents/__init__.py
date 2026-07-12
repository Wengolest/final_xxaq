# -*- coding: utf-8 -*-
"""五种完整部署的 MEMORY Agent 注册表。"""

from pathlib import Path

from plugin.agents.ci_pipeline_agent import CIPipelineAgent
from plugin.agents.code_review_agent import CodeReviewAgent
from plugin.agents.customer_support_agent import CustomerSupportAgent
from plugin.agents.data_interpreter_agent import DataInterpreterAgent
from plugin.agents.rag_analyst_agent import RAGAnalystAgent
from plugin.llm_client import DeepSeekClient

AGENT_CLASSES = [
    DataInterpreterAgent,
    RAGAnalystAgent,
    CIPipelineAgent,
    CustomerSupportAgent,
    CodeReviewAgent,
]


def create_all_agents(db_dir: Path, llm: DeepSeekClient | None = None) -> dict:
    """实例化全部 Agent 并初始化良性记忆。"""
    agents = {}
    for cls in AGENT_CLASSES:
        agent = cls(db_dir=db_dir, llm=llm)
        agent.reset()
        agents[agent.agent_id] = agent
    return agents
