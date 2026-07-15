"""
农业 Agent MVP v4 — 分层协作编排实验

架构：
- 用户层：CLI / Web / App / 微信小程序入口可统一调用 Orchestrator
- Agent Orchestrator：中央调度、上下文抽取、工作流编排
- 感知层：视觉 Agent、传感器 Agent、天气 Agent
- 专家层：病理 Agent、气象 Agent、栽培 Agent
- 记忆层：RAG、知识图谱、历史案例库
- Debate & Judge：多专家交叉质询与最终裁决

Agent 类定义已拆分到 `agents/` 和 `debate/` 各自文件，
此处仅保留 orchestrator 核心编排逻辑。
"""

from __future__ import annotations

import argparse
import json
import os

from _env import load_env

load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD）

from agents.types import AgentOutput, RequestContext, DebateResult, DecisionOutput
from agents.sensor_agent import SensorAgent
from agents.weather_agent import WeatherAgent
from agents.vision_agent import VisionAgent
from agents.rag_memory_agent import RagMemoryAgent
from agents.kg_agent import KnowledgeGraphAgent
from agents.case_memory_agent import CaseMemoryAgent
from agents.outcome_agent import OutcomeAgent
from agents.pathology_agent import PathologyAgent
from agents.meteorology_agent import MeteorologyExpertAgent
from agents.cultivation_agent import CultivationAgent
from agents.economic_agent import EconomicAgent
from agents.ecology_agent import EcologyAgent
from agents.judge_agent import JudgeAgent
from debate.engine import DebateEngine


def _extract_greenhouse_id(query: str) -> str:
    if any(keyword in query for keyword in ["温室B", "温室b", "黄瓜", "gh-b", "greenhouse_b"]):
        return "gh-b"
    return "gh-a"


def _extract_crop(query: str) -> str:
    if "甜菜" in query:
        return "sugar_beet"
    if "棉花" in query:
        return "cotton"
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


class AgentOrchestrator:
    def __init__(self, use_langgraph: bool = True, use_llm_judge: bool = False, use_llm_critic: bool = False):
        self.use_langgraph = use_langgraph
        self.vision_agent = VisionAgent()
        self.sensor_agent = SensorAgent()
        self.weather_agent = WeatherAgent()
        self.rag_agent = RagMemoryAgent()
        self.knowledge_graph_agent = KnowledgeGraphAgent()
        self.case_memory_agent = CaseMemoryAgent()
        self.outcome_agent = OutcomeAgent()
        self.pathology_agent = PathologyAgent()
        self.meteorology_agent = MeteorologyExpertAgent()
        self.cultivation_agent = CultivationAgent()
        self.economic_agent = EconomicAgent()
        self.ecology_agent = EcologyAgent()
        self.debate_engine = DebateEngine()
        from debate.critic import CriticEngine
        self.critic_engine = CriticEngine(use_llm=use_llm_critic)
        self.judge_agent = JudgeAgent(use_llm=use_llm_judge)
        self._compiled_graph = self._build_langgraph() if use_langgraph else None

    def run(self, query: str, image_path: str | None = None) -> DecisionOutput:
        decision = self._run_core(query, image_path)
        self._persist(decision, query, image_path)
        return decision

    def _run_core(self, query: str, image_path: str | None = None) -> DecisionOutput:
        if self._compiled_graph is not None:
            try:
                final_state = self._compiled_graph.invoke({"query": query, "image_path": image_path})
                return final_state["decision"]
            except Exception as exc:
                fallback_decision = self.run_rules(query, image_path)
                fallback_decision.debate.missing_evidence.append(
                    f"LangGraph 主图执行失败，已回退规则编排：{exc}"
                )
                return fallback_decision

        return self.run_rules(query, image_path)

    def _persist(self, decision: DecisionOutput, query: str, image_path: str | None) -> None:
        """SQLite 持久化；失败不影响核心流程（AGRI_AI_PERSIST=0 可关闭）。"""
        if os.environ.get("AGRI_AI_PERSIST", "1") != "1":
            return
        try:
            from storage.repository import save_decision
            ctx = build_context(query, image_path)
            save_decision(decision, ctx, query)
        except Exception:
            pass

    def run_rules(self, query: str, image_path: str | None = None) -> DecisionOutput:
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
            self.outcome_agent.run(context),
        ]

        expert_outputs = [
            self.pathology_agent.run(context, sensor_output),
            self.meteorology_agent.run(context),
            self.cultivation_agent.run(context, sensor_output),
        ]
        # ACIS 2.0: 经济 & 生态 Agent 依据技术专家意见做成本/生态评估（可降级）
        if os.environ.get("AGRI_AI_EXTRA_EXPERTS", "1") not in {"0", "false", "False"}:
            expert_outputs.append(self.economic_agent.run(context, expert_outputs[0], expert_outputs[2]))
            expert_outputs.append(self.ecology_agent.run(context, expert_outputs))

        outputs = perception_outputs + memory_outputs + expert_outputs
        debate = self.debate_engine.run(outputs, context)
        outputs, debate = self.critic_engine.run(context, outputs, debate)
        return self.judge_agent.run(context, outputs, debate)

    def _build_langgraph(self):
        try:
            from workflow import compile_workflow
        except ImportError:
            return None
        return compile_workflow(self)


def format_decision(decision: DecisionOutput) -> str:
    lines = [
        "=" * 60,
        "农业 Agent v4 — Orchestrator / Debate / Judge",
        "=" * 60,
        f"\n【总结】{decision.summary}",
        f"【裁决】{decision.decision}",
        f"【Judge】{decision.judge_mode}",
        f"【置信度】{decision.confidence:.0%}",
        f"【风险等级】{decision.risk_level}",
        f"【人工复核】{'是' if decision.need_human_review else '否'}",
        "\n【Debate 共识】",
    ]
    lines.extend(f"- {item}" for item in decision.debate.consensus)

    if decision.debate.conflicts:
        lines.append("\n【Debate 冲突】")
        lines.extend(f"- {item}" for item in decision.debate.conflicts)

    if decision.debate.critic.get("triggered"):
        lines.append("\n【Critic 反驳轮次】")
        lines.append(f"- {decision.debate.critic.get('resolution', '')}")
        for dw in decision.debate.critic.get("down_weighted", []):
            lines.append(f"- {dw['agent']} 置信度 {dw['from']:.0%} → {dw['to']:.0%}")

    if decision.debate.missing_evidence:
        lines.append("\n【缺失证据】")
        lines.extend(f"- {item}" for item in decision.debate.missing_evidence)

    if decision.reasoning_trace:
        lines.append("\n【裁决推理】")
        lines.append(decision.reasoning_trace)

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
    parser.add_argument("--rules-only", action="store_true", help="禁用 LangGraph，直接使用规则编排")
    parser.add_argument("--llm-judge", action="store_true", help="启用 DeepSeek 结构化 Judge；失败时自动回退规则裁决")
    parser.add_argument("--llm-critic", action="store_true", help="启用 DeepSeek 结构化 Critic 反驳；无 key 或失败时回退规则反驳")
    args = parser.parse_args()

    orchestrator = AgentOrchestrator(use_langgraph=not args.rules_only, use_llm_judge=args.llm_judge, use_llm_critic=args.llm_critic)
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