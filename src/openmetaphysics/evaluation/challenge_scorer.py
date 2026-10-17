"""Challenge-set scoring metrics (Phase 4, Benchmark Validity Study).

Introduces three metrics that go beyond the saturated accuracy signal
(Phase 3: 64/64 cases correct, accuracy == 1.00 across all configurations):

- :func:`calc_confidence_calibration` — Expected Calibration Error (ECE) over
  decision confidence vs. observed correctness.
- :func:`calc_abstention_rate` — fraction of outputs that abstain
  (``证据不足`` / ``无法定论`` style decisions) instead of guessing.
- :func:`calc_reasoning_coherence` — legacy name for a 0-3 quantized
  factor-coverage level. It does not measure logical consistency. Uses the existing
  ``deepseek-v4-flash`` model via the OpenAI-compatible gateway when
  ``DEEPSEEK_API_KEY`` is set, and falls back to a deterministic keyword
  rule engine over :data:`FACTOR_ALIASES` otherwise. The rule fallback keeps
  the module runnable with no external dependency except the model API.

Agent outputs are accepted as plain dicts (``decision`` / ``claim``,
``confidence``, optional ``correct`` or ``expected``, ``abstained``) or as
dataclass-like objects exposing the same attributes, so the module stays
domain-free and does not import agent or evaluation-runner code.

This module is additive: it does not touch any agent logic, the retrieval
configuration, or the Phase 3 benchmark cases.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from typing import Any

from decision_semantics import (
    decision_correctness as _decision_correctness,
)
from decision_semantics import (
    decision_text as _shared_decision_text,
)
from decision_semantics import (
    is_abstention as _shared_is_abstention,
)
from decision_semantics import (
    normalize_decision_label as _shared_normalize_decision_label,
)

#: Legal probe group labels for the challenge set (``benchmarks/
#: challenge_set_v1.json``).
VALID_GROUPS: tuple[str, ...] = (
    "ambiguity",
    "conflicting",
    "incomplete",
    "multi_step",
)

#: Bin count for the expected calibration error.
ECE_BINS: int = 10

#: Model used for the reasoning-coherence factor judge unless overridden.
DEFAULT_COHERENCE_MODEL: str = "deepseek-v4-flash"

#: Chinese evidence keywords per expected key factor. Used by the rule
#: fallback of :func:`calc_reasoning_coherence` when the LLM judge is not
#: available. The vocabulary is derived from the in-domain knowledge base
#: (``rag/knowledge_base.py`` DISEASE_DB symptoms/conditions) so no external
#: knowledge is introduced.
FACTOR_ALIASES: dict[str, tuple[str, ...]] = {
    # -- symptom factors --
    "leaf_mold_layer": ("霉层", "绒状"),
    "backside_mold": ("叶背", "背面", "霉层"),
    "yellow_spot": ("黄斑", "淡黄色"),
    "concentric_ring": ("轮纹", "同心"),
    "brown_spot": ("褐", "褐色"),
    "gray_white_center": ("灰白",),
    "angular_lesion": ("多角",),
    "circular_spot": ("圆形",),
    "root_rot": ("根腐", "根部", "腐烂"),
    "wilt": ("萎蔫",),
    "yellowing": ("黄化", "发黄"),
    "mottling": ("黄绿斑驳", "斑驳"),
    "vascular_browning": ("维管束",),
    "half_leaf_yellowing": ("半边",),
    "edge_yellowing": ("叶缘",),
    "leaf_curl": ("卷曲", "干枯"),
    "stem_lesion": ("茎部",),
    "fruit_stage": ("果实", "膨大", "结果期"),
    "lower_leaf_start": ("下部", "老叶"),
    # -- environment factors --
    "high_humidity": ("湿度高", "湿度大", "多雨", "湿"),
    "low_humidity": ("干燥", "湿度低"),
    "high_temp": ("高温",),
    "low_temp": ("低温", "凉爽", "冷"),
    "leaf_dew": ("结露", "露"),
    "soil_wet": ("偏湿", "过湿", "积水", "漫灌"),
    "soil_dry": ("干旱", "偏干"),
    "poor_ventilation": ("通风不良", "通风"),
    # -- reasoning / decision factors --
    "evidence_insufficient": ("证据不足", "无法定论", "不能确诊", "不能下结论"),
    "info_request": ("补充", "需要", "检查", "采集", "信息"),
    "root_check": ("根部", "挖开", "检查"),
    "differential": ("排除", "区分", "鉴别", "优先", "还是"),
    "risk_priority": ("风险", "优先", "控制", "加重"),
    "delay_irrigation": ("暂缓", "推迟", "避免浇水", "不要浇水"),
    "irrigation_decision": ("浇水", "灌溉", "灌水", "水量"),
    "action_plan": ("步骤", "安排", "防治", "用药", "计划"),
    "quarantine": ("隔离", "相邻", "串水", "传播"),
}


class ChallengeScoringError(ValueError):
    """Raised when challenge scoring inputs violate the contract."""


def calc_confidence_calibration(
    agent_outputs: Sequence[Any],
    *,
    bins: int = ECE_BINS,
) -> float | None:
    """Expected Calibration Error over agent outputs.

    Each output must carry a numeric ``confidence`` and a correctness label,
    given either directly as ``correct`` (bool) or derived from
    ``expected`` + ``decision`` (substring containment, matching the
    Phase 3 accuracy convention). Outputs without a label are excluded from
    the estimate. Returns ``None`` when no labeled output remains; missing
    calibration data must not be interpreted as perfect calibration.

    Args:
        agent_outputs: sequence of dicts / dataclass-like outputs.
        bins: number of confidence bins (default 10).

    Returns:
        ECE in ``[0.0, 1.0]``, or ``None`` when no labeled output exists.
    """
    if bins < 1:
        raise ChallengeScoringError(f"bins must be >= 1, got {bins}")
    labeled: list[tuple[float, bool]] = []
    for out in agent_outputs:
        if not _has_correctness(out):
            continue
        confidence = float(_confidence(out))
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ChallengeScoringError(
                f"confidence must be finite and in [0,1], got {confidence!r}"
            )
        labeled.append((confidence, _correctness(out)))
    if not labeled:
        return None
    bin_size = 1.0 / bins
    bin_counts = [0] * bins
    bin_accs = [0.0] * bins
    bin_confs = [0.0] * bins
    for confidence, correct in labeled:
        index = min(bins - 1, int(confidence / bin_size))
        bin_counts[index] += 1
        bin_accs[index] += 1.0 if correct else 0.0
        bin_confs[index] += confidence
    total = len(labeled)
    error = 0.0
    for index in range(bins):
        count = bin_counts[index]
        if not count:
            continue
        acc = bin_accs[index] / count
        conf = bin_confs[index] / count
        error += (count / total) * abs(acc - conf)
    return round(error, 6)


def is_abstention(output: Any) -> bool:
    """Return whether an output semantically represents an abstention."""
    return _shared_is_abstention(output)


def normalize_decision_label(
    output: Any,
    *,
    known_labels: Sequence[str] = (),
) -> str:
    """Map one decision to ``ABSTAIN``, a known label, or a short fallback."""
    return _shared_normalize_decision_label(output, known_labels=known_labels)


def calc_abstention_rate(agent_outputs: Sequence[Any]) -> float | None:
    """Fraction of valid outputs that abstain instead of committing.

    An output abstains when its ``abstained`` flag is truthy or its
    ``decision`` / ``claim`` text matches the abstention vocabulary
    (``证据不足``, ``无法定论``, ...). Returns a percentage in
    ``[0.0, 100.0]``. Returns ``None`` when no output carries a decision
    text or explicit abstention flag; missing output is not "no abstention".
    """
    valid = [
        out
        for out in agent_outputs
        if _decision_text(out).strip()
        or (
            isinstance(out, Mapping)
            and out.get("abstained") is not None
        )
    ]
    if not valid:
        return None
    abstained = sum(1 for out in valid if _is_abstention(out))
    return round(100.0 * abstained / len(valid), 2)


def calc_factor_scores(
    agent_output: Any,
    expected_factors: Sequence[str],
    *,
    use_llm: bool = True,
) -> tuple[float, int]:
    """Coverage fraction plus its quantized 0-3 coherence in one judgment.

    Runs the coverage judgment exactly once (LLM with rule fallback) and
    returns ``(coverage_fraction, coherence)`` where the two values are
    derived from the same per-factor results, so callers aggregating both
    metrics never see internally inconsistent numbers.

    Args:
        agent_output: a single dict / dataclass-like output.
        expected_factors: non-empty list of factor names.
        use_llm: whether to attempt the LLM judge (default true).

    Returns:
        ``(coverage in [0.0, 1.0], coherence in [0, 3])``.
    """
    if not expected_factors:
        raise ChallengeScoringError(
            "expected_factors must be a non-empty sequence"
        )
    coverage = _factor_coverage(agent_output, expected_factors, use_llm=use_llm)
    covered = sum(1 for factor in expected_factors if coverage.get(factor, False))
    fraction = covered / len(expected_factors)
    return fraction, min(3, int(fraction * 3 + 0.5))


def calc_factor_coverage(
    agent_output: Any,
    expected_factors: Sequence[str],
    *,
    use_llm: bool = True,
) -> float:
    """Fraction of the expected key factors covered by the output.

    Uses the same coverage judgment as :func:`calc_reasoning_coherence`
    (LLM judge with rule fallback) but returns the raw fraction in
    ``[0.0, 1.0]`` instead of the quantized 0-3 score. This is the
    factor coverage fraction of one case. It is not a label-accuracy metric.

    Args:
        agent_output: a single dict / dataclass-like output.
        expected_factors: non-empty list of factor names.
        use_llm: whether to attempt the LLM judge (default true).

    Returns:
        Coverage fraction in ``[0.0, 1.0]``.
    """
    if not expected_factors:
        raise ChallengeScoringError(
            "expected_factors must be a non-empty sequence"
        )
    coverage = _factor_coverage(agent_output, expected_factors, use_llm=use_llm)
    covered = sum(1 for factor in expected_factors if coverage.get(factor, False))
    return covered / len(expected_factors)


def calc_reasoning_coherence(
    agent_output: Any,
    expected_factors: Sequence[str],
    *,
    use_llm: bool = True,
) -> int:
    """Legacy API: return the quantized factor-coverage level.

    Despite the historical name, this does not measure logical consistency.
    Coverage is judged factor-by-factor, then mapped to a 0-3 scale with
    round-half-up on ``3 * covered / len(factors)``:

    - 0: none of the factors are addressed;
    - 1: roughly the first third of the factors are covered;
    - 2: roughly two thirds covered;
    - 3: every factor is covered.

    When ``use_llm`` is true and ``DEEPSEEK_API_KEY`` is set, the judge runs
    :data:`DEFAULT_COHERENCE_MODEL` (override via ``AGRI_AI_COHERENCE_MODEL``
    or ``DEEPSEEK_MODEL``) asking for per-factor coverage. Any API failure
    falls back to the deterministic keyword rule over
    :data:`FACTOR_ALIASES`, so the function always returns a numeric score
    and never raises on model unavailability.

    Args:
        agent_output: a single dict / dataclass-like output whose
            ``decision`` / ``claim`` and reasoning text are inspected.
        expected_factors: non-empty list of factor names from the case's
            ``expected_key_factors``.
        use_llm: whether to attempt the LLM judge (default true).

    Returns:
        Coherence score in ``[0, 3]``.
    """
    if not expected_factors:
        raise ChallengeScoringError(
            "expected_factors must be a non-empty sequence"
        )
    coverage = _factor_coverage(agent_output, expected_factors, use_llm=use_llm)
    covered = sum(1 for factor in expected_factors if coverage.get(factor, False))
    fraction = covered / len(expected_factors)
    return min(3, int(fraction * 3 + 0.5))


def _factor_coverage(
    agent_output: Any,
    expected_factors: Sequence[str],
    *,
    use_llm: bool,
) -> dict[str, bool]:
    """Per-factor coverage of the final user-visible decision output.

    ``action_plan`` is a formal structured output field, so a non-empty action
    plan covers that factor without relying on keyword presence. Other factors
    are judged from decision, reasoning, and action-plan text.
    """
    output_text = _reasoning_text(agent_output)
    if use_llm and os.environ.get("DEEPSEEK_API_KEY", "").strip():
        try:
            coverage = _llm_factor_coverage(
                output_text, list(expected_factors)
            )
        except Exception:  # noqa: BLE001  fallback is the documented contract
            coverage = _rule_factor_coverage(output_text, expected_factors)
    else:
        coverage = _rule_factor_coverage(output_text, expected_factors)
    if "action_plan" in expected_factors:
        data = _as_dict(agent_output)
        action_plan = data.get("action_plan")
        coverage["action_plan"] = isinstance(action_plan, list) and any(
            isinstance(item, str) and item.strip() for item in action_plan
        )
    return coverage


# ---------------------------------------------------------------------------
# output normalization
# ---------------------------------------------------------------------------


def _as_dict(output: Any) -> dict[str, Any]:
    if isinstance(output, Mapping):
        return dict(output)
    return {
        key: getattr(output, key)
        for key in (
            "decision",
            "claim",
            "confidence",
            "correct",
            "expected",
            "abstained",
            "reasoning_trace",
            "summary",
            "action_plan",
        )
        if hasattr(output, key)
    }


def _decision_text(output: Any) -> str:
    return _shared_decision_text(output)


def _reasoning_text(output: Any) -> str:
    data = _as_dict(output)
    decision = _decision_text(output)
    reasoning = str(
        data.get("reasoning_trace") or data.get("summary") or ""
    )
    action_plan = data.get("action_plan")
    action_text = (
        " ".join(str(item) for item in action_plan if str(item).strip())
        if isinstance(action_plan, list)
        else ""
    )
    return f"{decision} {reasoning} {action_text}".strip()


def _confidence(output: Any) -> float:
    data = _as_dict(output)
    value = data.get("confidence")
    if value is None:
        raise ChallengeScoringError(
            f"output {_decision_text(output)!r} has no confidence"
        )
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ChallengeScoringError(
            f"output {_decision_text(output)!r} has non-numeric confidence "
            f"{value!r}"
        ) from None


def _has_correctness(output: Any) -> bool:
    data = _as_dict(output)
    if data.get("correct") is not None:
        return True
    return bool(data.get("expected")) and bool(_decision_text(output))


def _correctness(output: Any) -> bool:
    """Correctness using the canonical final-decision semantics."""
    data = _as_dict(output)
    explicit = data.get("correct")
    if explicit is not None:
        return bool(explicit)
    return _decision_correctness(data.get("expected"), output)


def _is_abstention(output: Any) -> bool:
    return _shared_is_abstention(output)


# ---------------------------------------------------------------------------
# factor coverage
# ---------------------------------------------------------------------------


def _rule_factor_coverage(
    text: str,
    expected_factors: Sequence[str],
) -> dict[str, bool]:
    """Deterministic coverage: a factor is covered when any of its Chinese
    aliases or its snake-case name (with ``_`` collapsed) appears in the
    output text."""
    coverage: dict[str, bool] = {}
    for factor in expected_factors:
        tokens = FACTOR_ALIASES.get(factor, ())
        name_hits = factor.replace("_", "") in text.replace("_", "")
        coverage[factor] = any(token in text for token in tokens) or name_hits
    return coverage


def _llm_factor_coverage(
    text: str,
    expected_factors: list[str],
) -> dict[str, bool]:
    """Coverage via the existing deepseek-v4-flash model (OpenAI-compatible
    gateway). Raises on any failure so the caller can fall back to rules."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ChallengeScoringError("DEEPSEEK_API_KEY is not set")
    from openai import OpenAI

    model = (
        os.environ.get("AGRI_AI_COHERENCE_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or DEFAULT_COHERENCE_MODEL
    )
    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        ),
    )
    payload = {
        "agent_output": text,
        "expected_factors": expected_factors,
        "output_schema": {
            "factor_coverage": {
                factor: "true/false - 输出是否覆盖/讨论了该关键因子"
                for factor in expected_factors
            },
            "note": "覆盖指输出显式讨论该因子（包括显式排除或说明其缺失），不指该因子在输出中恰好出现文字",
        },
    }
    system = (
        "你是农业诊断评测员。给定 Agent 输出与期望关键因子列表，逐因子判断输出"
        "是否覆盖了该因子（显式讨论、引用或排除均算覆盖）。只输出 JSON。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(resp.choices[0].message.content or "{}")
    raw = parsed.get("factor_coverage") or {}
    coverage: dict[str, bool] = {}
    for factor in expected_factors:
        value = raw.get(factor)
        coverage[factor] = (
            value is True
            or (
                isinstance(value, str)
                and value.strip().lower() in {"true", "yes", "1", "是"}
            )
        )
    return coverage


__all__ = [
    "DEFAULT_COHERENCE_MODEL",
    "ECE_BINS",
    "FACTOR_ALIASES",
    "VALID_GROUPS",
    "ChallengeScoringError",
    "calc_abstention_rate",
    "calc_confidence_calibration",
    "calc_factor_coverage",
    "calc_factor_scores",
    "calc_reasoning_coherence",
    "is_abstention",
    "normalize_decision_label",
]
