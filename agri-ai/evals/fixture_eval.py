"""Run the fixed fixture set through the orchestrator and assert invariants.

Run from agri-ai/:
    python evals/fixture_eval.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
os.environ.setdefault("AGRI_AI_DB_PATH", str(ROOT / "data" / "eval.db"))

from orchestrator import AgentOrchestrator, build_context
from rule_engine import sensor_anomaly
from evals.fixtures import FIXTURES


def assert_decision_shape(decision) -> None:
    assert decision.summary, "summary should not be empty"
    assert decision.decision, "decision should not be empty"
    assert 0.0 <= decision.confidence <= 1.0, "confidence should be normalized"
    assert decision.risk_level in {"low", "medium", "high"}, "risk_level should be bounded"
    assert decision.action_plan, "action_plan should not be empty"
    assert decision.traces, "traces should include agent outputs"
    assert decision.judge_mode in {"rules", "deepseek"}, "judge_mode should be explicit"
    assert isinstance(decision.need_human_review, bool), "need_human_review should be bool"
    assert decision.reasoning_trace, "reasoning_trace should not be empty"
    assert "kg" in decision.judge_analysis, "judge_analysis should include kg reference"
    kg = decision.judge_analysis.get("kg", {})
    assert kg.get("backend") in {"memory", "neo4j", "fallback"}, "KG backend should be explicit"
    assert isinstance(decision.debate.critic, dict), "DebateResult.critic should always be a dict"


def run_fixture(orchestrator: AgentOrchestrator, fx: dict) -> None:
    ctx = build_context(fx["query"])
    assert ctx.crop == fx["crop"], f"{fx['id']}: crop {ctx.crop!r} != {fx['crop']!r}"
    assert ctx.intent == fx["intent"], f"{fx['id']}: intent {ctx.intent!r} != {fx['intent']!r}"

    if fx.get("sensor_override"):
        sensor_anomaly.ANOMALIES["gh-a"] = fx["sensor_override"]
    try:
        random.seed(7)  # 固定随机种子，保证灌溉/天气判断可复现
        decision = orchestrator.run(fx["query"])
    finally:
        sensor_anomaly.ANOMALIES.pop("gh-a", None)
    assert_decision_shape(decision)

    pathology = next((t for t in decision.traces if t.agent == "病理Agent"), None)
    assert pathology is not None, f"{fx['id']}: missing pathology trace"

    expected = fx.get("disease")
    if expected == "证据不足":
        assert "病理证据不足" in pathology.claim, f"{fx['id']}: expected 证据不足, got {pathology.claim!r}"
    elif expected:
        assert expected in pathology.claim, f"{fx['id']}: expected {expected!r} in claim, got {pathology.claim!r}"
        kg_diseases = decision.judge_analysis.get("kg", {}).get("diseases", [])
        assert any(expected in d for d in kg_diseases), f"{fx['id']}: {expected!r} not in kg.diseases {kg_diseases}"

    # If the debate produced conflicts, the Critic rebuttal round must have run.
    if decision.debate.conflicts:
        assert decision.debate.critic.get("triggered"), f"{fx['id']}: conflicts present but critic not triggered"
    if "expect_critic" in fx:
        triggered = bool(decision.debate.critic.get("triggered"))
        assert triggered == fx["expect_critic"], f"{fx['id']}: critic={triggered} != expect_critic={fx['expect_critic']}"

    print(
        f"- [ok] {fx['id']:30s} crop={ctx.crop:8s} intent={ctx.intent:8s} "
        f"risk={decision.risk_level:6s} critic={'on' if decision.debate.critic.get('triggered') else 'off'} | {pathology.claim}"
    )


def main() -> None:
    orchestrator = AgentOrchestrator(use_langgraph=True)
    print(f"running {len(FIXTURES)} fixtures (langgraph + critic)...")
    for fx in FIXTURES:
        run_fixture(orchestrator, fx)
    print(f"\nfixture eval passed ({len(FIXTURES)} scenarios)")


if __name__ == "__main__":
    main()
