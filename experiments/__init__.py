"""ACIS Experiment Manager (Phase 2.1E, Sprint 05).

Experiment-as-code: parse a YAML/JSON experiment definition, execute each run
through the frozen evaluation runner/ablation framework via an adapter, and
archive an immutable result bundle (config, manifest, environment snapshot,
report) so any historical conclusion can be reproduced.

The package never modifies frozen modules; it composes
:mod:`evals.runner` / :mod:`evals.ablation` through
:mod:`experiments.runner_adapter`.
"""
from experiments.schema import (
    AblationSpec,
    ExperimentDefinition,
    ExperimentMetadata,
    RunSpec,
    dump_definition,
    load_definition,
    parse_definition,
)

__all__ = [
    "AblationSpec",
    "ExperimentDefinition",
    "ExperimentMetadata",
    "RunSpec",
    "dump_definition",
    "load_definition",
    "parse_definition",
]