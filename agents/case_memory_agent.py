"""CaseMemoryAgent - 记忆层 历史案例库

优先召回 SQLite 中人工复核确认（feedback='correct'）的历史决策，
无确认案例时回退到内置模式匹配。
"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext


class CaseMemoryAgent:
    name = "历史案例库"

    def run(self, context: RequestContext) -> AgentOutput:
        confirmed = self._recall_confirmed(context)
        if confirmed:
            top = confirmed[0]
            return AgentOutput(
                layer="记忆层", agent=self.name,
                claim=f"历史确认案例匹配：{top['decision']}（人工复核确认）",
                confidence=0.75,
                evidence={
                    "case_id": f"confirmed-{top['id']}",
                    "source": "sqlite_confirmed",
                    "original_query": top.get("query", ""),
                    "original_confidence": top.get("confidence"),
                    "feedback_note": top.get("feedback_note"),
                },
                recommendations=[f"参考已确认案例 #{top['id']} 的处置经验，核对关键症状"],
            )
        if context.crop == "tomato" and any(k in context.query for k in ["黄斑", "霉层", "背面"]):
            return AgentOutput(layer="记忆层", agent=self.name, claim="历史案例中高湿环境下番茄叶霉病相似度较高", confidence=0.68, evidence={"case_id": "case-tomato-leaf-mold-001", "pattern": "番茄 + 黄斑 + 叶背霉层 + 高湿风险"}, recommendations=["优先排查通风不足、叶面结露和下部老叶发病"])
        if context.crop == "cucumber" and any(k in context.query for k in ["霉层", "多角", "结露"]):
            return AgentOutput(layer="记忆层", agent=self.name, claim="历史案例中黄瓜霜霉病相似度较高", confidence=0.65, evidence={"case_id": "case-cucumber-downy-mildew-001", "pattern": "黄瓜 + 多角黄斑 + 叶背霉层 + 结露"}, recommendations=["重点检查清晨叶面结露和棚内湿度"])
        return AgentOutput(layer="记忆层", agent=self.name, claim="历史案例库暂无强匹配案例", confidence=0.3, evidence={"matched_case": None})

    def _recall_confirmed(self, context: RequestContext) -> list:
        """召回同作物的人工确认案例，按查询字符重叠度排序。"""
        try:
            from storage.repository import search_confirmed_cases
            cases = search_confirmed_cases(context.crop, context.query)
        except Exception:
            return []
        qchars = set(context.query)
        scored = []
        for c in cases:
            overlap = len(set(c.get("query", "")) & qchars)
            if overlap >= 2:
                scored.append((overlap, c))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:3]]

