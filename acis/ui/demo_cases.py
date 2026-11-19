"""Shared deterministic demo inputs for the Web and Rich interfaces."""

from __future__ import annotations

import json
from pathlib import Path

_DEMO_CASES_PATH = Path(__file__).resolve().parents[2] / "shared" / "demo_cases_v1.json"

with _DEMO_CASES_PATH.open(encoding="utf-8") as demo_file:
    DEMO_CASES = tuple(json.load(demo_file))

