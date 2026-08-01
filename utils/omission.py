"""Collective Omission Detection helpers (Phase 7A Sprint 02).

Pure functions that turn the Judge's existing collective-omission detection
(KG candidate diseases never discussed by any expert) into a structured,
score-based cognitive-blind-spot signal.

These helpers do NOT retrieve the KG and do NOT depend on the Judge; they
operate on the candidate list and the already-computed ignored list, keeping
complexity O(n).
"""
from __future__ import annotations

from typing import Any

# Behavior thresholds per the Phase 7A Sprint 02 spec.
WARN_THRESHOLD = 0.20
PENALTY_THRESHOLD = 0.50
PENALTY_STEP = 0.05
PENALTY_MAX = 0.10
CONFIDENCE_FLOOR = 0.50


def omission_score(ignored_count: int, retrieved_candidate_count: int) -> float:
    """Return ignored_count / retrieved_candidate_count, clamped to [0, 1].

    A retrieval that returns zero candidates yields 0.0: nothing was ignored,
    so there is no blind spot to score.
    """
    if retrieved_candidate_count <= 0:
        return 0.0
    ratio = ignored_count / retrieved_candidate_count
    return round(min(1.0, max(0.0, ratio)), 4)


def omission_reason(ignored_candidates: list[str]) -> str:
    """Natural-language explanation of the collective blind spot."""
    if not ignored_candidates:
        return "所有 KG 候选病害均已被专家讨论，未发现集体漏检。"
    names = "、".join(ignored_candidates)
    return f"{names} 已从知识图谱检索到，但未被任何专家考虑。"


def omission_action(score: float) -> dict[str, Any]:
    """Map an omission_score to the spec's three-band behavior.

    Returns a dict with:
      - level: "none" | "warn" | "penalize"
      - confidence_delta: non-negative amount to subtract from final confidence
      - append_warning: whether the Judge should append a warning
    """
    if score > PENALTY_THRESHOLD:
        return {"level": "penalize", "confidence_delta": PENALTY_STEP, "append_warning": True}
    if score >= WARN_THRESHOLD:
        return {"level": "warn", "confidence_delta": 0.0, "append_warning": True}
    return {"level": "none", "confidence_delta": 0.0, "append_warning": False}


def apply_omission_penalty(confidence: float, score: float, *, already_applied: float = 0.0) -> float:
    """Apply the score-based confidence penalty with cap and floor.

    Only the ``penalize`` band (score > 0.50) reduces confidence, by
    ``PENALTY_STEP`` (0.05). The cumulative omission penalty never exceeds
    ``PENALTY_MAX`` (0.10) and confidence is never reduced below
    ``CONFIDENCE_FLOOR`` (0.50).
    """
    action = omission_action(score)
    delta = action["confidence_delta"]
    if delta <= 0.0:
        return round(confidence, 2)
    remaining = max(0.0, PENALTY_MAX - already_applied)
    delta = min(delta, remaining)
    if delta <= 0.0:
        return round(confidence, 2)
    return round(max(CONFIDENCE_FLOOR, confidence - delta), 2)