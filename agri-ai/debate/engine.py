"""DebateEngine — 冲突检测与共识生成"""
from __future__ import annotations
from typing import Any
from agents.types import AgentOutput, RequestContext, DebateResult

class DebateEngine:
    DISEASE_CLAIM_PREFIX = "病理判断首选："
    DISEASE_INSUFFICIENT = "病理证据不足"
    HIGH_HUMIDITY_DISEASES = ("叶霉病", "霜霉病", "褐斑病", "黑斑病", "叶斑病")

    @staticmethod
    def _sensor_humidity(outputs: list[AgentOutput]) -> float | None:
        sensor = next((o for o in outputs if o.agent == "传感器Agent"), None)
        if sensor is None: return None
        v = sensor.evidence.get("reading", {}).get("readings", {}).get("air_humidity")
        try: return float(v) if v is not None else None
        except: return None

    def run(self, outputs: list[AgentOutput], context: RequestContext | None = None) -> DebateResult:
        consensus, conflicts, missing_evidence = [], [], []
        pathology = next((o for o in outputs if o.agent == "病理Agent"), None)
        meteorology = next((o for o in outputs if o.agent == "气象Agent"), None)
        disease_claimed = bool(pathology and self.DISEASE_CLAIM_PREFIX in pathology.claim and self.DISEASE_INSUFFICIENT not in pathology.claim)
        intent = getattr(context, "intent", "") if context else ""
        irrigation_advised = bool(meteorology and "支持灌溉" in meteorology.claim)
        high_hum = any("湿度偏高" in w for o in outputs for w in o.warnings)

        if disease_claimed and any("湿度" in w for o in outputs for w in o.warnings):
            consensus.append("病害症状与高湿风险互相支持，真菌性病害优先级升高")
        if disease_claimed and any("最匹配" in o.claim or "历史案例" in o.claim for o in outputs):
            consensus.append("病理诊断与记忆层（RAG/历史案例）结论一致，诊断可信度升高")
        if irrigation_advised and high_hum:
            conflicts.append("气象建议灌溉，但棚内湿度偏高，需避免加重病害风险")
        if irrigation_advised and disease_claimed and intent == "irrigate":
            conflicts.append("已诊断真菌性病害，此时灌溉可能加重叶面湿度与病情，建议先控病后灌溉")
        if disease_claimed:
            disease_name = pathology.claim.replace(self.DISEASE_CLAIM_PREFIX, "").strip()
            humidity = self._sensor_humidity(outputs)
            if any(k in disease_name for k in self.HIGH_HUMIDITY_DISEASES) and humidity is not None and humidity < 55:
                conflicts.append(f"诊断{disease_name}为高湿型病害，但当前空气湿度{humidity}%偏低，环境不支持该病害高发")
        sensor_anomalous = any(o.agent == "传感器Agent" and "异常" in o.claim for o in outputs)
        pathology_insufficient = bool(pathology and self.DISEASE_INSUFFICIENT in pathology.claim)
        if sensor_anomalous and pathology_insufficient:
            conflicts.append("传感器检测到环境异常，但病理Agent未能确认病害，需补充图像与现场复核")
        if any(o.agent == "视觉Agent" and o.confidence == 0 for o in outputs):
            missing_evidence.append("缺少有效图像证据，视觉 Agent 未参与确认")
        if not consensus:
            consensus.append("各 Agent 暂无强冲突，建议按风险优先级执行")

        max_wc = max((len(o.warnings) for o in outputs), default=0)
        max_cw = any(o.confidence >= 0.65 and o.warnings for o in outputs)
        if conflicts or max_wc >= 2: risk_level = "high"
        elif max_cw: risk_level = "medium"
        else: risk_level = "low"

        return DebateResult(consensus=consensus, conflicts=conflicts, missing_evidence=missing_evidence, risk_level=risk_level)
