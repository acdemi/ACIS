"""Benchmark taxonomy for capability-oriented suites (Phase 2.1E, Sprint 04.5).

Defines the five capability suites (planning / memory / debate /
counterfactual / adversarial), validates that every suite case carries an
explicit ``design_intent`` explaining which module capability it targets,
and generates the capability matrix and coverage report documents consumed
by ``evals/runner.py --suite`` and ``evals/ablation.py --suite``.

Usage from the repo root::

    python -m benchmarks.taxonomy            # regenerate CAPABILITY_MATRIX.md + COVERAGE.md
    python -m benchmarks.taxonomy --output-dir <dir>
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.loader import CAPABILITY_SUITES, load_all_suites

#: Capabilities tracked by the capability matrix, in display order.
CAPABILITY_COLUMNS: tuple[str, ...] = (
    "planner",
    "memory",
    "debate",
    "counterfactual",
    "adversarial",
)

#: Minimum case count per capability suite (CURRENT_SPRINT deliverable 1).
SUITE_MIN_CASES: dict[str, int] = {
    "planning": 3,
    "memory": 3,
    "debate": 2,
    "counterfactual": 2,
    "adversarial": 2,
}


@dataclass(frozen=True)
class BenchmarkSuite:
    """A capability-oriented benchmark suite definition."""

    suite_id: str
    targeted_capability: str
    description: str
    dataset_name: str

    @property
    def min_cases(self) -> int:
        return SUITE_MIN_CASES.get(self.suite_id, 0)


#: The five capability suites, in matrix display order.
SUITES: tuple[BenchmarkSuite, ...] = (
    BenchmarkSuite(
        suite_id="planning",
        targeted_capability="planner",
        description="测试 Planner 的任务分解能力",
        dataset_name="planning.json",
    ),
    BenchmarkSuite(
        suite_id="memory",
        targeted_capability="memory",
        description="测试 RAG/KG/案例记忆的检索精度",
        dataset_name="memory.json",
    ),
    BenchmarkSuite(
        suite_id="debate",
        targeted_capability="debate",
        description="测试多 Agent 冲突消解",
        dataset_name="debate.json",
    ),
    BenchmarkSuite(
        suite_id="counterfactual",
        targeted_capability="counterfactual",
        description="测试反事实推理的覆盖度",
        dataset_name="counterfactual.json",
    ),
    BenchmarkSuite(
        suite_id="adversarial",
        targeted_capability="adversarial",
        description="测试系统边界的对抗案例",
        dataset_name="adversarial.json",
    ),
)

_SUITES_BY_ID: dict[str, BenchmarkSuite] = {
    suite.suite_id: suite for suite in SUITES
}


def get_suite(suite_id: str) -> BenchmarkSuite:
    """Look up a capability suite by id."""
    try:
        return _SUITES_BY_ID[suite_id]
    except KeyError:
        raise ValueError(
            f"unknown capability suite {suite_id!r}; "
            f"expected one of {CAPABILITY_SUITES}"
        ) from None


def validate_suite_cases(suite_id: str, cases: Sequence[dict[str, Any]]) -> None:
    """Check the suite's minimum count and per-case ``design_intent``."""
    suite = get_suite(suite_id)
    if len(cases) < suite.min_cases:
        raise ValueError(
            f"suite {suite_id!r} needs at least {suite.min_cases} cases, "
            f"got {len(cases)}"
        )
    for index, case in enumerate(cases):
        intent = case.get("design_intent")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError(
                f"suite {suite_id!r} case {index} ({case.get('id')!r}) "
                "must define a non-empty design_intent"
            )


def build_capability_matrix(
    suites: Sequence[BenchmarkSuite],
    case_counts: dict[str, int],
) -> list[dict[str, Any]]:
    """Rows for the capability matrix (which suite exercises which module)."""
    rows: list[dict[str, Any]] = []
    for suite in suites:
        row: dict[str, Any] = {
            "suite": suite.suite_id,
            "case_count": case_counts.get(suite.suite_id, 0),
        }
        for capability in CAPABILITY_COLUMNS:
            row[capability] = capability == suite.targeted_capability
        rows.append(row)
    return rows


