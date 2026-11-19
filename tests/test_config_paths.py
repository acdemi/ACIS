"""Path resolution must be independent of the process working directory."""

from __future__ import annotations

from pathlib import Path

import acis
from acis import config

REPO_ROOT = Path(acis.__file__).resolve().parent.parent


def _clear_root_override(monkeypatch) -> None:
    monkeypatch.delenv("ACIS_PROJECT_ROOT", raising=False)


def test_project_root_is_the_repository_root(monkeypatch, tmp_path) -> None:
    _clear_root_override(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert config.project_root() == REPO_ROOT


def test_relative_env_paths_resolve_against_repo_root(monkeypatch, tmp_path) -> None:
    _clear_root_override(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGRI_AI_DB_PATH", "data/relative.db")
    assert config.db_path() == REPO_ROOT / "data" / "relative.db"


def test_absolute_env_paths_are_preserved(monkeypatch, tmp_path) -> None:
    _clear_root_override(monkeypatch)
    monkeypatch.chdir(tmp_path)
    absolute = tmp_path / "absolute.db"
    monkeypatch.setenv("AGRI_AI_DB_PATH", str(absolute))
    assert config.db_path() == absolute


def test_default_paths_ignore_cwd(monkeypatch, tmp_path) -> None:
    _clear_root_override(monkeypatch)
    monkeypatch.delenv("AGRI_AI_DB_PATH", raising=False)
    monkeypatch.delenv("ACIS_DATA_DIR", raising=False)
    monkeypatch.delenv("ACIS_WEB_DIST_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert config.data_dir() == REPO_ROOT / "data"
    assert config.db_path() == REPO_ROOT / "data" / "agri.db"
    assert config.web_dist_dir() == REPO_ROOT / "web" / "dist"


def test_project_root_env_override(monkeypatch, tmp_path) -> None:
    override = tmp_path / "checkout"
    override.mkdir()
    monkeypatch.setenv("ACIS_PROJECT_ROOT", str(override))
    assert config.project_root() == override.resolve()


def test_load_env_reads_file_once_without_overriding(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "ACIS_CONFIG_TEST_VALUE=from-file\nACIS_CONFIG_TEST_EXISTING=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ACIS_CONFIG_TEST_VALUE", raising=False)
    monkeypatch.setenv("ACIS_CONFIG_TEST_EXISTING", "keep-me")

    assert config.load_env(env_file) == env_file
    assert config.load_env(env_file) is None
    assert config.load_env(env_file) is None

    import os

    assert os.environ["ACIS_CONFIG_TEST_VALUE"] == "from-file"
    assert os.environ["ACIS_CONFIG_TEST_EXISTING"] == "keep-me"


def test_load_env_default_does_not_use_cwd(monkeypatch, tmp_path) -> None:
    cwd_env = tmp_path / ".env"
    cwd_env.write_text("ACIS_CWD_ONLY_MARKER=1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ACIS_CWD_ONLY_MARKER", raising=False)
    monkeypatch.delenv("ACIS_PROJECT_ROOT", raising=False)

    config.load_env()

    import os

    assert "ACIS_CWD_ONLY_MARKER" not in os.environ
