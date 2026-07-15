"""PathologyAgent - 专家层 病理诊断（ACIS 2.0：内置反事实要求）"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.knowledge_base import diagnose_and_advise

# ACIS 2.0 反事实要求（等价于在专家 System Prompt 末尾追加的固定段落）：
# 【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，
# 并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。
COUNTERFACTUAL_REQUIREMENT = (
    "【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，"
    "并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。"
)


class PathologyAgent:
    name = "病理Agent"

    def run(self, context: RequestContext, sensor_output: AgentOutput) -> AgentOutput:
        readings = sensor_output.evidence.get("reading", {}).get("readings", {})
        current_conditions = {k: v for k, v in {"temperature": readings.get("air_temperature"), "humidity": readings.get("air_humidity"), "soil_moisture": readings.get("soil_moisture")}.items() if v is not None}
        diagnosis = diagnose_and_advise(context.crop, context.query, current_conditions)
        diseases = diagnosis.get("possible_diseases", [])
        if diseases:
            top = diseases[0]
            top_name = top["name"]
            claim = f"病理判断首选：{top_name}"
            confidence = min(0.9, 0.45 + top.get("match_score", 0) * 0.08)
        else:
            claim = "病理证据不足，不能确认具体病害"
            confidence = 0.3
        counterfactual = self._build_counterfactual(diseases)
        return AgentOutput(layer="专家层", agent=self.name, claim=claim, confidence=confidence, evidence=diagnosis, warnings=diagnosis.get("environment_issues", []), recommendations=diagnosis.get("recommended_actions", []), counterfactual=counterfactual)

    @staticmethod
    def _build_counterfactual(diseases: list[dict]) -> dict[str, str]:
        """给出最可能的替代诊断及排除理由（反事实推理）。"""
        if len(diseases) >= 2:
            top, alt = diseases[0], diseases[1]
            top_score = top.get("match_score", 0)
            alt_score = alt.get("match_score", 0)
            alt_name = alt["name"]
            alt_syms = "、".join(alt.get("matched_symptoms", [])) or "不详"
            reason = (
                f"匹配度{alt_score}低于首选{top_score}，"
                f"且{alt_name}的典型症状({alt_syms})"
                f"与现场描述重合度更低，故排除。"
            )
            return {"alternative": alt_name, "rejection_reason": reason}
        if diseases:
            return {
                "alternative": "生理性障碍或营养缺乏",
                "rejection_reason": "知识库中无其他匹配度相当的侵染性病害，但需排除缺素、药害等非侵染性因素。",
            }
        return {
            "alternative": "环境胁迫或生理性病害",
            "rejection_reason": "症状描述不足以匹配侵染性病害数据库，优先考虑温湿度逆境等生理性诱因。",
        }
