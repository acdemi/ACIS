"""Unified command-line entry point for ACIS.

Subcommands::

    python -m acis                     # same CLI as ``python orchestrator.py``
    python -m acis tui                 # Rich terminal UI
    python -m acis eval [options]      # offline delivery evaluation
    python -m acis doctor              # environment self-check

The legacy ``python orchestrator.py ...`` launcher keeps working through a
thin compatibility shim at the repository root.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from typing import Callable

from acis import __version__
from acis.config import data_dir, db_path, load_env, project_root, upload_dir, web_dist_dir

MIN_PYTHON = (3, 11)
MIN_API_KEY_LENGTH = 32

#: Import names checked by ``doctor``. Missing required deps fail the check;
#: optional deps only warn because the runtime degrades gracefully.
REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("pydantic", "pydantic"),
    ("rich", "rich"),
    ("httpx", "httpx"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("PIL", "pillow"),
)
OPTIONAL_MODULES: tuple[tuple[str, str], ...] = (
    ("openai", "LLM Judge/Critic"),
    ("langgraph", "LangGraph workflow"),
    ("neo4j", "Neo4j knowledge graph"),
    ("qdrant_client", "Qdrant RAG backend"),
    ("numpy", "numeric backends"),
    ("sklearn", "confidence calibration"),
    ("torch", "vision model"),
    ("transformers", "vision model"),
)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _api_key_valid(value: str) -> bool:
    try:
        return len(value.encode("ascii")) >= MIN_API_KEY_LENGTH
    except UnicodeEncodeError:
        return False


def _check(label: str, ok: bool, detail: str = "", required: bool = True) -> bool:
    status = "OK  " if ok else ("FAIL" if required else "WARN")
    suffix = f"  {detail}" if detail else ""
    print(f"[{status}] {label}{suffix}")
    return ok or not required


def doctor() -> int:
    """Check the interpreter, dependencies, paths and API configuration."""
    print(f"ACIS {__version__} doctor")
    print(f"  python:  {platform.python_version()} ({sys.executable})")
    print(f"  repo:    {project_root()}")
    print()

    failures = 0
    if sys.version_info >= MIN_PYTHON:
        print(f"[OK  ] Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    else:
        print(f"[FAIL] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required")
        failures += 1

    for name, label in REQUIRED_MODULES:
        if not _check(f"dependency {name} ({label})", _module_available(name)):
            failures += 1
    for name, label in OPTIONAL_MODULES:
        _check(
            f"optional {name} ({label})",
            _module_available(name),
            "not installed; runtime fallback applies",
            required=False,
        )

    data = data_dir()
    try:
        data.mkdir(parents=True, exist_ok=True)
        probe = data / ".acis-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable = True
        detail = str(data)
    except OSError as exc:
        writable = False
        detail = f"{data} ({type(exc).__name__})"
    if not _check("data directory writable", writable, detail):
        failures += 1

    _check("database path", True, str(db_path()), required=False)
    _check("upload directory", True, str(upload_dir()), required=False)
    dist = web_dist_dir()
    _check("frontend bundle", dist.is_dir(), str(dist), required=False)

    api_key = os.environ.get("ACIS_API_KEY", "").strip()
    _check(
        "ACIS_API_KEY",
        _api_key_valid(api_key),
        "protected API routes will return 503"
        if not _api_key_valid(api_key)
        else "configured",
        required=False,
    )
    judge_key = (
        os.environ.get("AGRI_AI_JUDGE_API_KEY", "").strip()
        or os.environ.get("DEEPSEEK_API_KEY", "").strip()
    )
    _check(
        "LLM Judge/Critic key",
        bool(judge_key),
        "rules-only mode" if not judge_key else "configured",
        required=False,
    )

    print()
    if failures:
        print(f"doctor: {failures} required check(s) failed")
        return 1
    print("doctor: OK")
    return 0


def _run_tui(_args: list[str]) -> int:
    from acis.ui.tui import main as tui_main

    tui_main()
    return 0


def _run_eval(args: list[str]) -> int:
    sys.path.insert(0, str(project_root()))
    from scripts.run_delivery_eval import main as eval_main

    result = eval_main(args)
    return int(result) if isinstance(result, int) else 0


def _run_orchestrator(args: list[str]) -> int:
    from acis.core.orchestrator import main as orchestrator_main

    orchestrator_main(args)
    return 0


_SUBCOMMANDS: dict[str, Callable[[list[str]], int]] = {
    "tui": _run_tui,
    "doctor": lambda _args: doctor(),
    "eval": _run_eval,
}


def main(argv: list[str] | None = None) -> int:
    """Dispatch ``python -m acis`` and the ``acis`` console script."""
    args = list(sys.argv[1:] if argv is None else argv)
    load_env()
    if args and args[0] in _SUBCOMMANDS:
        command = args.pop(0)
        return _SUBCOMMANDS[command](args)
    return _run_orchestrator(args)


if __name__ == "__main__":
    raise SystemExit(main())
