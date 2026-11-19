"""KnowledgeGraphAgent — 记忆层 知识图谱"""
from __future__ import annotations

from acis.core.types import AgentOutput, RequestContext
from acis.knowledge.kg.adapter import query_kg
from acis.knowledge.rag.knowledge_base import get_optimal_conditions


class KnowledgeGraphAgent:
    name = "知识图谱"

    def run(self, context: RequestContext) -> AgentOutput:
        knowledge_graph = query_kg(context.crop, context.query)
        optimal = get_optimal_conditions(context.crop)
        backend = knowledge_graph.get("backend", "memory")
        error = knowledge_graph.get("error")
        diseases = knowledge_graph.get("diseases", [])
        degraded = backend == "fallback" or bool(error)
        claim = (
            f"知识图谱检索到 {len(diseases)} 个相关病害候选"
            if diseases
            else "知识图谱未检索到相关病害候选"
        )
        evidence = {
            "backend": backend,
            "knowledge_graph": knowledge_graph,
            "diseases": diseases,
            "triples": knowledge_graph.get("triples", []),
            "rules": knowledge_graph.get("rules", []),
            "hard_constraints": knowledge_graph.get("hard_constraints", []),
            "neo4j_connected": knowledge_graph.get("neo4j_connected", False),
            "optimal_conditions": optimal.get("optimal_conditions", {}),
            "error": error or optimal.get("error"),
        }
        warnings = []
        if error:
            warnings.append(f"知识图谱后端异常，实际使用 {backend}：{error}")
        if optimal.get("error"):
            warnings.append(optimal["error"])
        return AgentOutput(
            layer="记忆层",
            agent=self.name,
            claim=claim,
            confidence=0.7 if diseases else 0.4,
            evidence=evidence,
            warnings=warnings,
            execution={
                "status": "degraded" if degraded else "success",
                "mode": f"kg:{backend}",
                "backend": backend,
                "fallback_reason": error,
            },
        )
