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
        error = retrieval.get("error")
        retrieval_status = retrieval.get("retrieval_status") or (
            "failed" if error else "success" if matches else "no_results"
        )
        fallback_reason = retrieval.get("fallback_reason")
        degraded = retrieval_status in {"fallback", "failed"} or bool(error)
        execution = {
            "status": "failed" if retrieval_status == "failed" else "degraded" if degraded else "no_results" if not matches else "success",
            "mode": f"rag:{backend}",
            "backend": backend,
            "requested_backend": retrieval.get("requested_backend", backend),
            "fallback_reason": fallback_reason,
        }
        evidence = {
            "backend": backend,
            "requested_backend": retrieval.get("requested_backend", backend),
            "retrieval_status": retrieval_status,
            "match_status": "success" if matches else "no_results",
            "fallback_reason": fallback_reason,
            "matches": matches,
            "error": error,
            "sources": list(dict.fromkeys(hit.get("source", "unknown") for hit in matches)),
        }
        warnings = []
        if degraded:
            warnings.append(f"RAG 后端降级到 {backend}：{error or fallback_reason or 'backend_fallback'}")
        elif not matches:
            warnings.append("检索已完成，但没有找到相关知识；不把空结果当作检索故障")

        if not matches:
            return AgentOutput(
                layer="记忆层",
                agent=self.name,
                claim="RAG 未检索到相关知识" if not error else "RAG 检索失败或已降级，未取得相关知识",
                confidence=0.0 if error else 0.25,
                evidence=evidence,
                warnings=warnings,
                execution=execution,
            )
        top = matches[0]
        score = float(top.get("score", 0.0))
        confidence = min(0.9, max(0.35, 0.35 + min(score, 5.0) * 0.1))
        return AgentOutput(
            layer="记忆层",
            agent=self.name,
            claim=f"症状最匹配：{top['title']}",
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            recommendations=["围绕最高匹配病害核对关键症状"],
            execution=execution,
        )
