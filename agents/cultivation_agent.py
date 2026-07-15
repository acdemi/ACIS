"""CultivationAgent - 专家层 栽培管理（ACIS 2.0：内置反事实要求）"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.knowledge_base import get_farming_guide

# ACIS 2.0 反事实要求
COUNTERFACTUAL_REQUIREMENT = (
    "【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，"
    "并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。"
)


class CultivationAgent:
    name = "栽培Agent"

    def run(self, context: RequestContext, sensor_output: AgentOutput) -> AgentOutput:
        guide = get_farming_guide(context.crop)
        readings = sensor_output.evidence.get("reading", {}).get("readings", {})
        recommendations, warnings = [], []
        h, t, sm = readings.get("air_humidity"), readings.get("air_temperature"), readings.get("soil_moisture")
        if h is not None and h > 80:
            warnings.append(f"棚内湿度偏高：{h}%"); recommendations.append("加强通风排湿，避免叶面长时间结露")
        if t is not None and t > 30:
            warnings.append(f"棚内温度偏高：{t}℃"); recommendations.append("中午加强遮阳或雾化降温")
        if sm is not None and sm < 35:
            warnings.append(f"土壤含水量偏低：{sm}%"); recommendations.append("安排小水勤灌，避免一次性大水漫灌")
        if not recommendations:
            recommendations.append("维持当前管理，继续监测温湿度和叶面状态")
        counterfactual = {
            "alternative": "直接采用化学药剂防治",
            "rejection_reason": "综合防治(IPM)原则下优先环境调控与栽培措施，化学防治作为后备手段，可避免抗药性上升与生态副作用。",
        }
        return AgentOutput(layer="专家层", agent=self.name, claim="已生成栽培管理建议", confidence=0.68 if "error" not in guide else 0.35, evidence={"guide": guide, "current_readings": readings}, warnings=warnings, recommendations=recommendations, counterfactual=counterfactual)
