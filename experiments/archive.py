"""Experiment archive (Phase 2.1E, Sprint 05).

Produces the immutable result bundle that makes every experiment reproducible:
a copy of the experiment definition (``config.yaml``), an environment snapshot
(``environment.txt`` from ``pip freeze``), and a ``manifest.json`` recording
the git commit, Python/platform, dataset, timing, and per-run metric +
capability summaries. Archives are write-once: once written they are not
modified by later runs, so a historical conclusion stays pinned to the exact
environment that produced it.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from experiments.schema import ExperimentDefinition, dump_definition


@dataclass(frozen=True)
class RunSummary:
    """Reproducibility summary for one archived run."""

    name: str
    dataset: str
    output_dir: str
    toggles: dict[str, bool]
    cases: int
    aggregate: dict[str, Any] = field(default_factory=dict)
    capability_scores: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AblationSummary:
    """Reproducibility summary for the optional ablation arm.

    `combos` reuses :class:RunSummary so ablation arms and evaluation runs
    can be compared uniformly by the catalog.
    """

    enabled: bool = False
    run_dir: str = ""
    report_path: str = ""
    combos: tuple[RunSummary, ...] = ()


def capture_git_info(repo_dir: str | Path | None = None) -> dict[str, str]:
    """Return short/long commit hash and branch; empty strings if unavailable."""
    cwd = str(repo_dir) if repo_dir else None

    def _git(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                cwd=cwd,
                check=False,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    return {
        "short": _git("rev-parse", "--short", "HEAD"),
        "full": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
    }


def capture_environment() -> str:
    """Capture ``pip freeze`` output for the current interpreter."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else result.stderr


def write_config_copy(exp_dir: str | Path, definition: ExperimentDefinition) -> Path:
    """Persist the experiment definition as ``config.yaml``."""
    path = Path(exp_dir) / "config.yaml"
    dump_definition(definition, path)
    return path


def write_environment(exp_dir: str | Path) -> Path:
    """Persist the ``pip freeze`` snapshot as ``environment.txt``."""
    path = Path(exp_dir) / "environment.txt"
    path.write_text(capture_environment(), encoding="utf-8")
    return path


def build_manifest(
    definition: ExperimentDefinition,
    *,
    dataset: str,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    runs: list[RunSummary],
    ablation: AblationSummary,
) -> dict[str, Any]:
    """Assemble the ``manifest.json`` mapping for an experiment."""
    return {
        "experiment": definition.name,
        "description": definition.description,
        "dataset": dataset,
        "capability_eval": definition.capability_eval,
        "metadata": asdict(definition.metadata),
        "git": capture_git_info(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "artifacts": {
            "config": "config.yaml",
            "environment": "environment.txt",
            "report": "REPORT.md",
        },
        "runs": [asdict(run) for run in runs],
        "ablation": asdict(ablation),
    }


def write_manifest(exp_dir: str | Path, manifest: dict[str, Any]) -> Path:
    """Write ``manifest.json`` (UTF-8, pretty-printed)."""
    path = Path(exp_dir) / "manifest.json"
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path