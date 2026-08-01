"""Benchmark metadata standardization (Phase 2.1E, Sprint 04.5).

Defines :class:`BenchmarkMetadata` — the standardized per-case metadata
attached to every ``enriched.json`` case — plus the five cognitive challenge
types the enriched benchmark covers:

- ``missing_information`` — 症状信息不完整，系统应主动请求补充信息；
- ``contradictory_evidence`` — 症状与现场/环境证据矛盾，需要冲突消解；
- ``multi_disease`` — 多病害症状并存，需要候选排序与反事实排除；
- ``rare_knowledge`` — 非主流作物或非侵染性（生理性）问题的知识边界；
- ``sensor_conflict`` — 传感器异常与病害/农事决策叠加时的融合判断。

Phase 2.1E, Sprint 04.5A (Capability Framework): :class:`BenchmarkMetadata`
gains a ``capabilities`` field (a list of :class:`Capability`) as the primary
capability classification. ``challenge_type`` is retained but is no longer
the primary classification dimension. New cases must declare at least one
capability; legacy datasets (e.g. the current ``enriched.json``) are scanned
leniently and reported as pending annotation.

This module is domain-free: it only validates JSON-native metadata dicts.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from benchmarks.capabilities import Capability, parse_capabilities

#: The five cognitive challenge types covered by the enriched benchmark.
CHALLENGE_TYPES: tuple[str, ...] = (
    "missing_information",
    "contradictory_evidence",
    "multi_disease",
    "rare_knowledge",
    "sensor_conflict",
)

#: Supported noise levels.
NOISE_LEVELS: tuple[str, ...] = ("low", "medium", "high")

#: Reasoning features the pipeline is expected to exhibit.
REASONING_FEATURES: tuple[str, ...] = (
    "information_request",
    "knowledge_retrieval",
    "counterfactual_analysis",
    "conflict_resolution",
)

DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5


@dataclass(frozen=True)
class BenchmarkMetadata:
    """Standardized metadata carried by every enriched benchmark case.

    ``capabilities`` is the primary capability classification introduced by
    the Capability Framework (Sprint 04.5A); ``challenge_type`` is retained
    but is no longer the primary classification dimension.
    """

    challenge_type: str
    expected_reasoning_features: tuple[str, ...]
    capabilities: tuple[Capability, ...]
    difficulty: int
    crop: str
    disease: str | None
    noise_level: str
    modalities: tuple[str, ...]
    design_intent: str


class BenchmarkMetadataError(ValueError):
    """Raised when case metadata violates the enrichment contract."""


def validate_metadata(
    value: Any,
    *,
    require_capabilities: bool = True,
) -> BenchmarkMetadata:
    """Validate a raw ``metadata`` dict and return a ``BenchmarkMetadata``.

    New cases must declare a non-empty ``capabilities`` list
    (``require_capabilities=True``). Legacy datasets (e.g. the current
    ``enriched.json``) predate the Capability Framework and are scanned with
    ``require_capabilities=False`` so their cases are reported as pending
    annotation rather than rejected.
    """
    if not isinstance(value, dict):
        raise BenchmarkMetadataError("metadata must be an object")

    challenge_type = value.get("challenge_type")
    if challenge_type not in CHALLENGE_TYPES:
        raise BenchmarkMetadataError(
            f"unknown challenge_type {challenge_type!r}; "
            f"expected one of {list(CHALLENGE_TYPES)}"
        )

    features = value.get("expected_reasoning_features")
    if (
        not isinstance(features, list)
        or not features
        or not all(
            isinstance(feature, str) and feature.strip() for feature in features
        )
    ):
        raise BenchmarkMetadataError(
            "expected_reasoning_features must be a non-empty list of strings"
        )
    for feature in features:
        if feature not in REASONING_FEATURES:
            raise BenchmarkMetadataError(
                f"unknown reasoning feature {feature!r}; "
                f"expected one of {list(REASONING_FEATURES)}"
            )

    difficulty = value.get("difficulty")
    if (
        not isinstance(difficulty, int)
        or isinstance(difficulty, bool)
        or not DIFFICULTY_MIN <= difficulty <= DIFFICULTY_MAX
    ):
        raise BenchmarkMetadataError(
            f"difficulty must be an int in [{DIFFICULTY_MIN}, {DIFFICULTY_MAX}]"
        )

    crop = value.get("crop")
    if not isinstance(crop, str) or not crop.strip():
        raise BenchmarkMetadataError("crop must be a non-empty string")
    disease = value.get("disease")
    if disease is not None and not isinstance(disease, str):
        raise BenchmarkMetadataError("disease must be a string or null")

    noise_level = value.get("noise_level")
    if noise_level not in NOISE_LEVELS:
        raise BenchmarkMetadataError(
            f"unknown noise_level {noise_level!r}; "
            f"expected one of {list(NOISE_LEVELS)}"
        )

    modalities = value.get("modalities")
    if (
        not isinstance(modalities, list)
        or not modalities
        or not all(
            isinstance(modality, str) and modality.strip() for modality in modalities
        )
    ):
        raise BenchmarkMetadataError(
            "modalities must be a non-empty list of strings"
        )

    design_intent = value.get("design_intent")
    if not isinstance(design_intent, str) or not design_intent.strip():
        raise BenchmarkMetadataError("design_intent must be a non-empty string")

    capabilities = _parse_capability_list(
        value.get("capabilities"), require_capabilities
    )
    return BenchmarkMetadata(
        challenge_type=challenge_type,
        expected_reasoning_features=tuple(features),
        capabilities=capabilities,
        difficulty=difficulty,
        crop=crop,
        disease=disease,
        noise_level=noise_level,
        modalities=tuple(modalities),
        design_intent=design_intent,
    )


def validate_enriched_case(case: Any, index: int = 0) -> dict[str, Any]:
    """Validate one ``enriched.json`` case beyond the shared schema rules.

    Legacy enriched cases predate the Capability Framework; they are
    validated leniently (no ``capabilities`` requirement) and reported as
    pending annotation by the coverage scanner.
    """
    if not isinstance(case, dict):
        raise BenchmarkMetadataError(f"case {index} must be an object")
    for field in ("id", "query", "ground_truth"):
        value = case.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BenchmarkMetadataError(
                f"case {index}: {field} must be a non-empty string"
            )

    confidence_range = case.get("expected_confidence_range")
    if not _valid_confidence_range(confidence_range):
        raise BenchmarkMetadataError(
            f"case {index}: expected_confidence_range must be [min, max] "
            "within [0, 1]"
        )

    tools = case.get("expected_tools")
    if not isinstance(tools, list) or not all(
        isinstance(tool, str) and tool.strip() for tool in tools
    ):
        raise BenchmarkMetadataError(
            f"case {index}: expected_tools must be a list of strings"
        )

    validate_metadata(case.get("metadata"), require_capabilities=False)
    return dict(case)


def _parse_capability_list(
    value: Any,
    required: bool,
) -> tuple[Capability, ...]:
    if not isinstance(value, list) or not value:
        if required:
            raise BenchmarkMetadataError(
                "capabilities must be a non-empty list of capability names"
            )
        return ()
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise BenchmarkMetadataError("capabilities must be a list of strings")
    try:
        return parse_capabilities(value)
    except ValueError as exc:
        raise BenchmarkMetadataError(str(exc)) from None


def _valid_confidence_range(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    try:
        low, high = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return False
    return 0.0 <= low <= high <= 1.0


def challenge_counts(
    cases: Sequence[dict[str, Any]],
) -> dict[str, int]:
    """Count enriched cases per challenge type (legacy, capability-free scan)."""
    counts = {challenge: 0 for challenge in CHALLENGE_TYPES}
    for case in cases:
        metadata = validate_metadata(
            case.get("metadata"), require_capabilities=False
        )
        counts[metadata.challenge_type] += 1
    return counts


__all__ = [
    "CHALLENGE_TYPES",
    "DIFFICULTY_MAX",
    "DIFFICULTY_MIN",
    "NOISE_LEVELS",
    "REASONING_FEATURES",
    "BenchmarkMetadata",
    "BenchmarkMetadataError",
    "challenge_counts",
    "validate_enriched_case",
    "validate_metadata",
]
