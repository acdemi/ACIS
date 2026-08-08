"""Runner adapter (Phase 2.1E, Sprint 05).

Isolates the Experiment Manager from the frozen evaluation runner/ablation
framework. Maps an :class:`~experiments.schema.RunSpec` onto an
:class:`evals.config.EvalConfig` and an
:class:`~experiments.schema.AblationSpec` onto an
:class:`evals.config.AblationConfig`, then delegates execution to
:func:`evals.runner.run_evaluation` / :func:`evals.ablation.run_ablation`
without modifying their source.

The adapter is the single seam through which experiment execution flows. It is
also the dependency-injection point: tests (and a future Dashboard) can supply
any object satisfying :class:`RunnerAdapter` to avoid running the real
orchestrator. The heavy runner/ablation modules are imported lazily so that
merely importing this module (or :mod:`experiments.manager`) does not load the
orchestrator or its model stack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from evals.config import AblationConfig, EvalConfig
from experiments.schema import AblationSpec, RunSpec

if TYPE_CHECKING:
    from evals.ablation import AblationRunResult
    from evals.runner import EvaluationResult


class RunnerAdapter(Protocol):
    """Execution seam used by :mod:`experiments.manager`.

    Implementations translate a run/ablation spec into a frozen config and
    execute it, returning the runner's result object. The default
    implementation wraps the real runner/ablation framework; tests inject a
    fake to keep the suite fast and orchestrator-free.
    """

    def run_evaluation(
        self, run_spec: RunSpec, *, dataset: str, output_dir: str
    ) -> EvaluationResult:
        ...

    def run_ablation(
        self, ablation_spec: AblationSpec, *, dataset: str, output_dir: str
    ) -> AblationRunResult:
        ...


def run_spec_to_eval_config(
    run_spec: RunSpec, *, dataset: str, output_dir: str
) -> EvalConfig:
    """Map a :class:`RunSpec` onto the frozen :class:`EvalConfig`."""
    return EvalConfig(
        dataset=dataset,
        output_dir=str(output_dir),
        planner_on=run_spec.planner,
        debate_on=run_spec.debate,
        critic_on=run_spec.critic,
        memory_on=run_spec.memory,
        tool_router_on=run_spec.tool_router,
        counterfactual_on=run_spec.counterfactual,
        use_langgraph=not run_spec.rules_only,
        use_llm_judge=run_spec.use_llm_judge,
        seed=run_spec.seed,
        max_cases=run_spec.max_cases,
        save_traces=run_spec.save_traces,
    )


def ablation_spec_to_config(
    ablation_spec: AblationSpec, *, dataset: str, output_dir: str
) -> AblationConfig:
    """Map an :class:`AblationSpec` onto the frozen :class:`AblationConfig`."""
    return AblationConfig(
        dataset=dataset,
        output_dir=str(output_dir),
        seed=ablation_spec.seed,
        max_cases=ablation_spec.max_cases,
        use_langgraph=not ablation_spec.rules_only,
        combos=ablation_spec.combos,
    )


class DefaultRunnerAdapter:
    """Adapter that runs the real evaluation runner / ablation framework."""

    def run_evaluation(
        self, run_spec: RunSpec, *, dataset: str, output_dir: str
    ) -> EvaluationResult:
        from evals.runner import run_evaluation

        config = run_spec_to_eval_config(run_spec, dataset=dataset, output_dir=output_dir)
        return run_evaluation(config)

    def run_ablation(
        self, ablation_spec: AblationSpec, *, dataset: str, output_dir: str
    ) -> AblationRunResult:
        from evals.ablation import run_ablation

        config = ablation_spec_to_config(ablation_spec, dataset=dataset, output_dir=output_dir)
        return run_ablation(config)