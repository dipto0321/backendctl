"""Generator matrix tests.

For every framework crossed with representative option combinations, generate a
project into a temp dir and assert that:

1. the expected entry-point files exist, and
2. every generated ``.py`` file compiles (no syntax errors in the templates).

Dependency installation and git init are stubbed out so the suite stays fast and
hermetic — we only exercise file generation, not the generated project's runtime.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

import pytest

from backendctl.core.config import (
    AIConfig,
    AIProvider,
    AuthType,
    Database,
    Framework,
    PackageManager,
    ProjectConfig,
    UserModelConfig,
)
from backendctl.generators import base, get_generator


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the network/disk-mutating steps of generation."""
    monkeypatch.setattr(base.BaseGenerator, "_install_deps", lambda self: None)
    monkeypatch.setattr(base.BaseGenerator, "_git_init", lambda self: None)


def _entry_points(framework: Framework, slug: str) -> list[str]:
    return {
        Framework.FASTAPI: [f"src/{slug}/main.py", "pyproject.toml", ".env.example"],
        Framework.FLASK: [f"src/{slug}/__init__.py", "pyproject.toml", ".env.example"],
        Framework.DJANGO: ["manage.py", "config/settings/base.py", "pyproject.toml"],
    }[framework]


def _make_config(framework: Framework, **overrides) -> ProjectConfig:
    config = ProjectConfig(name="demo_app", framework=framework, init_git=False)
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


# (framework, kwargs) combinations worth covering.
_MATRIX = [
    (Framework.FASTAPI, {}),
    (Framework.FASTAPI, {"database": Database.BOTH, "auth": AuthType.NONE}),
    (
        Framework.FASTAPI,
        {"user_model": UserModelConfig(has_name=True)},
    ),
    (Framework.FLASK, {}),
    (Framework.FLASK, {"database": Database.MONGODB}),
    (Framework.DJANGO, {}),
    (Framework.DJANGO, {"user_model": UserModelConfig(has_name=True)}),
    (
        Framework.FASTAPI,
        {
            "package_manager": PackageManager.PIP,
            "ai": AIConfig(
                provider=AIProvider.CLAUDE,
                create_instructions_file=True,
                create_cursorrules=True,
                create_mcp_config=True,
                install_sdk=True,
            ),
        },
    ),
]


@pytest.mark.parametrize(("framework", "overrides"), _MATRIX)
def test_generated_files_exist_and_compile(
    framework: Framework,
    overrides: dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(framework, **overrides)

    root = get_generator(config).generate()

    assert root.is_dir()
    for rel in _entry_points(framework, config.slug):
        assert (root / rel).is_file(), f"missing expected file: {rel}"

    py_files = list(root.rglob("*.py"))
    assert py_files, "generator produced no Python files"
    for py_file in py_files:
        py_compile.compile(str(py_file), doraise=True)


def test_ai_files_written_when_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(
        Framework.FASTAPI,
        ai=AIConfig(provider=AIProvider.CLAUDE, create_instructions_file=True),
    )

    root = get_generator(config).generate()

    assert (root / "CLAUDE.md").is_file()


def test_no_auth_skips_auth_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI, auth=AuthType.NONE)

    root = get_generator(config).generate()

    assert not (root / f"src/{config.slug}/modules/auth").exists()
