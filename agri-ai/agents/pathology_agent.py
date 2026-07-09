"""PathologyAgent — 专家层 病理诊断"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rag.knowledge_base import diagnose_and_advise

class PathologyAgent:
    name = "病理Agent"
    def run(self, context: RequestContext, sensor_output: AgentOutput) -> AgentOutput:
        readings = sensor_output.evidence.get("reading", {}).get("readings", {})
        current_conditions = {k: v for k, v in {"temperature": readings.get("air_temperature"), "humidity": readings.get("air_humidity"), "soil_moisture": readings.get("soil_moisture")}.items() if v is not None}
        diagnosis = diagnose_and_advise(context.crop, context.query, current_conditions)
        diseases = diagnosis.get("possible_diseases", [])
        if diseases:
            top = diseases[0]
            claim = f"病理判断首选：{top['name']}"
            confidence = min(0.9, 0.45 + top.get("match_score", 0) * 0.08)
        else:
            claim = "病理证据不足，不能确认具体病害"
            confidence = 0.3
        return AgentOutput(layer="专家层", agent=self.name, claim=claim, confidence=confidence, evidence=diagnosis, warnings=diagnosis.get("environment_issues", []), recommendations=diagnosis.get("recommended_actions", []))
