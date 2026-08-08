"""Experiment definition schema (Phase 2.1E, Sprint 05).

Defines the dataclasses that describe a reproducible experiment: the dataset,
the per-run module toggles, an optional ablation arm, the capability-evaluation
flag, and metadata. Definitions are authored as YAML (recommended) or JSON and
parsed into :class:`ExperimentDefinition` instances by :func:`load_definition`.

The schema is a thin, serializable description with no behaviour. Execution is
delegated to :mod:`experiments.runner_adapter`, which maps each run onto the
frozen ``EvalConfig`` / ``AblationConfig`` consumed by ``evals.runner`` /
``evals.ablation``. No frozen module is modified.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

#: Cognitive-module toggles shared by every run and ablation combo.
TOGGLE_FIELDS: tuple[str, ...] = (
    "planner",
    "debate",
    "memory",
    "tool_router",
    "counterfactual",
    "critic",
)


@dataclass(frozen=True)
class RunSpec:
    """One evaluation run within an experiment."""

    name: str
    dataset: str | None = None
    planner: bool = True
    debate: bool = True
    memory: bool = True
    tool_router: bool = True
    counterfactual: bool = True
    critic: bool = True
    seed: int = 7
    seeds: list[int] = field(default_factory=list)
    max_cases: int | None = None
    save_traces: bool = False
    rules_only: bool = False
    use_llm_judge: bool = False


@dataclass(frozen=True)
class AblationSpec:
    """Optional full-ablation arm driven by ``evals.ablation``."""

    enabled: bool = False
    combos: tuple[str, ...] = ()
    dataset: str | None = None
    seed: int = 7
    max_cases: int | None = None
    rules_only: bool = False


@dataclass(frozen=True)
class ExperimentMetadata:
    """Free-form reproducibility metadata for an experiment."""

    author: str = ""
    version: str = ""
    tags: tuple[str, ...] = ()
    notes: str = ""
    paper: str = ""


@dataclass(frozen=True)
class ExperimentDefinition:
    """A complete, serializable experiment definition."""

    name: str
    description: str = ""
    dataset: str = "evals.fixtures"
    output_root: str = "results/experiments"
    runs: tuple[RunSpec, ...] = ()
    ablation: AblationSpec = field(default_factory=AblationSpec)
    capability_eval: bool = True
    metadata: ExperimentMetadata = field(default_factory=ExperimentMetadata)


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_seeds(value: Any) -> list[int]:
    """Parse a ``seeds: [a, b, c]`` list, empty if absent."""
    if value is None:
        return []
    if isinstance(value, (int, str)) and not isinstance(value, bool):
        raise TypeError("seeds must be a list of integers, e.g. [41, 42, 43]")
    if not isinstance(value, list):
        raise TypeError(
            f"seeds must be a list of integers, got {type(value).__name__}"
        )
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"each seed must be an integer, got {item!r}") from exc
    return result


def _parse_run(raw: dict[str, Any]) -> RunSpec:
    name = raw.get("name")
    if not name:
        raise ValueError("each run must define a non-empty 'name'")
    seeds = _parse_seeds(raw.get("seeds"))
    if seeds and "seed" in raw:
        raise ValueError(
            f"run {name!r}: 'seed' and 'seeds' are mutually exclusive; "
            "specify only one"
        )
    resolved_seed = _as_int_or_none(raw.get("seed"))
    return RunSpec(
        name=str(name),
        dataset=raw.get("dataset"),
        planner=_as_bool(raw.get("planner", True)),
        debate=_as_bool(raw.get("debate", True)),
        memory=_as_bool(raw.get("memory", True)),
        tool_router=_as_bool(raw.get("tool_router", True)),
        counterfactual=_as_bool(raw.get("counterfactual", True)),
        critic=_as_bool(raw.get("critic", True)),
        seed=resolved_seed if resolved_seed is not None else 7,
        seeds=seeds,
        max_cases=_as_int_or_none(raw.get("max_cases")),
        save_traces=_as_bool(raw.get("save_traces", False), False),
        rules_only=_as_bool(raw.get("rules_only", False), False),
        use_llm_judge=_as_bool(raw.get("use_llm_judge", False), False),
    )


def _parse_ablation(raw: dict[str, Any] | None) -> AblationSpec:
    if not raw:
        return AblationSpec()
    combos = raw.get("combos") or ()
    if isinstance(combos, str):
        combos = [c.strip() for c in combos.split(",") if c.strip()]
    return AblationSpec(
        enabled=_as_bool(raw.get("enabled", False), False),
        combos=tuple(str(c) for c in combos),
        dataset=raw.get("dataset"),
        seed=int(raw.get("seed", 7)),
        max_cases=_as_int_or_none(raw.get("max_cases")),
        rules_only=_as_bool(raw.get("rules_only", False), False),
    )


def _parse_metadata(raw: dict[str, Any] | None) -> ExperimentMetadata:
    if not raw:
        return ExperimentMetadata()
    tags = raw.get("tags") or ()
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return ExperimentMetadata(
        author=str(raw.get("author", "")),
        version=str(raw.get("version", "")),
        tags=tuple(str(t) for t in tags),
        notes=str(raw.get("notes", "")),
        paper=str(raw.get("paper", "")),
    )


def _load_raw(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = json.loads(text) if p.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise TypeError(f"experiment definition {p} must be a mapping at the top level")
    return data


def parse_definition(data: dict[str, Any]) -> ExperimentDefinition:
    """Build an :class:`ExperimentDefinition` from a parsed mapping."""
    name = data.get("name")
    if not name:
        raise ValueError("experiment definition must define a non-empty 'name'")
    runs_raw = data.get("runs") or []
    if not isinstance(runs_raw, list):
        raise TypeError("'runs' must be a list")
    # Top-level defaults propagate to runs that don't set the field explicitly.
    top_use_llm_judge = data.get("use_llm_judge")
    top_save_traces = data.get("save_traces")
    runs_list: list[RunSpec] = []
    for raw in runs_raw:
        if not isinstance(raw, dict):
            raise TypeError("each run must be a mapping")
        if top_use_llm_judge is not None and "use_llm_judge" not in raw:
            raw = dict(raw, use_llm_judge=_as_bool(top_use_llm_judge, False))
        if top_save_traces is not None and "save_traces" not in raw:
            raw = dict(raw, save_traces=_as_bool(top_save_traces, False))
        runs_list.append(_parse_run(raw))
    runs = tuple(runs_list)
    return ExperimentDefinition(
        name=str(name),
        description=str(data.get("description", "")),
        dataset=str(data.get("dataset", "evals.fixtures")),
        output_root=str(data.get("output_root", "results/experiments")),
        runs=runs,
        ablation=_parse_ablation(data.get("ablation")),
        capability_eval=_as_bool(data.get("capability_eval", True), True),
        metadata=_parse_metadata(data.get("metadata")),
    )


def load_definition(path: str | Path) -> ExperimentDefinition:
    """Load an experiment definition from a YAML or JSON file."""
    return parse_definition(_load_raw(path))


def definition_to_dict(definition: ExperimentDefinition) -> dict[str, Any]:
    """Convert a definition to a plain (serializable) mapping."""
    return asdict(definition)


def dump_definition(definition: ExperimentDefinition, path: str | Path) -> Path:
    """Write a definition back to YAML or JSON (by file suffix)."""
    p = Path(path)
    data = definition_to_dict(definition)
    if p.suffix.lower() == ".json":
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    p.write_text(text, encoding="utf-8")
    return p