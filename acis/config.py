"""ACIS configuration: repository paths and explicit ``.env`` loading.

The runtime must not depend on the process working directory.  Every path is
resolved either from an explicit absolute environment variable or relative to
the repository root, which is located from this package's own location.

``load_env()`` is idempotent and is called only by entry points
(``python -m acis``, the ``orchestrator.py`` compatibility launcher, the TUI
and API entry modules).  Importing library modules never mutates
``os.environ``.
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent
_loaded_env_files: set[Path] = set()


def project_root() -> Path:
    """Return the repository root that contains the ``acis`` package."""
    override = os.environ.get("ACIS_PROJECT_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _REPO_ROOT


def resolve_path(value: str | Path) -> Path:
    """Resolve ``value`` against the repository root when it is relative."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return project_root() / path


def data_dir() -> Path:
    """Directory for host-only data (datasets, SQLite databases, uploads)."""
    return resolve_path(os.environ.get("ACIS_DATA_DIR", "data"))


def db_path() -> Path:
    """Path of the decision audit SQLite database."""
    return resolve_path(os.environ.get("AGRI_AI_DB_PATH", str(data_dir() / "agri.db")))


def web_dist_dir() -> Path:
    """Directory holding the built Vue frontend bundle."""
    return resolve_path(os.environ.get("ACIS_WEB_DIST_DIR", "web/dist"))


def upload_dir() -> Path:
    """Directory where uploaded leaf images are staged."""
    return resolve_path(os.environ.get("ACIS_IMAGE_UPLOAD_DIR", str(data_dir() / "uploads")))


def load_env(path: str | Path | None = None) -> Path | None:
    """Load ``KEY=VALUE`` pairs from ``.env`` without overriding real env vars.

    Returns the loaded file, or ``None`` when the file is absent.  Repeated
    calls for the same file are no-ops.
    """
    target = resolve_path(path) if path is not None else project_root() / ".env"
    if target in _loaded_env_files or not target.exists():
        return None
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
    _loaded_env_files.add(target)
    return target
