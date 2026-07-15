"""WeatherAgent — 天气感知层"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from agents.weather import get_current_weather, get_weather_alerts, get_weather_for_irrigation

class WeatherAgent:
    name = "天气Agent"
    def run(self, context: RequestContext) -> AgentOutput:
        current = get_current_weather()
        alerts = get_weather_alerts()
        active_alerts = [a for a in alerts if a.get("type") != "无预警"]
        claim = "存在外部天气预警" if active_alerts else "外部天气暂无明显预警"
        warnings = [a.get("description", str(a)) for a in active_alerts]
        return AgentOutput(layer="感知层", agent=self.name, claim=claim, confidence=0.7, evidence={"current_weather": current, "alerts": alerts}, warnings=warnings)
