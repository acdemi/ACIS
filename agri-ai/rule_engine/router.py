"""
Agent Router — 核心调度引擎
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Intent(Enum):
    DIAGNOSE = "diagnose"
    MONITOR = "monitor"
    PREDICT = "predict"
    IRRIGATE = "irrigate"
    ALERT = "alert"
    GUIDE = "guide"
    UNKNOWN = "unknown"


@dataclass
class ToolCall:
    server: str
    tool: str
    args: dict
    result: Any = None
    error: str = None


@dataclass
class AgentTrace:
    intent: Intent
    reasoning: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    synthesis: str = ""
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _format_sensor_value(data: dict) -> str:
    """格式化传感器值，正确处理布尔类型"""
    val = data["value"]
    unit = data.get("unit", "")
    if unit == "boolean":
        return "是" if val else "否"
    return f"{val}{unit}"


class AgentRouter:

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._intent_keywords = {
            Intent.DIAGNOSE: ["病", "虫", "黄", "枯", "烂", "斑", "霉", "诊断", "怎么了", "什么原因", "异常"],
            Intent.MONITOR: ["温度", "湿度", "状态", "现在", "当前", "查看", "监测", "数据"],
            Intent.PREDICT: ["预测", "趋势", "未来", "明天", "下周", "会怎样"],
            Intent.IRRIGATE: ["灌溉", "浇水", "浇地", "水肥", "滴灌"],
            Intent.ALERT: ["预警", "报警", "警告", "注意", "风险"],
            Intent.GUIDE: ["指南", "怎么种", "管理", "施肥", "种植", "建议"],
        }

    def register_tool(self, server: str, tool_name: str, func: Callable):
        key = f"{server}.{tool_name}"
        self._tools[key] = func

    def _classify_intent(self, query: str) -> tuple[Intent, float]:
        scores = {}
        for intent, keywords in self._intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query)
            if score > 0:
                scores[intent] = score
        if not scores:
            return Intent.UNKNOWN, 0.0
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        return best, scores[best] / max(total, 1)

    def _extract_greenhouse_id(self, query: str) -> str:
        if any(kw in query for kw in ["番茄", "温室A", "温室a", "gh-a"]):
            return "gh-a"
        if any(kw in query for kw in ["黄瓜", "温室B", "温室b", "gh-b"]):
            return "gh-b"
        return "gh-a"

    def _extract_crop(self, query: str) -> str:
        if "番茄" in query:
            return "tomato"
        if "黄瓜" in query:
            return "cucumber"
        return "tomato"

    async def _call_tool(self, server: str, tool_name: str, args: dict) -> ToolCall:
        call = ToolCall(server=server, tool=tool_name, args=args)
        key = f"{server}.{tool_name}"
        try:
            func = self._tools.get(key)
            if not func:
                call.error = f"工具 {key} 未注册"
                return call
            call.result = func(**args)
        except Exception as e:
            call.error = str(e)
        return call

    def _assess_confidence(self, trace: AgentTrace) -> float:
        confidence = 0.5
        if any(c.server == "sensors" and c.result for c in trace.tool_calls):
            confidence += 0.15
        if any(c.server == "weather" and c.result for c in trace.tool_calls):
            confidence += 0.1
        for c in trace.tool_calls:
            if c.server == "knowledge" and c.result and isinstance(c.result, dict):
                diseases = c.result.get("possible_diseases", [])
                if diseases and diseases[0].get("match_score", 0) > 1:
                    confidence += 0.15
        if trace.warnings:
            confidence += min(0.05 * len(trace.warnings), 0.1)
        return min(confidence, 0.95)

    # ============================================================
    # 意图处理器
    # ============================================================

    async def _handle_diagnose(self, query: str, gh_id: str, crop: str) -> AgentTrace:
        trace = AgentTrace(intent=Intent.DIAGNOSE, reasoning="检测到诊断意图，启动多源数据汇聚诊断流程")

        # Step 1: 传感器
        sensor_call = await self._call_tool("sensors", "get_current_reading", {"greenhouse_id": gh_id})
        trace.tool_calls.append(sensor_call)

        # Step 2: 天气
        weather_call = await self._call_tool("weather", "get_weather_for_irrigation", {})
        trace.tool_calls.append(weather_call)

        # Step 3: 综合诊断
        current_conditions = {}
        if sensor_call.result and "sensors" in sensor_call.result:
            sensors = sensor_call.result["sensors"]
            current_conditions = {
                "temperature": sensors.get("air_temperature", {}).get("value"),
                "humidity": sensors.get("air_humidity", {}).get("value"),
                "soil_moisture": sensors.get("soil_moisture", {}).get("value"),
            }

        diagnose_call = await self._call_tool("knowledge", "diagnose_and_advise", {
            "crop": crop,
            "symptoms": query,
            "current_conditions": current_conditions,
        })
        trace.tool_calls.append(diagnose_call)

        # Step 4: 检查异常
        if sensor_call.result:
            sensors = sensor_call.result.get("sensors", {})
            for name, data in sensors.items():
                if data.get("status") == "warning":
                    trace.warnings.append(f"{name}: {_format_sensor_value(data)} (异常)")

        # Step 5: 综合评估
        trace.confidence = self._assess_confidence(trace)

        if diagnose_call.result:
            diseases = diagnose_call.result.get("possible_diseases", [])
            if diseases:
                top = diseases[0]
                trace.synthesis = (
                    f"根据症状描述「{query}」和当前环境数据，"
                    f"最可能的诊断是：{top.get('name', '未知')}（匹配度: {top.get('match_score', 0):.1f}）"
                )
                if top.get("full_info"):
                    info = top["full_info"]
                    trace.recommendations = info.get("treatment", [])[:2] + info.get("prevention", [])[:2]
            else:
                trace.synthesis = "知识库中未找到与描述高度匹配的病害，建议进一步观察或送检"
                trace.confidence = 0.3

        if trace.warnings:
            trace.recommendations.insert(0, f"⚠️ 当前环境存在异常: {'; '.join(trace.warnings[:3])}")

        return trace

    async def _handle_monitor(self, query: str, gh_id: str, crop: str) -> AgentTrace:
        trace = AgentTrace(intent=Intent.MONITOR, reasoning="检测到监控意图，获取当前环境数据")

        sensor_call = await self._call_tool("sensors", "get_current_reading", {"greenhouse_id": gh_id})
        trace.tool_calls.append(sensor_call)

        conditions_call = await self._call_tool("knowledge", "get_optimal_conditions", {"crop": crop})
        trace.tool_calls.append(conditions_call)

        if sensor_call.result:
            sensors = sensor_call.result.get("sensors", {})
            deviations = []
            air_temp = sensors.get("air_temperature", {}).get("value", 0)
            if air_temp > 32:
                deviations.append(f"空气温度偏高 ({air_temp}°C)")
            elif air_temp < 18:
                deviations.append(f"空气温度偏低 ({air_temp}°C)")

            air_hum = sensors.get("air_humidity", {}).get("value", 0)
            if air_hum > 85:
                deviations.append(f"空气湿度过高 ({air_hum}%)")
            elif air_hum < 40:
                deviations.append(f"空气湿度过低 ({air_hum}%)")

            trace.warnings = deviations
            trace.synthesis = f"【{sensor_call.result.get('greenhouse_name', gh_id)}】当前状态"
            if deviations:
                trace.synthesis += f"，发现 {len(deviations)} 项偏差"
                trace.recommendations = [f"建议关注: {d}" for d in deviations]
            else:
                trace.synthesis += "，各项指标正常"
                trace.confidence = 0.9

        return trace

    async def _handle_irrigate(self, query: str, gh_id: str, crop: str) -> AgentTrace:
        trace = AgentTrace(intent=Intent.IRRIGATE, reasoning="检测到灌溉决策意图，获取土壤数据和天气预报")

        sensor_call = await self._call_tool("sensors", "get_current_reading", {"greenhouse_id": gh_id})
        trace.tool_calls.append(sensor_call)

        weather_call = await self._call_tool("weather", "get_weather_for_irrigation", {})
        trace.tool_calls.append(weather_call)

        guide_call = await self._call_tool("knowledge", "get_farming_guide", {"crop": crop})
        trace.tool_calls.append(guide_call)

        soil_moisture = 50
        if sensor_call.result:
            soil_moisture = sensor_call.result.get("sensors", {}).get("soil_moisture", {}).get("value", 50)

        should_irrigate = False
        reasons = []
        if weather_call.result:
            advice = weather_call.result.get("irrigation_advice", {})
            if advice.get("should_irrigate"):
                should_irrigate = True
                reasons.append(advice.get("reason", ""))
        if soil_moisture < 35:
            should_irrigate = True
            reasons.append(f"土壤含水量偏低 ({soil_moisture}%)")

        trace.synthesis = f"灌溉建议: {'建议灌溉' if should_irrigate else '暂不需要灌溉'}"
        trace.recommendations = reasons if reasons else ["土壤湿度和天气条件均适宜，无需灌溉"]
        trace.confidence = 0.8
        return trace

    async def _handle_alert(self, query: str, gh_id: str, crop: str) -> AgentTrace:
        trace = AgentTrace(intent=Intent.ALERT, reasoning="检测到预警查询意图，检查所有预警源")

        weather_alerts = await self._call_tool("weather", "get_weather_alerts", {})
        trace.tool_calls.append(weather_alerts)

        sensor_call = await self._call_tool("sensors", "get_current_reading", {"greenhouse_id": gh_id})
        trace.tool_calls.append(sensor_call)

        all_alerts = []
        if weather_alerts.result:
            for alert in weather_alerts.result:
                if alert.get("type") != "无预警":
                    all_alerts.append(f"气象: {alert['type']} - {alert.get('description', '')}")

        if sensor_call.result:
            sensors = sensor_call.result.get("sensors", {})
            for name, data in sensors.items():
                if data.get("status") == "warning":
                    all_alerts.append(f"传感器: {name} = {_format_sensor_value(data)}")

        trace.warnings = all_alerts
        trace.synthesis = f"当前共有 {len(all_alerts)} 条预警" if all_alerts else "当前无预警"
        trace.confidence = 0.85
        return trace

    # ============================================================
    # 主入口
    # ============================================================

    async def route(self, query: str) -> AgentTrace:
        intent, _ = self._classify_intent(query)
        gh_id = self._extract_greenhouse_id(query)
        crop = self._extract_crop(query)

        handler_map = {
            Intent.DIAGNOSE: self._handle_diagnose,
            Intent.MONITOR: self._handle_monitor,
            Intent.IRRIGATE: self._handle_irrigate,
            Intent.ALERT: self._handle_alert,
        }

        handler = handler_map.get(intent, self._handle_monitor)
        if intent not in handler_map:
            intent = Intent.MONITOR

        return await handler(query, gh_id, crop)

    def format_trace(self, trace: AgentTrace) -> str:
        intent_names = {
            Intent.DIAGNOSE: "病虫害诊断",
            Intent.MONITOR: "环境监控",
            Intent.PREDICT: "趋势预测",
            Intent.IRRIGATE: "灌溉决策",
            Intent.ALERT: "预警查询",
            Intent.GUIDE: "种植指南",
        }
        lines = []
        lines.append(f"━━━ {intent_names.get(trace.intent, '未知')} ━━━")
        lines.append(f"意图识别: {trace.reasoning}")
        lines.append("")

        lines.append("📋 数据采集链路:")
        for i, call in enumerate(trace.tool_calls, 1):
            status = "✅" if call.result and not call.error else "❌"
            lines.append(f"  {i}. {status} [{call.server}] {call.tool}")
            if call.error:
                lines.append(f"     错误: {call.error}")
        lines.append("")

        lines.append(f"🔍 诊断结论: {trace.synthesis}")
        lines.append(f"📊 置信度: {trace.confidence:.0%}")
        lines.append("")

        if trace.warnings:
            lines.append("⚠️  预警信息:")
            for w in trace.warnings:
                lines.append(f"  • {w}")
            lines.append("")

        if trace.recommendations:
            lines.append("💡 建议措施:")
            for r in trace.recommendations:
                lines.append(f"  • {r}")

        return "\n".join(lines)
