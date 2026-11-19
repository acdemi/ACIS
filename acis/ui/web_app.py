"""Compatibility launcher for the Vue and TypeScript web interface."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"


def main() -> int:
    if not shutil.which("npm"):
        print("Node.js and npm are required to run the Vue frontend.", file=sys.stderr)
        return 2
    if not (WEB_ROOT / "node_modules").is_dir():
        print("Install frontend dependencies first: npm ci --prefix web", file=sys.stderr)
        return 2
    return subprocess.run(
        "npm run dev -- --host 127.0.0.1",
        cwd=WEB_ROOT,
        check=False,
        shell=True,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
