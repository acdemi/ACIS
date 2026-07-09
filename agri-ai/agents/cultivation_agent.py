"""CultivationAgent — 专家层 栽培管理"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.knowledge_base import get_farming_guide

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
        return AgentOutput(layer="专家层", agent=self.name, claim="已生成栽培管理建议", confidence=0.68 if "error" not in guide else 0.35, evidence={"guide": guide, "current_readings": readings}, warnings=warnings, recommendations=recommendations)
