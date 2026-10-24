"""CLI output must survive narrow console encodings (Windows GBK/ASCII)."""
from __future__ import annotations

import io
import sys

import orchestrator


def _narrow_stdout(encoding: str):
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding=encoding, newline="")
    return buffer, stream


def test_print_safe_degrades_on_narrow_console(monkeypatch):
    """U+26A0 cannot be encoded as ASCII; printing must not raise."""
    buffer, stream = _narrow_stdout("ascii")
    monkeypatch.setattr(sys, "stdout", stream)

    orchestrator._print_safe("Cornerspot ⚠ confidence 0.72")

    stream.flush()
    printed = buffer.getvalue().decode("ascii")
    assert "0.72" in printed
    assert "\u26a0" not in printed


def test_print_safe_keeps_text_on_utf8_console(monkeypatch):
    buffer, stream = _narrow_stdout("utf-8")
    monkeypatch.setattr(sys, "stdout", stream)

    orchestrator._print_safe("Cornerspot ⚠ confidence 0.72")

    stream.flush()
    printed = buffer.getvalue().decode("utf-8")
    assert "\u26a0" in printed
    assert "0.72" in printed


def test_format_decision_output_is_printable_on_narrow_console(monkeypatch):
    """A decision whose text carries unencodable symbols must still print."""
    from agents.types import DebateResult, DecisionOutput

    debate = DebateResult(consensus=["规则路径一致"], conflicts=[], missing_evidence=[], risk_level="low")
    decision = DecisionOutput(
        summary="summary with symbol ⚠",
        decision="番茄叶霉病",
        confidence=0.72,
        risk_level="low",
        action_plan=["检查通风"],
        debate=debate,
        traces=[],
        judge_mode="rules",
        need_human_review=False,
        reasoning_trace="trace ⚠",
        judge_analysis={},
    )
    rendered = orchestrator.format_decision(decision)
    buffer, stream = _narrow_stdout("ascii")
    monkeypatch.setattr(sys, "stdout", stream)

    orchestrator._print_safe(rendered)

    stream.flush()
    printed = buffer.getvalue().decode("ascii")
    assert "0.72" in rendered or "72%" in rendered
    assert printed.strip()
