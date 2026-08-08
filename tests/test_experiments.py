"""Unit tests for the Experiment Manager (Phase 2.1E, Sprint 05).

Covers schema parsing (YAML/JSON), the runner-adapter config mapping, archive
manifest reproducibility fields, catalog list/filter/compare/latest, and an
end-to-end manager run using a fake adapter (no orchestrator execution).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.config import AblationConfig, EvalConfig
from experiments import manager as exp_manager
from experiments.archive import (
    AblationSummary,
    RunSummary,
    build_manifest,
    write_manifest,
)
from experiments.catalog import (
    compare_experiments,
    filter_experiments,
    latest_experiment,
    list_experiments,
    load_record,
    parse_filter_args,
)
from experiments.runner_adapter import ablation_spec_to_config, run_spec_to_eval_config
from experiments.schema import (
    AblationSpec,
    RunSpec,
    dump_definition,
    load_definition,
    parse_definition,
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def test_parse_definition_defaults_and_toggles():
    defn = parse_definition(
        {
            "name": "exp",
            "dataset": "evals.fixtures",
            "runs": [
                {"name": "all_on", "max_cases": 2},
                {"name": "no_memory", "memory": False, "max_cases": 2},
            ],
            "metadata": {"tags": ["a", "b"], "author": "tester"},
        }
    )
    assert defn.name == "exp"
    assert defn.capability_eval is True
    assert defn.runs[0].memory is True
    assert defn.runs[1].memory is False
    assert defn.runs[1].planner is True
    assert defn.metadata.tags == ("a", "b")
    assert defn.ablation.enabled is False


def test_parse_definition_requires_name():
    with pytest.raises(ValueError):
        parse_definition({"dataset": "evals.fixtures"})


def test_parse_definition_run_requires_name():
    with pytest.raises(ValueError):
        parse_definition({"name": "exp", "runs": [{"max_cases": 1}]})


def test_load_yaml_and_json_definitions(tmp_path):
    yaml_path = tmp_path / "d.yaml"
    yaml_path.write_text(
        "name: y\ndataset: evals.fixtures\nruns:\n  - name: r1\n    max_cases: 1\n",
        encoding="utf-8",
    )
    assert load_definition(yaml_path).runs[0].name == "r1"
    json_path = tmp_path / "d.json"
    json_path.write_text(
        json.dumps({"name": "j", "dataset": "evals.fixtures", "runs": []}),
        encoding="utf-8",
    )
    assert load_definition(json_path).name == "j"


def test_dump_definition_roundtrip(tmp_path):
    defn = parse_definition(
        {"name": "rt", "runs": [{"name": "r1", "max_cases": 1}], "metadata": {"tags": ["x"]}}
    )
    path = tmp_path / "rt.yaml"
    dump_definition(defn, path)
    again = load_definition(path)
    assert again.name == "rt"
    assert again.runs[0].name == "r1"
    assert again.metadata.tags == ("x",)


def test_ablation_spec_parsing():
    defn = parse_definition(
        {"name": "exp", "ablation": {"enabled": True, "combos": ["all_on", "no_memory"]}}
    )
    assert defn.ablation.enabled is True
    assert defn.ablation.combos == ("all_on", "no_memory")


# ---------------------------------------------------------------------------
# Runner adapter
# ---------------------------------------------------------------------------
def test_run_spec_to_eval_config_maps_fields():
    spec = RunSpec(
        name="x",
        planner=False,
        memory=False,
        max_cases=3,
        rules_only=True,
        save_traces=True,
        seed=42,
    )
    cfg = run_spec_to_eval_config(spec, dataset="evals.fixtures", output_dir="out/x")
    assert isinstance(cfg, EvalConfig)
    assert cfg.dataset == "evals.fixtures"
    assert cfg.output_dir == "out/x"
    assert cfg.planner_on is False
    assert cfg.memory_on is False
    assert cfg.debate_on is True
    assert cfg.tool_router_on is True
    assert cfg.use_langgraph is False
    assert cfg.max_cases == 3
    assert cfg.save_traces is True
    assert cfg.seed == 42


def test_ablation_spec_to_config_maps_combos():
    spec = AblationSpec(enabled=True, combos=("all_on", "no_memory"), max_cases=2, seed=9)
    cfg = ablation_spec_to_config(spec, dataset="evals.fixtures", output_dir="out/abl")
    assert isinstance(cfg, AblationConfig)
    assert cfg.combos == ("all_on", "no_memory")
    assert cfg.dataset == "evals.fixtures"
    assert cfg.max_cases == 2
    assert cfg.seed == 9


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------
def test_build_manifest_has_reproducibility_fields():
    defn = parse_definition({"name": "exp", "dataset": "evals.fixtures"})
    runs = [
        RunSummary(
            name="all_on",
            dataset="evals.fixtures",
            output_dir="out",
            toggles={"planner": True},
            cases=2,
            aggregate={"accuracy": 1.0},
            capability_scores={
                "information_gathering": {"average": 0.5, "cases": 2, "positive": 1}
            },
        )
    ]
    manifest = build_manifest(
        defn,
        dataset="evals.fixtures",
        started_at="t0",
        ended_at="t1",
        duration_seconds=1.5,
        runs=runs,
        ablation=AblationSummary(),
    )
    assert manifest["experiment"] == "exp"
    assert "short" in manifest["git"]
    assert manifest["python"]
    assert manifest["platform"]
    assert manifest["dataset"] == "evals.fixtures"
    assert manifest["duration_seconds"] == 1.5
    assert manifest["runs"][0]["capability_scores"]["information_gathering"]["average"] == 0.5
    assert manifest["ablation"]["enabled"] is False


def test_write_manifest_roundtrip(tmp_path):
    manifest = {"experiment": "exp", "git": {"short": "abc1234"}}
    path = write_manifest(tmp_path, manifest)
    assert json.loads(path.read_text(encoding="utf-8"))["git"]["short"] == "abc1234"


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
def _make_exp(
    root: Path,
    dir_name: str,
    experiment: str,
    dataset: str,
    started: str,
    cap_average: float = 0.5,
) -> Path:
    exp_dir = root / dir_name
    exp_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "experiment": experiment,
        "dataset": dataset,
        "started_at": started,
        "git": {"short": "abc1234"},
        "python": "3.13.3",
        "runs": [
            {
                "name": "all_on",
                "aggregate": {
                    "accuracy": 1.0,
                    "average_confidence": 0.8,
                    "cases": 2,
                    "average_runtime": 0.5,
                },
                "capability_scores": {"information_gathering": {"average": cap_average}},
            }
        ],
        "ablation": {"enabled": False, "combos": []},
    }
    (exp_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return exp_dir


def test_list_filter_latest(tmp_path):
    _make_exp(tmp_path, "exp__1", "alpha", "enriched", "2026-01-01T00:00:00+00:00")
    _make_exp(tmp_path, "exp__2", "beta", "easy", "2026-02-01T00:00:00+00:00")
    records = list_experiments(tmp_path)
    assert len(records) == 2
    assert records[0].started_at == "2026-01-01T00:00:00+00:00"
    filtered = filter_experiments(records, {"dataset": "enriched"})
    assert len(filtered) == 1
    assert filtered[0].name == "alpha"
    latest = latest_experiment(tmp_path)
    assert latest is not None
    assert latest.name == "beta"


def test_filter_by_tag(tmp_path):
    _make_exp(tmp_path, "exp__1", "alpha", "enriched", "2026-01-01T00:00:00+00:00")
    records = list_experiments(tmp_path)
    records[0].manifest["metadata"] = {"tags": ["smoke", "paper"]}
    assert len(filter_experiments(records, {"metadata.tags": "paper"})) == 1
    assert len(filter_experiments(records, {"metadata.tags": "missing"})) == 0


def test_parse_filter_args():
    assert parse_filter_args(["dataset=enriched", "metadata.tags=test"]) == {
        "dataset": "enriched",
        "metadata.tags": "test",
    }
    with pytest.raises(ValueError):
        parse_filter_args(["noequals"])


def test_compare_includes_capability_columns(tmp_path):
    _make_exp(tmp_path, "a", "alpha", "enriched", "2026-01-01T00:00:00+00:00", cap_average=0.5)
    _make_exp(tmp_path, "b", "beta", "enriched", "2026-02-01T00:00:00+00:00", cap_average=0.25)
    record_a = load_record(tmp_path / "a")
    record_b = load_record(tmp_path / "b")
    assert record_a is not None and record_b is not None
    out = compare_experiments(record_a, record_b)
    assert "information_gathering" in out
    assert "0.500" in out
    assert "0.250" in out
    assert "accuracy" in out


# ---------------------------------------------------------------------------
# Manager (fake adapter)
# ---------------------------------------------------------------------------
class _FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run_evaluation(self, run_spec: RunSpec, *, dataset: str, output_dir: str) -> object:
        self.calls.append(("eval", run_spec.name, dataset, output_dir))
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.csv").write_text("case_id,accuracy\n", encoding="utf-8")
        (out / "summary.md").write_text("# summary\n", encoding="utf-8")
        rows = [
            SimpleNamespace(
                capability_scores={"information_gathering": 0.5, "knowledge_retrieval": 1.0}
            )
        ]
        return SimpleNamespace(
            rows=rows,
            aggregate={"cases": 1, "accuracy": 1.0, "average_confidence": 0.8},
        )

    def run_ablation(self, ablation_spec: AblationSpec, *, dataset: str, output_dir: str) -> object:
        self.calls.append(("ablation", dataset, output_dir))
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        combo_dir = out / "all_on"
        combo_dir.mkdir(parents=True, exist_ok=True)
        rows = [SimpleNamespace(capability_scores={"information_gathering": 0.5})]
        combo = SimpleNamespace(
            combo_name="all_on",
            toggles={"planner_on": True},
            rows=rows,
            aggregate={"cases": 1, "accuracy": 1.0},
            combo_dir=combo_dir,
        )
        report = out / "REPORT.md"
        report.write_text("# ablation\n", encoding="utf-8")
        return SimpleNamespace(run_dir=out, report_path=report, combo_results=[combo])


def _write_definition(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "def.yaml"
    path.write_text(body.format(root=str(tmp_path / "out")), encoding="utf-8")
    return path


def test_manager_run_archives_full_bundle(tmp_path):
    path = _write_definition(
        tmp_path,
        """name: test_exp
