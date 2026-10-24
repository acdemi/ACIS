"""End-to-end smoke tests for the offline CLI path.

These cover the command users actually type (see README), which the unit and
API contract suites do not: process exit code, rendered decision, SQLite
persistence and the exported trace.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERY = "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
STAGES = (
    "perception",
    "memory",
    "experts",
    "debate",
    "critic",
    "judge",
    "planner",
    "tool_router",
    "request",
    "metrics",
)


def _run_cli(tmp_path: Path, *extra: str, console_encoding: str = "utf-8"):
    db_path = tmp_path / "cli.db"
    # Own every ACIS setting: other suites mutate os.environ directly, and a
    # leaked AGRI_*/ACIS_* flag must not silently change what this e2e run does.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AGRI_", "ACIS_"))}
    env["AGRI_AI_DB_PATH"] = str(db_path)
    env["AGRI_AI_PERSIST"] = "1"
    env["PYTHONIOENCODING"] = console_encoding
    cmd = [
        sys.executable,
        "orchestrator.py",
        "--rules-only",
        "--seed",
        "7",
        *extra,
        QUERY,
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding=console_encoding,
        errors="replace",
    )
    return proc, db_path


def test_cli_rules_path_end_to_end(tmp_path):
    trace_path = tmp_path / "trace.json"

    proc, db_path = _run_cli(tmp_path, "--trace-out", str(trace_path))

    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "【裁决】" in proc.stdout
    assert "【置信度】" in proc.stdout
    assert "Trace" in proc.stdout

    assert db_path.exists(), "decision was not persisted to SQLite"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT decision, judge_mode FROM decisions").fetchall()
    assert len(rows) == 1, f"no decision row persisted; stderr={proc.stderr[-600:]!r}"
    decision, judge_mode = rows[0]
    assert decision
    assert judge_mode == "rules", "rules fallback must not be recorded as an LLM result"

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["trace_id"]
    for stage in STAGES:
        assert stage in trace, f"trace is missing the {stage} stage"


def test_cli_survives_narrow_console_encoding(tmp_path):
    """A GBK console must still print the diagnosis, not a traceback (P0)."""
    proc, _ = _run_cli(tmp_path, console_encoding="gbk")

    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "UnicodeEncodeError" not in proc.stderr
    assert "【裁决】" in proc.stdout
