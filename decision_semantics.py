"""Canonical decision-label, abstention, and correctness semantics.

This module is intentionally small and dependency-free.  Evaluation metrics,
the challenge scorer, and Phase 4 adapters all use the same definitions:

* an abstention is a decision status, never a disease label;
* a committed diagnosis is compared to the expected label by containment;
* an expected abstention is correct exactly when the final decision abstains;
* confidence is always confidence in the final decision, not in an expert's
  intermediate claim.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_ABSTENTION_PATTERN = re.compile(
    r"证据不足|无法定论|不能确诊|不能下结论|难以判断|待采集|继续采集|不确定|ABSTAIN",
    re.IGNORECASE,
)


def decision_text(output: Any) -> str:
    """Extract the final decision/claim text from an output object."""
    if isinstance(output, str):
        return output
    if isinstance(output, Mapping):
        return str(output.get("decision") or output.get("claim") or "")
    return str(getattr(output, "decision", None) or getattr(output, "claim", None) or "")


def is_abstention(output: Any) -> bool:
    """Return true when an output semantically abstains from diagnosis."""
    explicit = (
        output.get("abstained")
        if isinstance(output, Mapping)
        else getattr(output, "abstained", False)
    )
    if explicit:
        return True
    return bool(_ABSTENTION_PATTERN.search(decision_text(output)))


def normalize_decision_label(
    output: Any,
    *,
    known_labels: Sequence[str] = (),
) -> str:
    """Map a decision to ``ABSTAIN``, a known label, or a short fallback."""
    if is_abstention(output):
        return "ABSTAIN"
    text = decision_text(output)
    for label in sorted(known_labels, key=len, reverse=True):
        if label and label in text:
            return label
    return text.strip()[:40] or "EMPTY"


def decision_correctness(expected: str | None, output: Any) -> bool:
    """Evaluate the final decision against the benchmark label contract."""
    if expected is None:
        return False
    expected_text = str(expected).strip()
    abstained = is_abstention(output)
    if expected_text in {"证据不足", "ABSTAIN"}:
        return abstained
    if abstained:
        return False
    return expected_text in decision_text(output)


__all__ = [
    "decision_correctness",
    "decision_text",
    "is_abstention",
    "normalize_decision_label",
]
