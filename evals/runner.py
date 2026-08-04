"""Reproducible Evaluation Runner (Phase 2.1E, Sprint 02).

Executes a benchmark dataset through the orchestrator, collects the unified
Trace for each case, computes metrics, and writes ``metrics.csv`` plus
``summary.md`` under the configured output directory.

Phase 2.1E, Sprint 03: adds ``--save-traces`` (default off) which persists
each case's unified Trace to ``<output-dir>/traces/{trace_id}.json`` via the
frozen trace exporter, and accepts benchmark module-style dataset names
(``benchmarks.datasets.easy`` ...).

Phase 2.1E, Sprint 04: adds independent ``--critic-on/--critic-off`` and
``--counterfactual-on/--counterfactual-off`` toggles so the ablation runner
can quantify each cognitive module's contribution. With ``--debate-off`` the
critic now stays on unless ``--critic-off`` is given; with
``--counterfactual-off`` every agent's counterfactual fields are stripped
before the debate, critic, judge, or Trace sees them.

Usage from the repo root::

    python evals/runner.py --dataset evals.fixtures
    python evals/runner.py --dataset benchmarks.datasets.easy --save-traces

Toggles are honored without touching frozen modules: planner uses the
existing ``ACIS_ENABLE_PLANNER`` env switch, tool_router is disabled by
clearing the orchestrator's instance attribute, and memory/debate are disabled
by substituting duck-typed no-op engines at runtime.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trace import Trace, export_trace_json

from agents.types import AgentOutput, DebateResult
from benchmarks.loader import CAPABILITY_SUITES, suite_dataset_path
from evals.capability_metrics import compute_capability_scores
from evals.config import EvalCase, EvalConfig, load_dataset
from evals.metrics import (
    CaseMetrics,
    aggregate_metrics,
    compute_trace_metrics,
)
from evals.report import write_metrics_csv, write_summary_markdown
from orchestrator import AgentOrchestrator
from rule_engine import sensor_anomaly


class _NoopAgent:
    """Duck-typed memory agent used when ``memory_on=False``."""

    def __init__(self, layer: str, name: str) -> None:
        self.layer = layer
        self.name = name

    def run(self, context: Any, *args: Any, **kwargs: Any) -> AgentOutput:
        return AgentOutput(
            layer=self.layer,
            agent=self.name,
            claim=f"{self.name} 已由评估配置关闭（memory_on=False）",
            confidence=0.0,
        )


class _NoopDebateEngine:
    """Duck-typed debate engine used when ``debate_on=False``."""

    def run(self, outputs: Any, context: Any = None, **kwargs: Any) -> DebateResult:
        return DebateResult(
            consensus=[],
            conflicts=[],
            missing_evidence=[],
            risk_level="low",
            critic={},
        )


class _NoopCriticEngine:
    """Duck-typed critic engine used when ``critic_on=False``."""

    def run(
        self,
        context: Any,
        outputs: list[AgentOutput],
        debate: DebateResult,
    ) -> tuple[list[AgentOutput], DebateResult]:
        return outputs, debate


class _CounterfactualFreeAgent:
    """Duck-typed agent wrapper that strips counterfactual fields.

    Wraps a real agent and clears ``counterfactual`` /
    ``counterfactual_observations`` from its ``AgentOutput`` so the debate,
    critic, judge, and Trace never see counterfactual reasoning. No frozen
    module is modified; the substitution is instance-level only.
    """

    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def run(self, context: Any, *args: Any, **kwargs: Any) -> AgentOutput:
        output = self._agent.run(context, *args, **kwargs)
        if isinstance(output, AgentOutput):
            output.counterfactual = {}
            output.counterfactual_observations = []
        return output


#: Orchestrator agent attributes that can carry counterfactual reasoning.
_AGENT_ATTRIBUTES = (
    "vision_agent",
    "sensor_agent",
    "weather_agent",
    "rag_agent",
    "knowledge_graph_agent",
    "case_memory_agent",
    "outcome_agent",
    "pathology_agent",
    "meteorology_agent",
    "cultivation_agent",
    "economic_agent",
    "ecology_agent",
)


@dataclass(frozen=True)
class EvaluationResult:
    """Output of a completed evaluation run."""

    config: EvalConfig
    cases: list[EvalCase]
    rows: list[CaseMetrics]
    aggregate: dict[str, float | int | None]
    csv_path: Path
    summary_path: Path
    trace_dir: Path | None = None


def run_evaluation(config: EvalConfig) -> EvaluationResult:
    """Run the dataset, collect Traces, compute metrics, write reports."""
    _configure_environment(config)
    cases = load_dataset(config.dataset)
    if config.max_cases is not None:
        cases = cases[: config.max_cases]

    random.seed(config.seed)
    orchestrator = AgentOrchestrator(use_langgraph=config.use_langgraph)
    _apply_toggles(orchestrator, config)
    _warm_up(orchestrator)  # 吸收冷启动，保证 runtime 指标是稳态值

    rows: list[CaseMetrics] = []
    traces: list[Trace] = []
    for case in cases:
        row, trace = _run_case(orchestrator, config, case)
        rows.append(row)
        traces.append(trace)
    aggregate = aggregate_metrics(rows)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "metrics.csv"
    summary_path = output_dir / "summary.md"
    write_metrics_csv(rows, aggregate, csv_path)
    write_summary_markdown(aggregate, config, rows, summary_path)
    trace_dir = _write_trace_files(traces, output_dir) if config.save_traces else None
    return EvaluationResult(
        config=config,
        cases=cases,
        rows=rows,
        aggregate=aggregate,
        csv_path=csv_path,
        summary_path=summary_path,
        trace_dir=trace_dir,
    )


def _configure_environment(config: EvalConfig) -> None:
    """Set the environment switches the orchestrator already understands."""
    os.environ.setdefault("AGRI_AI_DB_PATH", str(ROOT / "data" / "eval.db"))
    os.environ["AGRI_AI_PERSIST"] = "1" if config.persist else "0"
    if config.planner_on:
        os.environ["ACIS_ENABLE_PLANNER"] = "true"
    else:
        os.environ.pop("ACIS_ENABLE_PLANNER", None)


def _warm_up(orchestrator: AgentOrchestrator) -> None:
    """Run one untimed query to absorb one-time lazy imports / backend init."""
    orchestrator.run("温室A番茄今天状态怎么样")


def _run_case(
    orchestrator: AgentOrchestrator,
    config: EvalConfig,
    case: EvalCase,
) -> tuple[CaseMetrics, Trace]:
    if case.sensor_override is not None:
        sensor_anomaly.ANOMALIES["gh-a"] = dict(case.sensor_override)
    try:
        random.seed(config.seed)  # 固定传感器/天气随机序列，保证可复现
        started = time.perf_counter()
        orchestrator.run(case.query)
        runtime = time.perf_counter() - started
        trace = orchestrator.last_trace
        if trace is None:
            raise RuntimeError(f"case {case.id}: orchestrator produced no Trace")
        capability_scores = compute_capability_scores(trace, case)
        metrics = compute_trace_metrics(
            trace,
            case_id=case.id,
            runtime_seconds=runtime,
            expected=case.ground_truth,
            debate_on=config.debate_on,
            capability_scores=capability_scores,
        )
        return metrics, trace
    finally:
        sensor_anomaly.ANOMALIES.pop("gh-a", None)


def _write_trace_files(traces: list[Trace], output_dir: Path) -> Path:
    """Persist each case's unified Trace as JSON under ``output_dir/traces``."""
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for trace in traces:
        (trace_dir / f"{trace.trace_id}.json").write_text(
            export_trace_json(trace),
            encoding="utf-8",
        )
    return trace_dir