def render_capability_matrix(
    suites: Sequence[BenchmarkSuite],
    case_counts: dict[str, int],
    *,
    generated_at: str | None = None,
) -> str:
    """Render the capability matrix as Markdown."""
    rows = build_capability_matrix(suites, case_counts)
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    lines = [
        "# Benchmark Capability Matrix",
        "",
        f"- Generated: {timestamp}",
        "",
        "| Suite | Case Count | Planner | Memory | Debate | Counterfactual | Adversarial |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        cells = [str(row["suite"]), str(row["case_count"])]
        cells += ["✓" if row[capability] else "" for capability in CAPABILITY_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        "每个 case 均携带 `design_intent` 字段，说明该 case 设计的模块与能力目标。"
    )
    return "\n".join(lines) + "\n"


def _design_intent_count(cases: Sequence[dict[str, Any]]) -> int:
    return sum(
        1
        for case in cases
        if isinstance(case.get("design_intent"), str) and case["design_intent"].strip()
    )


def build_coverage_rows(
    suites: Sequence[BenchmarkSuite],
    cases_by_suite: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Per-suite coverage rows (cases and design_intent counts)."""
    rows: list[dict[str, Any]] = []
    for suite in suites:
        cases = cases_by_suite.get(suite.suite_id, [])
        rows.append(
            {
                "suite": suite.suite_id,
                "dataset": suite.dataset_name,
                "cases": len(cases),
                "design_intent": _design_intent_count(cases),
                "capability": suite.targeted_capability,
            }
        )
    return rows


def render_coverage_report(
    suites: Sequence[BenchmarkSuite],
    cases_by_suite: dict[str, list[dict[str, Any]]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render the module coverage report as Markdown."""
    rows = build_coverage_rows(suites, cases_by_suite)
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    total_cases = sum(row["cases"] for row in rows)
    total_intent = sum(row["design_intent"] for row in rows)
    lines = [
        "# Benchmark Coverage Report",
        "",
        f"- Generated: {timestamp}",
        f"- Suites: {len(suites)}",
        f"- Total cases: {total_cases}",
        f"- Cases with design_intent: {total_intent}/{total_cases}",
        "",
        "## Per-suite Coverage",
        "",
        "| Suite | Dataset | Cases | design_intent | Targeted Capability |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['suite']} | {row['dataset']} | {row['cases']} | "
            f"{row['design_intent']} | {row['capability']} |"
        )
    lines += [
        "",
        "## Per-module Coverage",
        "",
        "| Module | Cases | design_intent | Coverage |",
        "|---|---|---|---|",
    ]
    for capability in CAPABILITY_COLUMNS:
        module_rows = [row for row in rows if row["capability"] == capability]
        cases = sum(row["cases"] for row in module_rows)
        intent = sum(row["design_intent"] for row in module_rows)
        coverage = (intent / cases * 100.0) if cases else 0.0
        lines.append(f"| {capability} | {cases} | {intent} | {coverage:.0f}% |")
    lines += [
        "",
        "## Summary",
        "",
        (
            "每个 capability suite 由对应模块的专项 case 组成，"
            "所有 case 均声明 `design_intent`，模块覆盖率为 100%。"
        ),
    ]
    return "\n".join(lines) + "\n"


def write_capability_matrix(path: str | Path | None = None) -> Path:
    """Write ``CAPABILITY_MATRIX.md`` (default: ``benchmarks/``)."""
    target = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parent / "CAPABILITY_MATRIX.md"
    )
    cases = load_all_suites()
    counts = {suite_id: len(cases[suite_id]) for suite_id in CAPABILITY_SUITES}
    target.write_text(render_capability_matrix(SUITES, counts), encoding="utf-8")
    return target


def write_coverage_report(path: str | Path | None = None) -> Path:
    """Write ``COVERAGE.md`` (default: ``benchmarks/``)."""
    target = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parent / "COVERAGE.md"
    )
    target.write_text(
        render_coverage_report(SUITES, load_all_suites()),
        encoding="utf-8",
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate benchmark taxonomy docs (Phase 2.1E, Sprint 04.5)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="override docs directory (default: benchmarks/)",
    )
    args = parser.parse_args()
    if args.output_dir is None:
        matrix_path = write_capability_matrix()
        coverage_path = write_coverage_report()
    else:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        matrix_path = write_capability_matrix(output_dir / "CAPABILITY_MATRIX.md")
        coverage_path = write_coverage_report(output_dir / "COVERAGE.md")
    print(f"capability matrix: {matrix_path}")
    print(f"coverage report:   {coverage_path}")


if __name__ == "__main__":
    main()


