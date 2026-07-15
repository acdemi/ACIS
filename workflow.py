"""LangGraph workflow nodes for the agriculture Agent system.

ACIS 2.0: 主图增加条件循环（多轮辩论）。当 Judge 置信度落在 0.6~0.85 且辩论轮次
<2、且存在冲突/缺失证据时，进入 rebuttal 节点：收集 Judge 指出的关键冲突与质疑，
重新调用相关专家给出第二轮意见，再次 debate -> critic -> judge。第二轮 Judge 注明
"第二轮辩论后裁决"并比较两轮意见。环境变量 ``AGRI_AI_MULTI_ROUND_DEBATE=0`` 可关闭。
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    query: str
    image_path: str | None
    context: Any
    perception_outputs: list[Any]
    memory_outputs: list[Any]
    expert_outputs: list[Any]
    rebuttal_outputs: list[Any]
    outputs: list[Any]
    debate: Any
    decision: Any
    debate_round: int
    debate_history: list[Any]
    rebuttal_context: str


class AgricultureWorkflow:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def compile(self):
        from langgraph.graph import END, StateGraph

        graph = StateGraph(WorkflowState)
        graph.add_node("context", self.context_node)
        graph.add_node("perception", self.perception_node)
        graph.add_node("memory", self.memory_node)
        graph.add_node("experts", self.experts_node)
        graph.add_node("debate", self.debate_node)
        graph.add_node("critic", self.critic_node)
        graph.add_node("judge", self.judge_node)
        graph.add_node("rebuttal", self.rebuttal_node)

        graph.set_entry_point("context")
        graph.add_edge("context", "perception")
        graph.add_edge("perception", "memory")
        graph.add_edge("memory", "experts")
        graph.add_edge("experts", "debate")
        graph.add_edge("debate", "critic")
        graph.add_edge("critic", "judge")
        # ACIS 2.0: judge -> 条件循环(多轮辩论) 或 结束
        graph.add_conditional_edges("judge", self.should_rebuttal, {"rebuttal": "rebuttal", END: END})
        graph.add_edge("rebuttal", "debate")
        return graph.compile()

    def context_node(self, state: WorkflowState) -> WorkflowState:
        from orchestrator import build_context

        return {
            **state,
            "context": build_context(state["query"], state.get("image_path")),
            "debate_round": 1,
            "debate_history": [],
        }

    def perception_node(self, state: WorkflowState) -> WorkflowState:
        context = state["context"]
        orchestrator = self.orchestrator
        perception_outputs = [
            orchestrator.vision_agent.run(context),
            orchestrator.sensor_agent.run(context),
            orchestrator.weather_agent.run(context),
        ]
        return {**state, "perception_outputs": perception_outputs}

    def memory_node(self, state: WorkflowState) -> WorkflowState:
        context = state["context"]
        orchestrator = self.orchestrator
        memory_outputs = [
            orchestrator.rag_agent.run(context),
            orchestrator.knowledge_graph_agent.run(context),
            orchestrator.case_memory_agent.run(context),
            orchestrator.outcome_agent.run(context),
        ]
        return {**state, "memory_outputs": memory_outputs}

    def experts_node(self, state: WorkflowState) -> WorkflowState:
        context = state["context"]
        orchestrator = self.orchestrator
        sensor_output = next(
            output for output in state["perception_outputs"] if output.agent == "传感器Agent"
        )
        expert_outputs = [
            orchestrator.pathology_agent.run(context, sensor_output),
            orchestrator.meteorology_agent.run(context),
            orchestrator.cultivation_agent.run(context, sensor_output),
        ]
        # ACIS 2.0: 经济 & 生态 Agent 依据技术专家意见做成本/生态评估（可降级）
        if os.environ.get("AGRI_AI_EXTRA_EXPERTS", "1") not in {"0", "false", "False"}:
            expert_outputs.append(orchestrator.economic_agent.run(context, expert_outputs[0], expert_outputs[2]))
            expert_outputs.append(orchestrator.ecology_agent.run(context, expert_outputs))
        return {**state, "expert_outputs": expert_outputs}

    def debate_node(self, state: WorkflowState) -> WorkflowState:
        outputs = state["perception_outputs"] + state["memory_outputs"] + state["expert_outputs"]
        rebuttal = state.get("rebuttal_outputs") or []
        if rebuttal:
            outputs = outputs + rebuttal
        round_num = state.get("debate_round", 1)
        history = state.get("debate_history") or []
        debate = self.orchestrator.debate_engine.run(
            outputs, state["context"], multi_round=round_num >= 2, history=history
        )
        return {**state, "outputs": outputs, "debate": debate}

    def critic_node(self, state: WorkflowState) -> WorkflowState:
        outputs, debate = self.orchestrator.critic_engine.run(
            state["context"], state["outputs"], state["debate"]
        )
        return {**state, "outputs": outputs, "debate": debate}

    def rebuttal_node(self, state: WorkflowState) -> WorkflowState:
        """收集 Judge 指出的关键冲突与质疑，重新调用相关专家给出第二轮意见。"""
        context = state["context"]
        orchestrator = self.orchestrator
        debate = state["debate"]
        decision = state["decision"]
        doubts: list[str] = []
        doubts.extend(debate.conflicts)
        doubts.extend(debate.missing_evidence)
        if debate.critic.get("resolution"):
            doubts.append("Critic质疑：" + debate.critic["resolution"])
        doubt_text = " | ".join(doubts) if doubts else "无明确冲突，复核首轮意见"
        sensor_output = next(
            output for output in state["perception_outputs"] if output.agent == "传感器Agent"
        )
        round2 = []
        for out in [
            orchestrator.pathology_agent.run(context, sensor_output),
            orchestrator.meteorology_agent.run(context),
            orchestrator.cultivation_agent.run(context, sensor_output),
        ]:
            tagged = replace(
                out,
                evidence={**out.evidence, "rebuttal_round": 2, "rebuttal_doubts": doubt_text},
            )
            round2.append(tagged)
        history = list(state.get("debate_history", [])) + [debate]
        return {
            **state,
            "debate_round": state.get("debate_round", 1) + 1,
            "debate_history": history,
            "rebuttal_outputs": round2,
            "rebuttal_context": doubt_text,
        }

    def judge_node(self, state: WorkflowState) -> WorkflowState:
        round_num = state.get("debate_round", 1)
        decision = self.orchestrator.judge_agent.run(
            state["context"], state["outputs"], state["debate"], debate_round=round_num
        )
        return {**state, "decision": decision}

    @staticmethod
    def should_rebuttal(state: WorkflowState) -> str:
        from langgraph.graph import END

        if os.environ.get("AGRI_AI_MULTI_ROUND_DEBATE", "1") in {"0", "false", "False"}:
            return END
        decision = state.get("decision")
        round_num = state.get("debate_round", 1)
        if decision is None or round_num >= 2:
            return END
        if 0.6 <= decision.confidence <= 0.85 and (
            decision.debate.conflicts or decision.debate.missing_evidence
        ):
            return "rebuttal"
        return END


def compile_workflow(orchestrator):
    return AgricultureWorkflow(orchestrator).compile()