description: A test experiment.
dataset: evals.fixtures
output_root: {root}
capability_eval: true
metadata:
  author: tester
  tags: [test, smoke]
runs:
  - name: all_on
    max_cases: 2
  - name: no_memory
    memory: false
    max_cases: 2
""",
    )
    adapter = _FakeAdapter()
    exp_dir = exp_manager.run(path, adapter=adapter)
    assert (exp_dir / "config.yaml").exists()
    assert (exp_dir / "manifest.json").exists()
    assert (exp_dir / "environment.txt").exists()
    assert (exp_dir / "REPORT.md").exists()
    manifest = json.loads((exp_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["experiment"] == "test_exp"
    assert manifest["git"]["short"]
    assert manifest["python"]
    assert len(manifest["runs"]) == 2
    assert manifest["runs"][0]["name"] == "all_on"
    assert manifest["runs"][0]["capability_scores"]["information_gathering"]["average"] == 0.5
    assert (exp_dir / "runs" / "all_on" / "metrics.csv").exists()
    report = (exp_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "Capability Summary" in report
    assert "information_gathering" in report
    assert len(adapter.calls) == 2


def test_manager_run_ablation_arm(tmp_path):
    path = _write_definition(
        tmp_path,
        """name: abl_exp
dataset: evals.fixtures
output_root: {root}
runs: []
ablation:
  enabled: true
  combos: []
""",
    )
    adapter = _FakeAdapter()
    exp_dir = exp_manager.run(path, adapter=adapter)
    manifest = json.loads((exp_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ablation"]["enabled"] is True
    assert len(manifest["ablation"]["combos"]) == 1
    assert manifest["ablation"]["combos"][0]["name"] == "all_on"
    report = (exp_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "Ablation" in report
    assert len(adapter.calls) == 1


def test_manager_cli_list_latest_compare(tmp_path):
    _make_exp(tmp_path, "a", "alpha", "enriched", "2026-01-01T00:00:00+00:00")
    _make_exp(tmp_path, "b", "beta", "easy", "2026-02-01T00:00:00+00:00")
    assert exp_manager.main(["list", "--output-root", str(tmp_path)]) == 0
    assert exp_manager.main(["latest", "--output-root", str(tmp_path)]) == 0
    assert exp_manager.main(["compare", "--output-root", str(tmp_path), "a", "b"]) == 0


def test_manager_cli_compare_missing_experiment(tmp_path):
    _make_exp(tmp_path, "a", "alpha", "enriched", "2026-01-01T00:00:00+00:00")
    assert exp_manager.main(["compare", "--output-root", str(tmp_path), "a", "missing"]) == 1