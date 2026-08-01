"""Planner MVP - turns a Judge DecisionOutput into a high-level ExecutionPlan.

Sprint 01: the Planner runs AFTER the Judge (decision-level action planning per
ADR-003), a pragmatic MVP subset of RFC-008. It is optional, enabled via
``ACIS_ENABLE_PLANNER=true``; otherwise the existing pipeline is unchanged. The
Planner NEVER calls tools - it only decides which tools would be required. Tool
execution belongs to the MCP layer (later sprint).

Rule-based by default (deterministic, no API key, no new dependencies). Optional
LLM mode (``use_llm=True``) mirrors JudgeAgent/CriticEngine: DeepSeek via the
OpenAI-compatible client, JSON mode, graceful fallback to rules.
"""
from __future__ import annotations

import json
import os
from typing import Any

from agents.types import DecisionOutput
from planner import prompts
from planner.types import ExecutionPlan

_VALID_LEVELS = {"low", "medium", "high"}


class Planner:
    """Generate an ExecutionPlan from a Judge DecisionOutput without executing tools."""

    name = "PlannerAgent"

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def plan(self, decision: DecisionOutput) -> ExecutionPlan:
        if self.use_llm:
            try:
                llm_plan = self._plan_with_llm(decision)
                if llm_plan is not None:
                    return llm_plan
            except Exception:
                pass
        return self._plan_with_rules(decision)

    # ------------------------------------------------------------------
    # rule mode
    # ------------------------------------------------------------------
    def _plan_with_rules(self, decision: DecisionOutput) -> ExecutionPlan:
        required_tools = self._derive_tools(decision)
        return ExecutionPlan(
            goal=f"执行 Judge 裁决：{decision.decision}",
            steps=self._derive_steps(decision),
            required_tools=required_tools,
            priority=self._derive_priority(decision),
            estimated_risk=self._derive_risk(decision, required_tools),
            estimated_cost=self._derive_cost(required_tools),
        )

    @staticmethod
    def _derive_steps(decision: DecisionOutput) -> list[str]:
        steps: list[str] = []
        if decision.need_human_review:
            steps.append("人工复核裁决与关键证据后再执行")
        for item in decision.action_plan[:6]:
            if item not in steps:
                steps.append(item)
        if decision.debate.missing_evidence:
            steps.append("补充缺失证据并复评")
        if not steps:
            steps.append("按裁决建议执行")
        return steps

    @staticmethod
    def _derive_tools(decision: DecisionOutput) -> list[str]:
        tools: list[str] = []
        if decision.need_human_review:
            tools.append("human_review")
        if decision.debate.missing_evidence:
            tools.append("image_capture")
        pathology = next((t for t in decision.traces if t.agent == "病理Agent"), None)
        if pathology and "病理判断首选" in pathology.claim and "病理证据不足" not in pathology.claim:
            tools.append("spray_workorder")
        meteorology = next((t for t in decision.traces if t.agent == "气象Agent"), None)
        if meteorology and "支持灌溉" in meteorology.claim:
            tools.append("irrigation_control")
        sensor = next((t for t in decision.traces if t.agent == "传感器Agent"), None)
        if sensor and "异常" in sensor.claim:
            tools.append("sensor_verify")
        return tools

    @staticmethod
    def _derive_priority(decision: DecisionOutput) -> str:
        if decision.need_human_review or decision.risk_level == "high":
            return "high"
        if decision.risk_level == "medium" or decision.confidence < 0.6:
            return "medium"
        return "low"

    @staticmethod
    def _derive_risk(decision: DecisionOutput, required_tools: list[str]) -> str:
        if decision.need_human_review or decision.debate.conflicts or decision.risk_level == "high":
            return "high"
        if decision.risk_level == "medium" or len(required_tools) >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _derive_cost(required_tools: list[str]) -> str:
        tool_set = set(required_tools)
        if not tool_set:
            return "low"
        if len(tool_set) >= 3:
            return "high"
        if tool_set & {"spray_workorder", "irrigation_control"}:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # llm mode
    # ------------------------------------------------------------------
    def _plan_with_llm(self, decision: DecisionOutput) -> ExecutionPlan | None:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        model = os.environ.get("AGRI_AI_PLANNER_MODEL") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompts.PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(self._build_payload(decision), ensure_ascii=False)},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        llm = json.loads(resp.choices[0].message.content or "{}")
        fb = self._plan_with_rules(decision)
        return ExecutionPlan(
            goal=str(llm.get("goal") or fb.goal),
            steps=self._clean_list(llm.get("steps")) or fb.steps,
            required_tools=self._clean_list(llm.get("required_tools")) or fb.required_tools,
            priority=self._clean_level(llm.get("priority"), fb.priority),
            estimated_risk=self._clean_level(llm.get("estimated_risk"), fb.estimated_risk),
            estimated_cost=self._clean_level(llm.get("estimated_cost"), fb.estimated_cost),
        )

    @staticmethod
    def _build_payload(decision: DecisionOutput) -> dict[str, Any]:
        return {
            "裁决": {
                "summary": decision.summary,
                "decision": decision.decision,
                "confidence": decision.confidence,
                "risk_level": decision.risk_level,
                "need_human_review": decision.need_human_review,
                "action_plan": decision.action_plan,
                "reasoning_trace": decision.reasoning_trace,
            },
            "debate": {
                "conflicts": decision.debate.conflicts,
                "missing_evidence": decision.debate.missing_evidence,
                "risk_level": decision.debate.risk_level,
            },
            "traces": [
                {"agent": t.agent, "layer": t.layer, "claim": t.claim, "confidence": t.confidence}
                for t in decision.traces
            ],
            "output_schema": prompts.OUTPUT_SCHEMA_DESCRIPTION,
        }

    @staticmethod
    def _clean_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _clean_level(value: Any, default: str) -> str:
        text = str(value or "").strip().lower()
        return text if text in _VALID_LEVELS else default


def build_planner() -> Planner | None:
    """Construct a Planner when ACIS_ENABLE_PLANNER is truthy, else None.

    Truthy values: ``1``, ``true``, ``yes`` (case-insensitive). Anything else
    (including unset) keeps the existing pipeline behavior unchanged.
    """
    if os.environ.get("ACIS_ENABLE_PLANNER", "").strip().lower() in {"1", "true", "yes"}:
        return Planner()
    return None