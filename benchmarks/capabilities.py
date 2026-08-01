"""ACIS cognitive capability model (Phase 2.1E, Sprint 04.5A).

Defines the stable set of cognitive capabilities the benchmark measures.
The capability model describes what the system *should* be able to do
cognitively — it is deliberately decoupled from the current module layout so
modules can be refactored without invalidating benchmark measurements
(设计原则：能力抽象化，测量标准化).
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable


class Capability(str, Enum):
    """Stable ACIS cognitive capability identifiers."""

    INFORMATION_GATHERING = "information_gathering"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    CONFLICT_RESOLUTION = "conflict_resolution"
    COUNTERFACTUAL_REASONING = "counterfactual_reasoning"
    UNCERTAINTY_QUANTIFICATION = "uncertainty_quantification"
    MULTI_STEP_PLANNING = "multi_step_planning"
    SENSOR_CROSS_VALIDATION = "sensor_cross_validation"

    @property
    def description_zh(self) -> str:
        """Chinese description of the capability."""
        return _CAPABILITY_INFO[self.value][0]

    @property
    def trigger_scenarios(self) -> tuple[str, ...]:
        """Typical scenarios that exercise this capability."""
        return _CAPABILITY_INFO[self.value][1]


#: Capability metadata keyed by enum value:
#: ``{value: (Chinese description, typical trigger scenarios)}``.
_CAPABILITY_INFO: dict[str, tuple[str, tuple[str, ...]]] = {
    "information_gathering": (
        "主动请求缺失信息（温度、湿度、近期用药等）",
        ("症状描述不完整", "缺少关键环境参数或用药史"),
    ),
    "knowledge_retrieval": (
        "从长尾/罕见知识库（KG/RAG）中检索相关证据",
        ("非主流作物病害", "少见/生理性症状", "需要历史案例佐证"),
    ),
    "conflict_resolution": (
        "在多源矛盾（文本 vs 传感器、视觉 vs 环境）中消解冲突",
        ("灌溉建议与病害风险冲突", "症状与环境数据矛盾", "专家意见分歧"),
    ),
    "counterfactual_reasoning": (
        "生成并评估替代诊断，抑制集体遗漏",
        ("多病害症状并存", "需要排除相近病害", "替代诊断与排除理由"),
    ),
    "uncertainty_quantification": (
        "在证据不足时主动降低置信度或拒绝回答",
        ("症状信息不足", "非知识库覆盖的生理性问题", "证据不足的边界案例"),
    ),
    "multi_step_planning": (
        "将复杂问题分解为子任务并依次调用工具",
        ("多步农事任务", "作业排序与工具需求", "周期型防治计划"),
    ),
    "sensor_cross_validation": (
        "交叉验证多模态传感器读数，检测异常",
        ("传感器读数异常", "多传感器数据矛盾", "环境-症状协同判断"),
    ),
}

#: All capability members in declaration order.
ALL_CAPABILITIES: tuple[Capability, ...] = tuple(Capability)


def parse_capabilities(values: Iterable[str]) -> tuple[Capability, ...]:
    """Parse and validate a list of capability strings.

    Unknown values raise ``ValueError``; duplicates are removed while keeping
    declaration order.
    """
    parsed: list[Capability] = []
    for value in values:
        try:
            parsed.append(Capability(value))
        except ValueError:
            raise ValueError(
                f"unknown capability {value!r}; "
                f"expected one of {[c.value for c in ALL_CAPABILITIES]}"
            ) from None
    return tuple(dict.fromkeys(parsed))


#: Mapping from legacy ``expected_reasoning_features`` to capabilities.
_FEATURE_TO_CAPABILITY: dict[str, Capability] = {
    "information_request": Capability.INFORMATION_GATHERING,
    "knowledge_retrieval": Capability.KNOWLEDGE_RETRIEVAL,
    "conflict_resolution": Capability.CONFLICT_RESOLUTION,
    "counterfactual_analysis": Capability.COUNTERFACTUAL_REASONING,
}


def capability_from_reasoning_feature(feature: str) -> Capability | None:
    """Map a legacy reasoning feature to its capability (if any)."""
    return _FEATURE_TO_CAPABILITY.get(feature)


__all__ = [
    "ALL_CAPABILITIES",
    "Capability",
    "capability_from_reasoning_feature",
    "parse_capabilities",
]
