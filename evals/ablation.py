"""Ablation runner (Phase 2.1E, Sprint 04).

Quantifies each cognitive module's marginal contribution by running the
evaluation runner over a fixed set of module toggle combinations and
comparing every combo's metrics against the ``all_on`` baseline. Per-combo
``metrics.csv`` files are written under
``results/ablation/<timestamp>/<combo_name>/`` and a comparison report
(configuration matrix, absolute metrics, contribution matrix, normalized
radar data, findings, recommendations) is written to
``results/ablation/<timestamp>/REPORT.md``.

Usage from the repo root::

    python evals/ablation.py --dataset benchmarks.datasets.easy
    python evals/ablation.py --dataset evals.fixtures --combo all_on --combo no_memory

The runner itself is reused unchanged: each combo maps onto an
:class:`evals.config.EvalConfig` and is executed by
:func:`evals.runner.run_evaluation`, so toggles, warm-up, metrics, and
reporting stay identical across arms.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.loader import CAPABILITY_SUITES, suite_dataset_path
from evals.config import AblationConfig, EvalConfig
from evals.report import AblationResult, write_ablation_report
from evals.runner import run_evaluation


@dataclass(frozen=True)
class AblationCombo:
    """A named module toggle combination for one ablation arm."""

    name: str
    description: str
    planner_on: bool = True
    debate_on: bool = True
    critic_on: bool = True
    memory_on: bool = True
    tool_router_on: bool = True
    counterfactual_on: bool = True

    def toggles(self) -> dict[str, bool]:
        return {
            "planner_on": self.planner_on,
            "debate_on": self.debate_on,
            "critic_on": self.critic_on,
            "memory_on": self.memory_on,
            "tool_router_on": self.tool_router_on,
            "counterfactual_on": self.counterfactual_on,
        }


#: All ablation arms. ``all_on`` is the baseline every combo is compared to.
ABLATION_COMBOS: tuple[AblationCombo, ...] = (
    AblationCombo(
        name="all_on",
        description="全开基线：所有认知模块启用",
    ),
    AblationCombo(
        name="no_planner",
        description="关闭 Planner（任务规划）",
        planner_on=False,
    ),
    AblationCombo(
        name="no_debate",
        description="关闭 Debate 与多轮辩论，保留 Critic",
        debate_on=False,
    ),
    AblationCombo(
        name="no_memory",
        description="关闭 RAG/KG/案例记忆",
        memory_on=False,
    ),
    AblationCombo(
        name="no_counterfactual",
        description="移除所有反事实推理",
        counterfactual_on=False,
    ),
    AblationCombo(
        name="no_tool_router",
        description="关闭 Tool Router（工具路由）",
        tool_router_on=False,
    ),
    AblationCombo(
        name="no_critic",
        description="关闭 Critic（反驳降权）",
        critic_on=False,
    ),
)

#: Combos required by the sprint deliverable (the rest are optional arms).
REQUIRED_COMBOS: tuple[str, ...] = (
    "all_on",
    "no_planner",
    "no_debate",
    "no_memory",
    "no_counterfactual",
)

_COMBOS_BY_NAME: dict[str, AblationCombo] = {
    combo.name: combo for combo in ABLATION_COMBOS
}


def combo_names() -> tuple[str, ...]:
    """All combo names in definition order."""
    return tuple(combo.name for combo in ABLATION_COMBOS)


def get_combo(name: str) -> AblationCombo:
    """Look up an ablation combo by name."""
    try:
        return _COMBOS_BY_NAME[name]
    except KeyError:
        raise ValueError(
            f"unknown ablation combo {name!r}; expected one of {combo_names()}"
        ) from None


def resolve_combos(names: Sequence[str] | None) -> tuple[AblationCombo, ...]:
    """Resolve selected names (or every combo when ``names`` is empty)."""
    if not names:
        return ABLATION_COMBOS
    return tuple(get_combo(name) for name in names)


def combo_config(
    combo: AblationCombo,
    *,
    dataset: str,
    output_dir: str | Path,
    seed: int,
    max_cases: int | None = None,
    use_langgraph: bool = True,
) -> EvalConfig:
    """Map an ablation combo onto the EvalConfig the runner understands."""
    return EvalConfig(
        dataset=dataset,
        output_dir=str(output_dir),
        planner_on=combo.planner_on,
        debate_on=combo.debate_on,
        critic_on=combo.critic_on,
        memory_on=combo.memory_on,
        tool_router_on=combo.tool_router_on,
        counterfactual_on=combo.counterfactual_on,
        seed=seed,
        max_cases=max_cases,
        use_langgraph=use_langgraph,
    )


@dataclass(frozen=True)
class AblationRunResult:
    """Outcome of a full ablation run."""

    run_dir: Path
    report_path: Path
    combo_results: list[AblationResult]


def run_ablation(config: AblationConfig) -> AblationRunResult:
    """Run every selected combo and write per-combo metrics plus REPORT.md."""
    run_dir = Path(config.output_dir) / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    combos = resolve_combos(config.combos)
    combo_results: list[AblationResult] = []
    for combo in combos:
        combo_dir = run_dir / combo.name
        eval_config = combo_config(
            combo,
            dataset=config.dataset,
            output_dir=combo_dir,
            seed=config.seed,
            max_cases=config.max_cases,
            use_langgraph=config.use_langgraph,
        )
        result = run_evaluation(eval_config)
        combo_results.append(
            AblationResult(
                combo_name=combo.name,
                description=combo.description,
                toggles=combo.toggles(),
                aggregate=result.aggregate,
                rows=result.rows,
                combo_dir=combo_dir,
            )
        )
    report_path = write_ablation_report(
        combo_results,
        run_dir,
        dataset=config.dataset,
    )
    return AblationRunResult(
        run_dir=run_dir,
        report_path=report_path,
        combo_results=combo_results,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ACIS Ablation Runner (Phase 2.1E, Sprint 04)"
    )
    parser.add_argument(
        "--dataset",
        default=AblationConfig.dataset,
        help="dataset module path or .json file (default: evals.fixtures)",
    )
    parser.add_argument(
        "--suite",
        choices=(*CAPABILITY_SUITES, "all"),
        default=None,
        help="run ablation over a capability suite (planning/memory/debate/"
        "counterfactual/adversarial) instead of --dataset; 'all' runs every suite",
    )
    parser.add_argument(
        "--output-dir",
        default=AblationConfig.output_dir,
        help="ablation output root (default: results/ablation)",
    )
    parser.add_argument("--seed", type=int, default=AblationConfig.seed)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="use the rules orchestration path instead of LangGraph",
    )
    parser.add_argument(
        "--combo",
        action="append",
        default=None,
        choices=combo_names(),
        help="run only these combos (repeatable; default: all)",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> AblationConfig:
    dataset = (
        str(suite_dataset_path(args.suite))
        if args.suite and args.suite != "all"
        else args.dataset
    )
    return AblationConfig(
        dataset=dataset,
        output_dir=args.output_dir,
        seed=args.seed,
        max_cases=args.max_cases,
        use_langgraph=not args.rules_only,
        combos=tuple(args.combo) if args.combo else (),
    )


def _report_run(result: AblationRunResult) -> None:
    print(f"ablation complete: {len(result.combo_results)} combos")
    print(f"  run_dir: {result.run_dir}")
    print(f"  report:  {result.report_path}")
    for combo_result in result.combo_results:
        print(
            f"    {combo_result.combo_name}: "
            f"accuracy={combo_result.aggregate.get('accuracy')}"
        )


def main() -> None:
    args = build_parser().parse_args()
    if args.suite == "all":
        for suite in CAPABILITY_SUITES:
            config = replace(
                config_from_args(args),
                dataset=str(suite_dataset_path(suite)),
                output_dir=str(Path(args.output_dir) / "suites" / suite),
            )
            _report_run(run_ablation(config))
        return
    _report_run(run_ablation(config_from_args(args)))


if __name__ == "__main__":
    main()


