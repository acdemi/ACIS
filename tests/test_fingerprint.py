"""Tests for the dataset fingerprint module (Phase 2.1E -> 2.2, Sprint 06)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.fingerprint import (
    augment_manifest,
    compute_dataset_sha256,
    verify_experiment,
)


def _write_dataset(path: Path, payload: str) -> Path:
    path.write_text(payload, encoding="utf-8")
    return path


def _write_experiment(tmp_path: Path, dataset_path: Path, *, with_fingerprint: bool = True) -> Path:
    exp = tmp_path / "exp"
    exp.mkdir()
    manifest: dict[str, object] = {
        "experiment": "test_exp",
        "dataset": str(dataset_path),
        "dataset_source": str(dataset_path),
    }
    if with_fingerprint:
        manifest["dataset_sha256"] = compute_dataset_sha256(str(dataset_path))
    (exp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return exp


def test_compute_sha256_matches_hashlib(tmp_path: Path) -> None:
    p = _write_dataset(tmp_path / "d.json", '{"cases": []}')
    assert compute_dataset_sha256(str(p)) == hashlib.sha256(p.read_bytes()).hexdigest()


def test_compute_sha256_stable_across_calls(tmp_path: Path) -> None:
    p = _write_dataset(tmp_path / "d.json", '{"cases": [1, 2, 3]}')
    assert compute_dataset_sha256(str(p)) == compute_dataset_sha256(str(p))


def test_augment_manifest_adds_fingerprint_without_mutating() -> None:
    original = {"experiment": "x", "dataset": "benchmarks.datasets.enriched"}
    augmented = augment_manifest(original, "benchmarks.datasets.enriched")
    assert "dataset_sha256" in augmented
    assert augmented["dataset_source"] == "benchmarks.datasets.enriched"
    assert augmented["dataset_sha256"]
    assert "dataset_sha256" not in original


def test_verify_passes_when_dataset_intact(tmp_path: Path) -> None:
    p = _write_dataset(tmp_path / "d.json", '{"cases": []}')
    exp = _write_experiment(tmp_path, p)
    result = verify_experiment(exp)
    assert result.verified
    assert result.stored_sha256 == result.computed_sha256


def test_verify_fails_when_dataset_changed(tmp_path: Path) -> None:
    p = _write_dataset(tmp_path / "d.json", '{"cases": []}')
    exp = _write_experiment(tmp_path, p)
    _write_dataset(p, '{"cases": [1, 2, 3]}')  # mutate after archive
    result = verify_experiment(exp)
    assert not result.verified
    assert result.computed_sha256 != result.stored_sha256
    assert "changed" in result.reason


def test_verify_fails_when_fingerprint_missing(tmp_path: Path) -> None:
    p = _write_dataset(tmp_path / "d.json", '{"cases": []}')
    exp = _write_experiment(tmp_path, p, with_fingerprint=False)
    result = verify_experiment(exp)
    assert not result.verified
    assert "missing" in result.reason


def test_verify_fails_when_manifest_absent(tmp_path: Path) -> None:
    exp = tmp_path / "empty"
    exp.mkdir()
    result = verify_experiment(exp)
    assert not result.verified
    assert "manifest" in result.reason