def _apply_toggles(orchestrator: AgentOrchestrator, config: EvalConfig) -> None:
    """Honor the subsystem toggles via instance-level substitution only.

    Frozen modules (Planner, Judge, Debate, Tool Router, Memory) are not
    modified and the orchestrator API is unchanged.
    """
    if not config.tool_router_on:
        orchestrator.tool_router = None
    if not config.memory_on:
        _set_noop(orchestrator, "rag_agent", "RAG")
        _set_noop(orchestrator, "knowledge_graph_agent", "知识图谱Agent")
        _set_noop(orchestrator, "case_memory_agent", "历史案例Agent")
        _set_noop(orchestrator, "outcome_agent", "经验回放Agent")
    if not config.debate_on:
        setattr(orchestrator, "debate_engine", _NoopDebateEngine())  # noqa: B010
    if not config.critic_on:
        setattr(orchestrator, "critic_engine", _NoopCriticEngine())  # noqa: B010
    if not config.counterfactual_on:
        _disable_counterfactual(orchestrator)


def _set_noop(orchestrator: AgentOrchestrator, attr: str, name: str) -> None:
    setattr(orchestrator, attr, _NoopAgent("记忆层", name))


def _disable_counterfactual(orchestrator: AgentOrchestrator) -> None:
    """Wrap every agent so counterfactual reasoning never reaches the Trace."""
    for attr in _AGENT_ATTRIBUTES:
        agent = getattr(orchestrator, attr, None)
        if agent is not None:
            setattr(orchestrator, attr, _CounterfactualFreeAgent(agent))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _add_toggle(parser: argparse.ArgumentParser, name: str, default: bool) -> None:
    flag = name.replace("_", "-")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{flag}-on",
        dest=f"{name}_on",
        action="store_true",
        default=default,
    )
    group.add_argument(
        f"--{flag}-off",
        dest=f"{name}_on",
        action="store_false",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ACIS Evaluation Runner (Phase 2.1E, Sprint 02)"
    )
    parser.add_argument(
        "--dataset",
        default=EvalConfig.dataset,
        help="dataset module path (default: evals.fixtures) or .json file",
    )
    parser.add_argument(
        "--suite",
        choices=(*CAPABILITY_SUITES, "all"),
        default=None,
        help="run a capability suite (planning/memory/debate/counterfactual/"
        "adversarial) instead of --dataset; 'all' runs every suite",
    )
    _add_toggle(parser, "planner", True)
    _add_toggle(parser, "debate", True)
    _add_toggle(parser, "critic", True)
    _add_toggle(parser, "memory", True)
    _add_toggle(parser, "tool_router", True)
    _add_toggle(parser, "counterfactual", True)
    parser.add_argument("--output-dir", default=EvalConfig.output_dir)
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="use the rules orchestration path instead of LangGraph",
    )
    parser.add_argument("--seed", type=int, default=EvalConfig.seed)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument(
        "--save-traces",
        action="store_true",
        help="save each case Trace to <output-dir>/traces/{trace_id}.json",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> EvalConfig:
    dataset = (
        str(suite_dataset_path(args.suite))
        if args.suite and args.suite != "all"
        else args.dataset
    )
    return EvalConfig(
        dataset=dataset,
        planner_on=args.planner_on,
        debate_on=args.debate_on,
        critic_on=args.critic_on,
        memory_on=args.memory_on,
        tool_router_on=args.tool_router_on,
        counterfactual_on=args.counterfactual_on,
        output_dir=args.output_dir,
        use_langgraph=not args.rules_only,
        seed=args.seed,
        max_cases=args.max_cases,
        save_traces=args.save_traces,
    )


def _report_run(result: EvaluationResult) -> None:
    print(f"evaluation complete: {len(result.rows)} cases")
    print(f"  accuracy={result.aggregate.get('accuracy')}")
    print(f"  metrics.csv: {result.csv_path}")
    print(f"  summary.md:  {result.summary_path}")
    if result.trace_dir is not None:
        print(f"  traces:      {result.trace_dir} ({len(result.rows)} files)")


def main() -> None:
    args = build_parser().parse_args()
    if args.suite == "all":
        base = config_from_args(args)
        for suite in CAPABILITY_SUITES:
            config = replace(
                base,
                dataset=str(suite_dataset_path(suite)),
                output_dir=str(Path(args.output_dir) / "suites" / suite),
            )
            _report_run(run_evaluation(config))
        return
    _report_run(run_evaluation(config_from_args(args)))


if __name__ == "__main__":
    main()




