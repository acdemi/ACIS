"""Lightweight smoke evaluation for the Agri AI orchestrator.

Run from agri-ai/:
    python evals/smoke_eval.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("AGRI_AI_DB_PATH", str(ROOT / "data" / "eval.db"))

from orchestrator import AgentOrchestrator, DecisionOutput


SCENARIOS = [
    "温室A番茄叶片黄斑，叶背有灰色霉层，如何处理？",
    "温室A番茄今天需要浇水吗？如果有病害风险要一起考虑",
    "温室B黄瓜当前有什么风险，需要优先处理什么？",
]


def assert_decision_shape(decision: DecisionOutput) -> None:
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
    rag_trace = next((trace for trace in decision.traces if trace.agent == "RAG"), None)
    assert rag_trace is not None, "RAG trace should be present"
    assert rag_trace.evidence.get("backend") in {"memory", "qdrant", "fallback"}, "RAG backend should be explicit"
    kg_block = decision.judge_analysis.get("kg", {})
    assert kg_block.get("backend") in {"memory", "neo4j", "fallback"}, "KG backend should be explicit"


def run_suite(use_langgraph: bool, use_llm_judge: bool = False) -> None:
    orchestrator = AgentOrchestrator(
        use_langgraph=use_langgraph,
        use_llm_judge=use_llm_judge,
    )
    mode = "langgraph" if use_langgraph else "rules"
    if use_llm_judge:
        mode += "+llm-judge"

    print(f"\n[{mode}]")
    for query in SCENARIOS:
        decision = orchestrator.run(query)
        assert_decision_shape(decision)
        print(f"- {decision.risk_level:6s} | {decision.judge_mode:8s} | {decision.decision}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agri AI orchestrator smoke evaluation")
    parser.add_argument(
        "--with-deepseek",
        action="store_true",
        help="also call the real DeepSeek Judge when DEEPSEEK_API_KEY is set",
    )
    args = parser.parse_args()

    run_suite(use_langgraph=False)
    run_suite(use_langgraph=True)

    original_api_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        run_suite(use_langgraph=True, use_llm_judge=True)
    finally:
        if original_api_key is not None:
            os.environ["DEEPSEEK_API_KEY"] = original_api_key

    if args.with_deepseek:
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise SystemExit("--with-deepseek requires DEEPSEEK_API_KEY")
        run_suite(use_langgraph=True, use_llm_judge=True)

    print("\nsmoke eval passed")


if __name__ == "__main__":
    main()
