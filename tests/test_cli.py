"""CLI-level tests for `backendctl new` flag handling.

These exercise the argument path (not the interactive wizard), which is where
the path-traversal and non-interactive regressions lived.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from backendctl.main import app

runner = CliRunner()


@pytest.mark.parametrize("bad_name", ["../evil", "..", "sub/dir", "/tmp/evil", "my app", "1app"])
def test_invalid_project_name_argument_rejected(bad_name: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", bad_name, "--yes"])
    assert result.exit_code == 1
    assert not (tmp_path / "evil").exists()


def test_yes_requires_project_name() -> None:
    result = runner.invoke(app, ["new", "--yes"])
    assert result.exit_code == 1


def test_django_with_mongodb_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["new", "demo", "--framework", "django", "--db", "mongodb", "--yes", "--no-git", "--no-ai"],
    )
    assert result.exit_code == 1
    assert not (tmp_path / "demo").exists()


@pytest.mark.parametrize(
    ("flag", "value"),
    [("--framework", "rails"), ("--db", "oracle"), ("--pm", "poetry"), ("--auth", "oauth")],
)
def test_unknown_flag_values_rejected(flag: str, value: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "demo", flag, value, "--yes"])
    assert result.exit_code == 1


def test_nonempty_directory_without_force_fails_noninteractively(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "demo"
    target.mkdir()
    (target / "precious.txt").write_text("keep")

    result = runner.invoke(app, ["new", "demo", "--yes", "--no-git", "--no-ai"])

    assert result.exit_code == 1
    assert (target / "precious.txt").read_text() == "keep"


def _stub_generation(monkeypatch):
    from backendctl.generators import base

    monkeypatch.setattr(base.BaseGenerator, "_install_deps", lambda self: None)
    monkeypatch.setattr(base.BaseGenerator, "_git_init", lambda self: None)
    monkeypatch.setattr("backendctl.cli.new.run_preflight", lambda *a, **k: True)


def test_db_flags_flow_into_generated_env(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "new", "demo", "--framework", "fastapi", "--db", "postgres",
            "--db-name", "customdb", "--db-user", "alice", "--db-password", "pw12345",
            "--yes", "--no-git", "--no-ai",
        ],
    )

    assert result.exit_code == 0, result.output
    env = (tmp_path / "demo" / ".env").read_text()
    assert "postgresql+psycopg://alice:pw12345@localhost:5432/customdb" in env


@pytest.mark.parametrize("flag", ["--db-name", "--db-user"])
def test_invalid_db_identifier_flags_rejected(flag: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(app, ["new", "demo", flag, "bad;name", "--yes", "--no-git", "--no-ai"])

    assert result.exit_code == 1
    assert not (tmp_path / "demo").exists()


def test_yes_generates_random_password(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(app, ["new", "demo", "--yes", "--no-git", "--no-ai"])

    assert result.exit_code == 0, result.output
    env = (tmp_path / "demo" / ".env").read_text()
    assert "change-me-db-password" not in env
    assert "user:password@" not in env


def test_success_panel_is_framework_aware(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(
        app, ["new", "demo", "-f", "flask", "--yes", "--no-git", "--no-ai"]
    )

    assert result.exit_code == 0, result.output
    assert "flask" in result.output
    assert "cp .env.example" not in result.output
    assert "fastapi dev" not in result.output
