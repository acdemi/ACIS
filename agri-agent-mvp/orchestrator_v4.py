"""
农业 Agent MVP v4 — 分层协作编排实验

架构：
- 用户层：CLI / Web / App / 微信小程序入口可统一调用 Orchestrator
- Agent Orchestrator：中央调度、上下文抽取、工作流编排
- 感知层：视觉 Agent、传感器 Agent、天气 Agent
- 专家层：病理 Agent、气象 Agent、栽培 Agent
- 记忆层：RAG、知识图谱、历史案例库
- Debate & Judge：多专家交叉质询与最终裁决
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Any

from knowledge_mcp_server import (
    diagnose_and_advise,
    get_farming_guide,
    get_optimal_conditions,
    search_disease,
)
from sensor_mcp_server_v2 import check_anomaly, get_current_reading
from weather_mcp_server import (
    get_current_weather,
    get_weather_alerts,
    get_weather_for_irrigation,
)


@dataclass
class RequestContext:
    query: str
    greenhouse_id: str
    crop: str
    image_path: str | None = None
    intent: str = "diagnose"


@dataclass
class AgentOutput:
    layer: str
    agent: str
    claim: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DebateResult:
    consensus: list[str]
    conflicts: list[str]
    missing_evidence: list[str]
    risk_level: str


@dataclass
class DecisionOutput:
    summary: str
    decision: str
    confidence: float
    risk_level: str
    action_plan: list[str]
    debate: DebateResult
    traces: list[AgentOutput]


def _extract_greenhouse_id(query: str) -> str:
    if any(keyword in query for keyword in ["温室B", "温室b", "黄瓜", "gh-b", "greenhouse_b"]):
        return "gh-b"
    return "gh-a"


def _extract_crop(query: str) -> str:
    if "黄瓜" in query:
        return "cucumber"
    if "番茄" in query:
        return "tomato"
    return "tomato"


def _extract_intent(query: str) -> str:
    if any(keyword in query for keyword in ["浇水", "灌溉", "滴灌", "水肥"]):
        return "irrigate"
    if any(keyword in query for keyword in ["预警", "报警", "风险", "注意"]):
        return "alert"
    if any(keyword in query for keyword in ["状态", "监测", "数据", "当前"]):
        return "monitor"
    if any(keyword in query for keyword in ["病", "斑", "霉", "虫", "枯", "异常", "诊断"]):
        return "diagnose"
    return "consult"


def build_context(query: str, image_path: str | None = None) -> RequestContext:
    return RequestContext(
        query=query,
        greenhouse_id=_extract_greenhouse_id(query),
        crop=_extract_crop(query),
        image_path=image_path,
        intent=_extract_intent(query),
    )


class VisionAgent:
    name = "视觉Agent"

    def run(self, context: RequestContext) -> AgentOutput:
        if not context.image_path:
            return AgentOutput(
                layer="感知层",
                agent=self.name,
                claim="未提供图像，视觉诊断跳过",
                confidence=0.0,
                warnings=["缺少叶片图像，病害判断依赖症状与环境数据"],
            )

        if not os.path.exists(context.image_path):
            return AgentOutput(
                layer="感知层",
                agent=self.name,
                claim="图像路径不存在，无法执行视觉识别",
                confidence=0.0,
                evidence={"image_path": context.image_path},
                warnings=["请提供有效的叶片图片路径"],
            )

        try:
            from vision_mcp_server import diagnose_image

            result = diagnose_image(context.image_path)
        except Exception as exc:
            return AgentOutput(
                layer="感知层",
                agent=self.name,
                claim="视觉模型调用失败",
                confidence=0.0,
                evidence={"error": str(exc)},
                warnings=["视觉通道不可用，需要依赖其他 Agent 交叉判断"],
            )

        if "error" in result:
            return AgentOutput(
                layer="感知层",
                agent=self.name,
                claim="视觉识别未给出有效结论",
                confidence=0.1,
                evidence=result,
                warnings=[result["error"]],
            )

        top = result.get("top_prediction", {})
        disease = top.get("chinese_name") or top.get("label") or "未知类别"
        confidence = float(top.get("confidence", 0.0))
        return AgentOutput(
            layer="感知层",
            agent=self.name,
            claim=f"图像最可能识别为：{disease}",
            confidence=confidence,
            evidence=result,
            recommendations=["将视觉结果与传感器湿度、知识库症状匹配结果交叉验证"],
        )


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

        return AgentOutput(
            layer="感知层",
            agent=self.name,
            claim=claim,
            confidence=0.75 if is_anomalous else 0.65,
            evidence={"reading": reading, "anomaly": anomaly},
            warnings=warnings,
            recommendations=["对异常传感器复测，并查看最近 24 小时趋势"],
        )


class WeatherAgent:
    name = "天气Agent"

    def run(self, context: RequestContext) -> AgentOutput:
        current = get_current_weather()
        alerts = get_weather_alerts()
        active_alerts = [item for item in alerts if item.get("type") != "无预警"]
        claim = "存在外部天气预警" if active_alerts else "外部天气暂无明显预警"
        warnings = [item.get("description", str(item)) for item in active_alerts]

        return AgentOutput(
            layer="感知层",
            agent=self.name,
            claim=claim,
            confidence=0.7,
            evidence={"current_weather": current, "alerts": alerts},
            warnings=warnings,
        )


class RagMemoryAgent:
    name = "RAG"

    def run(self, context: RequestContext) -> AgentOutput:
        diseases = search_disease(context.query, context.crop)
        if not diseases:
            return AgentOutput(
                layer="记忆层",
                agent=self.name,
                claim="RAG 未检索到高匹配病害",
                confidence=0.25,
                evidence={"matches": []},
                warnings=["症状描述不足或知识库覆盖不足"],
            )

        top = diseases[0]
        confidence = min(0.9, 0.35 + top.get("match_score", 0) * 0.1)
        return AgentOutput(
            layer="记忆层",
            agent=self.name,
            claim=f"症状最匹配：{top['name']}",
            confidence=confidence,
            evidence={"matches": diseases},
            recommendations=["围绕最高匹配病害核对关键症状"],
        )


class KnowledgeGraphAgent:
    name = "知识图谱"

    def run(self, context: RequestContext) -> AgentOutput:
        optimal = get_optimal_conditions(context.crop)
        return AgentOutput(
            layer="记忆层",
            agent=self.name,
            claim="已提取作物最佳环境约束",
            confidence=0.7 if "error" not in optimal else 0.2,
            evidence=optimal,
            warnings=[optimal["error"]] if "error" in optimal else [],
        )


class CaseMemoryAgent:
    name = "历史案例库"

    def run(self, context: RequestContext) -> AgentOutput:
        if context.crop == "tomato" and any(keyword in context.query for keyword in ["黄斑", "霉层", "背面"]):
            return AgentOutput(
                layer="记忆层",
                agent=self.name,
                claim="历史案例中高湿环境下番茄叶霉病相似度较高",
                confidence=0.68,
                evidence={
                    "case_id": "case-tomato-leaf-mold-001",
                    "pattern": "番茄 + 黄斑 + 叶背霉层 + 高湿风险",
                },
                recommendations=["优先排查通风不足、叶面结露和下部老叶发病"],
            )

        if context.crop == "cucumber" and any(keyword in context.query for keyword in ["霉层", "多角", "结露"]):
            return AgentOutput(
                layer="记忆层",
                agent=self.name,
                claim="历史案例中黄瓜霜霉病相似度较高",
                confidence=0.65,
                evidence={
                    "case_id": "case-cucumber-downy-mildew-001",
                    "pattern": "黄瓜 + 多角黄斑 + 叶背霉层 + 结露",
                },
                recommendations=["重点检查清晨叶面结露和棚内湿度"],
            )

        return AgentOutput(
            layer="记忆层",
            agent=self.name,
            claim="历史案例库暂无强匹配案例",
            confidence=0.3,
            evidence={"matched_case": None},
        )


class PathologyAgent:
    name = "病理Agent"

    def run(self, context: RequestContext, sensor_output: AgentOutput) -> AgentOutput:
        readings = sensor_output.evidence.get("reading", {}).get("readings", {})
        current_conditions = {
            "temperature": readings.get("air_temperature"),
            "humidity": readings.get("air_humidity"),
            "soil_moisture": readings.get("soil_moisture"),
        }
        current_conditions = {key: value for key, value in current_conditions.items() if value is not None}
        diagnosis = diagnose_and_advise(context.crop, context.query, current_conditions)
        diseases = diagnosis.get("possible_diseases", [])

        if diseases:
            top = diseases[0]
            claim = f"病理判断首选：{top['name']}"
            confidence = min(0.9, 0.45 + top.get("match_score", 0) * 0.08)
        else:
            claim = "病理证据不足，不能确认具体病害"
            confidence = 0.3

        return AgentOutput(
            layer="专家层",
            agent=self.name,
            claim=claim,
            confidence=confidence,
            evidence=diagnosis,
            warnings=diagnosis.get("environment_issues", []),
            recommendations=diagnosis.get("recommended_actions", []),
        )


class MeteorologyExpertAgent:
    name = "气象Agent"

    def run(self, context: RequestContext) -> AgentOutput:
        irrigation = get_weather_for_irrigation()
        alerts = get_weather_alerts()
        advice = irrigation.get("irrigation_advice", {})
        should_irrigate = bool(advice.get("should_irrigate", False))
        claim = "气象条件支持灌溉" if should_irrigate else "气象条件暂不强制灌溉"
        active_alerts = [item for item in alerts if item.get("type") != "无预警"]

        recommendations = []
        if advice.get("reason"):
            recommendations.append(advice["reason"])
        if advice.get("recommended_time"):
            recommendations.append(f"建议作业时间：{advice['recommended_time']}")

        return AgentOutput(
            layer="专家层",
            agent=self.name,
            claim=claim,
            confidence=0.72,
            evidence={"irrigation": irrigation, "alerts": alerts},
            warnings=[item.get("description", str(item)) for item in active_alerts],
            recommendations=recommendations,
        )


class CultivationAgent:
    name = "栽培Agent"

    def run(self, context: RequestContext, sensor_output: AgentOutput) -> AgentOutput:
        guide = get_farming_guide(context.crop)
        readings = sensor_output.evidence.get("reading", {}).get("readings", {})
        recommendations = []
        warnings = []

        humidity = readings.get("air_humidity")
        temperature = readings.get("air_temperature")
        soil_moisture = readings.get("soil_moisture")

        if humidity is not None and humidity > 80:
            warnings.append(f"棚内湿度偏高：{humidity}%")
            recommendations.append("加强通风排湿，避免叶面长时间结露")
        if temperature is not None and temperature > 30:
            warnings.append(f"棚内温度偏高：{temperature}°C")
            recommendations.append("中午加强遮阳或雾化降温")
        if soil_moisture is not None and soil_moisture < 35:
            warnings.append(f"土壤含水量偏低：{soil_moisture}%")
            recommendations.append("安排小水勤灌，避免一次性大水漫灌")

        if not recommendations:
            recommendations.append("维持当前管理，继续监测温湿度和叶面状态")

        return AgentOutput(
            layer="专家层",
            agent=self.name,
            claim="已生成栽培管理建议",
            confidence=0.68 if "error" not in guide else 0.35,
            evidence={"guide": guide, "current_readings": readings},
            warnings=warnings,
            recommendations=recommendations,
        )


class DebateEngine:
    def run(self, outputs: list[AgentOutput]) -> DebateResult:
        consensus = []
        conflicts = []
        missing_evidence = []

        claims = "\n".join(output.claim for output in outputs)
        if "叶霉病" in claims and any("湿度" in warning for output in outputs for warning in output.warnings):
            consensus.append("病害症状与高湿风险互相支持，真菌性病害优先级升高")
        if "支持灌溉" in claims and any("湿度偏高" in warning for output in outputs for warning in output.warnings):
            conflicts.append("气象建议灌溉，但棚内湿度偏高，需避免加重病害风险")
        if any(output.agent == "视觉Agent" and output.confidence == 0 for output in outputs):
            missing_evidence.append("缺少有效图像证据，视觉 Agent 未参与确认")
        if not consensus:
            consensus.append("各 Agent 暂无强冲突，建议按风险优先级执行")

        max_warning_count = max((len(output.warnings) for output in outputs), default=0)
        max_confidence_warning = any(output.confidence >= 0.65 and output.warnings for output in outputs)
        if conflicts or max_warning_count >= 2:
            risk_level = "high"
        elif max_confidence_warning:
            risk_level = "medium"
        else:
            risk_level = "low"

        return DebateResult(
            consensus=consensus,
            conflicts=conflicts,
            missing_evidence=missing_evidence,
            risk_level=risk_level,
        )


class JudgeAgent:
    def run(self, context: RequestContext, outputs: list[AgentOutput], debate: DebateResult) -> DecisionOutput:
        expert_outputs = [output for output in outputs if output.layer == "专家层"]
        weighted_total = sum(output.confidence for output in expert_outputs) or 1.0
        confidence = sum(output.confidence * output.confidence for output in expert_outputs) / weighted_total
        confidence = round(min(0.92, max(0.25, confidence)), 2)

        pathology = next((output for output in outputs if output.agent == "病理Agent"), None)
        meteorology = next((output for output in outputs if output.agent == "气象Agent"), None)
        cultivation = next((output for output in outputs if output.agent == "栽培Agent"), None)

        if context.intent == "irrigate" and meteorology:
            decision = meteorology.claim
        elif pathology and "病理证据不足" not in pathology.claim:
            decision = pathology.claim
        elif cultivation:
            decision = cultivation.claim
        else:
            decision = "继续采集证据后再决策"

        action_plan = []
        for output in outputs:
            for recommendation in output.recommendations:
                if recommendation not in action_plan:
                    action_plan.append(recommendation)
        if debate.missing_evidence:
            action_plan.append("补充叶片近景图像，提升视觉和病理交叉验证置信度")
        if debate.conflicts:
            action_plan.append("存在策略冲突时，以病害风险控制优先，再安排水肥作业")

        summary = (
            f"Orchestrator 已完成 {context.greenhouse_id}/{context.crop} 的"
            f"{context.intent} 工作流：{decision}。风险等级：{debate.risk_level}。"
        )

        return DecisionOutput(
            summary=summary,
            decision=decision,
            confidence=confidence,
            risk_level=debate.risk_level,
            action_plan=action_plan[:6],
            debate=debate,
            traces=outputs,
        )


class AgentOrchestrator:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.sensor_agent = SensorAgent()
        self.weather_agent = WeatherAgent()
        self.rag_agent = RagMemoryAgent()
        self.knowledge_graph_agent = KnowledgeGraphAgent()
        self.case_memory_agent = CaseMemoryAgent()
        self.pathology_agent = PathologyAgent()
        self.meteorology_agent = MeteorologyExpertAgent()
        self.cultivation_agent = CultivationAgent()
        self.debate_engine = DebateEngine()
        self.judge_agent = JudgeAgent()

    def run(self, query: str, image_path: str | None = None) -> DecisionOutput:
        context = build_context(query, image_path)

        perception_outputs = [
            self.vision_agent.run(context),
            self.sensor_agent.run(context),
            self.weather_agent.run(context),
        ]
        sensor_output = next(output for output in perception_outputs if output.agent == "传感器Agent")

        memory_outputs = [
            self.rag_agent.run(context),
            self.knowledge_graph_agent.run(context),
            self.case_memory_agent.run(context),
        ]

        expert_outputs = [
            self.pathology_agent.run(context, sensor_output),
            self.meteorology_agent.run(context),
            self.cultivation_agent.run(context, sensor_output),
        ]

        outputs = perception_outputs + memory_outputs + expert_outputs
        debate = self.debate_engine.run(outputs)
        return self.judge_agent.run(context, outputs, debate)


def format_decision(decision: DecisionOutput) -> str:
    lines = [
        "=" * 60,
        "农业 Agent v4 — Orchestrator / Debate / Judge",
        "=" * 60,
        f"\n【总结】{decision.summary}",
        f"【裁决】{decision.decision}",
        f"【置信度】{decision.confidence:.0%}",
        f"【风险等级】{decision.risk_level}",
        "\n【Debate 共识】",
    ]
    lines.extend(f"- {item}" for item in decision.debate.consensus)

    if decision.debate.conflicts:
        lines.append("\n【Debate 冲突】")
        lines.extend(f"- {item}" for item in decision.debate.conflicts)

    if decision.debate.missing_evidence:
        lines.append("\n【缺失证据】")
        lines.extend(f"- {item}" for item in decision.debate.missing_evidence)

    lines.append("\n【行动建议】")
    lines.extend(f"{index}. {item}" for index, item in enumerate(decision.action_plan, start=1))

    lines.append("\n【Agent Trace】")
    for output in decision.traces:
        lines.append(f"- [{output.layer}] {output.agent}: {output.claim} ({output.confidence:.0%})")
        for warning in output.warnings[:2]:
            lines.append(f"  ⚠ {warning}")

    return "\n".join(lines)


def run_demo() -> None:
    orchestrator = AgentOrchestrator()
    scenarios = [
        "温室A的番茄叶片出现黄斑，叶片背面有灰色霉层，帮我诊断并给出处理建议",
        "温室A番茄今天需要浇水吗？如果有病害风险要一起考虑",
    ]
    for scenario in scenarios:
        print(format_decision(orchestrator.run(scenario)))
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="农业 Agent v4 分层协作编排实验")
    parser.add_argument("query", nargs="*", help="用户问题")
    parser.add_argument("--image", dest="image_path", help="叶片图片路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 调试信息")
    args = parser.parse_args()

    orchestrator = AgentOrchestrator()
    query = " ".join(args.query).strip()
    if not query:
        run_demo()
        return

    decision = orchestrator.run(query, args.image_path)
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, default=lambda value: value.__dict__, indent=2))
    else:
        print(format_decision(decision))


if __name__ == "__main__":
    main()
