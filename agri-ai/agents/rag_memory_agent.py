"""RagMemoryAgent — 记忆层 RAG 检索"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.retriever import retrieve_with_backend

class RagMemoryAgent:
    name = "RAG"
    def run(self, context: RequestContext) -> AgentOutput:
        retrieval = retrieve_with_backend(context.query, context.crop)
        matches = retrieval.get("matches", [])
        backend = retrieval.get("backend", "memory")
        if not matches:
            return AgentOutput(layer="记忆层", agent=self.name, claim="RAG 未检索到高匹配病害", confidence=0.25, evidence={"backend": backend, "matches": [], "error": retrieval.get("error")}, warnings=["症状描述不足或知识库覆盖不足"])
        top = matches[0]
        score = float(top.get("score", 0.0))
        confidence = min(0.9, max(0.35, 0.35 + min(score, 5.0) * 0.1))
        return AgentOutput(layer="记忆层", agent=self.name, claim=f"症状最匹配：{top['title']}", confidence=confidence, evidence={"backend": backend, "matches": matches, "error": retrieval.get("error")}, recommendations=["围绕最高匹配病害核对关键症状"])
