"""Planner prompts for the optional DeepSeek (OpenAI-compatible) mode.

The rule-based path is the default and deterministic. The LLM path mirrors
JudgeAgent / CriticEngine: DeepSeek via the OpenAI client, JSON mode, graceful
fallback to rules. Prompt text is kept here, outside the planner logic.
"""
from __future__ import annotations

from typing import Any

PLANNER_SYSTEM_PROMPT = (
    "你是农业多智能体决策系统中的 Planner（执行规划官）。Judge 已给出最终裁决，"
    "你的任务不是重新诊断，而是把裁决转化为一份高层执行计划 ExecutionPlan，"
    "并判断是否需要外部工具（MCP）。\n"
    "按顺序执行：1) 从裁决提炼目标 goal；"
    "2) 把 action_plan 与风险/人工复核信号组织为有序高层步骤 steps；"
    "3) 判断落实计划是否需要外部工具 required_tools（如 image_capture、spray_workorder、"
    "irrigation_control、sensor_verify、human_review），无需则为空数组，只判定不调用；"
    "4) 结合 risk_level、need_human_review、置信度给出 priority；"
    "5) 给出 estimated_risk 与 estimated_cost。\n"
    "约束：不得创造裁决中没有的事实；不得调用工具；只输出 JSON。"
    "字段严格为：goal, steps, required_tools, priority, estimated_risk, estimated_cost。"
)

OUTPUT_SCHEMA_DESCRIPTION: dict[str, Any] = {
    "goal": "本次执行目标，一句中文",
    "steps": ["有序高层执行步骤，中文字符串数组"],
    "required_tools": ["需要的外部工具名称数组；无需则为空数组"],
    "priority": "low | medium | high",
    "estimated_risk": "low | medium | high",
    "estimated_cost": "low | medium | high",
}