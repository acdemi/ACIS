"""MeteorologyExpertAgent - 专家层 气象分析（ACIS 2.0：内置反事实要求）"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from agents.weather import get_weather_alerts, get_weather_for_irrigation

# ACIS 2.0 反事实要求
COUNTERFACTUAL_REQUIREMENT = (
    "【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，"
    "并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。"
)


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
        reason = advice.get("reason")
        if reason: recommendations.append(reason)
        rt = advice.get("recommended_time")
        if rt: recommendations.append(f"建议作业时间：{rt}")
        if should_irrigate:
            counterfactual = {
                "alternative": "暂缓灌溉并择机补灌",
                "rejection_reason": "当前蒸发与土壤墒情支持灌溉，但若后续出现降雨或高湿预警，提前灌溉会叠加叶面湿度风险，故作为备选排除。",
            }
        else:
            counterfactual = {
                "alternative": "立即少量灌溉",
                "rejection_reason": "气象窗口暂不强制灌溉，贸然补水可能在近期降雨或低温时段造成沤根，故排除立即灌溉。",
            }
        return AgentOutput(layer="专家层", agent=self.name, claim=claim, confidence=0.72, evidence={"irrigation": irrigation, "alerts": alerts}, warnings=[a.get("description", str(a)) for a in active_alerts], recommendations=recommendations, counterfactual=counterfactual)
