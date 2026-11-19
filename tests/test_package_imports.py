"""Every ``acis`` subpackage must be importable after the package refactor."""

from __future__ import annotations

import importlib
import pkgutil

import acis


def test_import_every_acis_submodule() -> None:
    failures: list[tuple[str, str]] = []
    for module_info in pkgutil.walk_packages(acis.__path__, acis.__name__ + "."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:  # noqa: BLE001 - report every failing import
            failures.append((module_info.name, f"{type(exc).__name__}: {exc}"))
    assert failures == []


def test_public_entry_modules_import() -> None:
    importlib.import_module("acis.cli")
    importlib.import_module("acis.core.orchestrator")
    importlib.import_module("acis.api.app")
    importlib.import_module("acis.ui.tui")
