"""KnowledgeGraphAgent — 记忆层 知识图谱"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.knowledge_base import get_optimal_conditions

class KnowledgeGraphAgent:
    name = "知识图谱"
    def run(self, context: RequestContext) -> AgentOutput:
        optimal = get_optimal_conditions(context.crop)
        return AgentOutput(layer="记忆层", agent=self.name, claim="已提取作物最佳环境约束", confidence=0.7 if "error" not in optimal else 0.2, evidence=optimal, warnings=[optimal["error"]] if "error" in optimal else [])
