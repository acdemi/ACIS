"""SensorAgent — 传感器感知层"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext
from rule_engine.sensor_anomaly import check_anomaly, get_current_reading

class SensorAgent:
    name = "传感器Agent"
    def run(self, context: RequestContext) -> AgentOutput:
        reading = get_current_reading(context.greenhouse_id)
        anomaly = check_anomaly(context.greenhouse_id)
        detection = anomaly.get("detection_result", {})
        is_anomalous = bool(detection.get("is_anomalous", False))
        score = float(detection.get("combined_score", 0.0))
        severity = detection.get("severity", "normal")
        claim = "传感器检测到异常" if is_anomalous else "传感器读数整体正常"
        warnings = []
        if is_anomalous:
            warnings.append(f"异常等级：{severity}，综合分数：{score}")
        return AgentOutput(layer="感知层", agent=self.name, claim=claim, confidence=0.75 if is_anomalous else 0.65, evidence={"reading": reading, "anomaly": anomaly}, warnings=warnings, recommendations=["对异常传感器复测，并查看最近 24 小时趋势"])
