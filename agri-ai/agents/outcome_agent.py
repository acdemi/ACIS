"""OutcomeAgent - 记忆层 经验回放（ACIS 2.0）

查询历史高相似度案例中 outcome 为"有效"的案例，提取其行动建议，作为新的证据传递
给 Judge。与 RAG、KG 并列于记忆层节点。无有效案例时返回低置信度空结果，不干扰主流程。
"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from storage.repository import search_outcome_cases


class OutcomeAgent:
    name = "经验回放Agent"

    def run(self, context: RequestContext) -> AgentOutput:
        try:
            cases = search_outcome_cases(context.crop, context.query, limit=3)
        except Exception:
            cases = []
        if not cases:
            return AgentOutput(
                layer="记忆层", agent=self.name,
                claim="无历史有效结果案例可回放",
                confidence=0.3,
                evidence={"cases": [], "backend": "sqlite"},
                warnings=[], recommendations=[],
            )
        actions: list[str] = []
        decisions: list[str] = []
        for c in cases:
            if c.get("decision") and c["decision"] not in decisions:
                decisions.append(c["decision"])
            for a in (c.get("action_plan") or []):
                if a not in actions:
                    actions.append(a)
        return AgentOutput(
            layer="记忆层", agent=self.name,
            claim=f"回放{len(cases)}条历史有效案例，提取{len(actions)}条行动建议",
            confidence=0.6,
            evidence={"cases": cases, "backend": "sqlite", "historical_decisions": decisions},
            warnings=[],
            recommendations=actions[:3],
        )
