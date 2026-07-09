"""LangGraph workflow nodes for the agriculture Agent system."""

from __future__ import annotations

from typing import Any, TypedDict

class WorkflowState(TypedDict, total=False):
    query: str
    image_path: str | None
    context: Any
    perception_outputs: list[Any]
    memory_outputs: list[Any]
    expert_outputs: list[Any]
    outputs: list[Any]
    debate: Any
    decision: Any


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

        graph.set_entry_point("context")
        graph.add_edge("context", "perception")
        graph.add_edge("perception", "memory")
        graph.add_edge("memory", "experts")
        graph.add_edge("experts", "debate")
        graph.add_edge("debate", "critic")
        graph.add_edge("critic", "judge")
        graph.add_edge("judge", END)
        return graph.compile()

    def context_node(self, state: WorkflowState) -> WorkflowState:
        from orchestrator import build_context

        return {
            **state,
            "context": build_context(state["query"], state.get("image_path")),
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
        return {**state, "expert_outputs": expert_outputs}

    def debate_node(self, state: WorkflowState) -> WorkflowState:
        outputs = state["perception_outputs"] + state["memory_outputs"] + state["expert_outputs"]
        debate = self.orchestrator.debate_engine.run(outputs, state["context"])
        return {**state, "outputs": outputs, "debate": debate}

    def critic_node(self, state: WorkflowState) -> WorkflowState:
        outputs, debate = self.orchestrator.critic_engine.run(
            state["context"], state["outputs"], state["debate"]
        )
        return {**state, "outputs": outputs, "debate": debate}

    def judge_node(self, state: WorkflowState) -> WorkflowState:
        decision = self.orchestrator.judge_agent.run(
            state["context"], state["outputs"], state["debate"]
        )
        return {**state, "decision": decision}


def compile_workflow(orchestrator):
    return AgricultureWorkflow(orchestrator).compile()

