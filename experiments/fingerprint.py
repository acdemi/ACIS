"""Dataset fingerprinting (Phase 2.1E -> 2.2, Sprint 06).

Makes every archived experiment traceable to an exact dataset version by
recording a SHA-256 of the dataset content in ``manifest.json``. The
fingerprint is *mandatory* reproducibility metadata: ``verify`` recomputes it
and fails (returns ``verified=False``) if the dataset has changed since the
experiment ran.

The fingerprint is computed over the resolved dataset *file* bytes whenever
the dataset source maps to a JSON file (``benchmarks.datasets.*`` module-style
names and ``.json`` paths, both resolved via the frozen
:func:`benchmarks.loader.resolve_dataset`). Dataset sources that do not map to
a file (e.g. ``evals.fixtures``) are fingerprinted over the canonical JSON of
their loaded cases, so the contract holds for every dataset type. No frozen
module is modified.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _resolve_dataset_file(source: str) -> Path | None:
    """Return the backing JSON file for ``source``, or ``None`` if not file-backed."""
    try:
        from benchmarks.loader import resolve_dataset

        path, _difficulty = resolve_dataset(source)
        return path
    except Exception:  # noqa: BLE001
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_module_cases(source: str) -> str:
    """Fingerprint a non-file dataset over the canonical JSON of its cases."""
    from evals.config import load_dataset

    cases = [
        {
            "id": case.id,
            "query": case.query,
            "ground_truth": case.ground_truth,
            "sensor_override": case.sensor_override,
            "raw": case.raw,
        }
        for case in load_dataset(source)
    ]
    payload = json.dumps(cases, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_dataset_sha256(source: str) -> str:
    """Return the SHA-256 hex digest of the dataset identified by ``source``."""
    path = _resolve_dataset_file(source)
    if path is not None and path.exists():
        return _sha256_file(path)
    return _sha256_module_cases(source)


def dataset_file_path(source: str) -> Path | None:
    """Return the backing file path for ``source`` if one exists (for reporting)."""
    path = _resolve_dataset_file(source)
    if path is not None and path.exists():
        return path
    return None


def augment_manifest(manifest: dict[str, Any], dataset_source: str) -> dict[str, Any]:
    """Return ``manifest`` with mandatory dataset fingerprint fields added.

    Adds two top-level fields:

    - ``dataset_sha256`` - SHA-256 of the dataset content (mandatory).
    - ``dataset_source`` - the dataset source string that was fingerprinted.

    The input manifest is not mutated; a shallow copy is returned so callers
    can keep the original (e.g. the frozen ``archive.build_manifest`` output).
    """
    augmented = dict(manifest)
    augmented["dataset_source"] = dataset_source
    augmented["dataset_sha256"] = compute_dataset_sha256(dataset_source)
    return augmented


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of verifying an experiment's dataset fingerprint."""

    experiment_dir: str
    dataset_source: str
    stored_sha256: str
    computed_sha256: str
    verified: bool
    reason: str


def _read_manifest(experiment_dir: str | Path) -> dict[str, Any] | None:
    path = Path(experiment_dir) / "manifest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def verify_experiment(experiment_dir: str | Path) -> VerifyResult:
    """Verify the archived experiment's dataset fingerprint.

    Recomputes the dataset SHA-256 from the source recorded in the manifest and
    compares it to the stored ``dataset_sha256``. Returns a :class:`VerifyResult`
    with ``verified=True`` only when the manifest carries a fingerprint and the
    recomputed digest matches.
    """
    exp = str(experiment_dir)
    manifest = _read_manifest(exp)
    if manifest is None:
        return VerifyResult(exp, "", "", "", False, "manifest.json not found")
    source = str(manifest.get("dataset_source") or manifest.get("dataset") or "")
    if not source:
        return VerifyResult(exp, "", "", "", False, "no dataset source in manifest")
    stored = str(manifest.get("dataset_sha256") or "")
    if not stored:
        return VerifyResult(
            exp, source, "", "", False, "dataset_sha256 missing from manifest"
        )
    try:
        computed = compute_dataset_sha256(source)
    except Exception as exc:  # noqa: BLE001  dataset no longer resolvable
        return VerifyResult(exp, source, stored, "", False, f"recompute failed: {exc}")
    if computed == stored:
        return VerifyResult(exp, source, stored, computed, True, "dataset intact")
    return VerifyResult(
        exp, source, stored, computed, False, "dataset changed since experiment ran"
    )


__all__ = [
    "VerifyResult",
    "augment_manifest",
    "compute_dataset_sha256",
    "dataset_file_path",
    "verify_experiment",
]