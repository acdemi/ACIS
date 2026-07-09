"""MeteorologyExpertAgent — 专家层 气象分析"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from agents.weather import get_weather_alerts, get_weather_for_irrigation

class MeteorologyExpertAgent:
    name = "气象Agent"
    def run(self, context: RequestContext) -> AgentOutput:
        irrigation = get_weather_for_irrigation()
        alerts = get_weather_alerts()
        advice = irrigation.get("irrigation_advice", {})
        should_irrigate = bool(advice.get("should_irrigate", False))
        claim = "气象条件支持灌溉" if should_irrigate else "气象条件暂不强制灌溉"
        active_alerts = [a for a in alerts if a.get("type") != "无预警"]
        recommendations = []
        if advice.get("reason"): recommendations.append(advice["reason"])
        if advice.get("recommended_time"): recommendations.append(f"建议作业时间：{advice['recommended_time']}")
        return AgentOutput(layer="专家层", agent=self.name, claim=claim, confidence=0.72, evidence={"irrigation": irrigation, "alerts": alerts}, warnings=[a.get("description", str(a)) for a in active_alerts], recommendations=recommendations)
