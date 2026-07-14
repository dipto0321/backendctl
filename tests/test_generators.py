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
    (Framework.FLASK, {"user_model": UserModelConfig(has_name=True)}),
    (Framework.FASTAPI, {"database": Database.MONGODB}),
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


# ─── safety guards (C1/C2/M3 regression tests) ──────────────────────────────


@pytest.mark.parametrize("bad_name", ["../evil", "..", "sub/dir", "/tmp/evil", "a b", ""])
def test_unsafe_project_names_rejected(
    bad_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(name=bad_name, framework=Framework.FASTAPI, init_git=False)

    with pytest.raises(base.ScaffoldError):
        get_generator(config)


def test_nonempty_directory_requires_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "demo_app"
    existing.mkdir()
    (existing / "precious.txt").write_text("do not clobber")

    config = _make_config(Framework.FASTAPI)

    with pytest.raises(base.ScaffoldError):
        get_generator(config).generate()
    assert (existing / "precious.txt").read_text() == "do not clobber"


def test_force_preserves_existing_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "demo_app"
    existing.mkdir()
    (existing / ".env").write_text("SECRET_KEY=my-real-production-secret\n")

    config = _make_config(Framework.FASTAPI, force=True)
    get_generator(config).generate()

    assert (existing / ".env").read_text() == "SECRET_KEY=my-real-production-secret\n"


def test_failed_generation_cleans_up_new_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    generator = get_generator(config)
    monkeypatch.setattr(
        type(generator), "_scaffold", lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    with pytest.raises(RuntimeError):
        generator.generate()

    assert not (tmp_path / "demo_app").exists()


def test_failed_generation_keeps_preexisting_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "demo_app"
    existing.mkdir()
    (existing / "precious.txt").write_text("keep me")

    config = _make_config(Framework.FASTAPI, force=True)
    generator = get_generator(config)
    monkeypatch.setattr(
        type(generator), "_scaffold", lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    with pytest.raises(RuntimeError):
        generator.generate()

    assert (existing / "precious.txt").read_text() == "keep me"


# ─── DB credentials wired into env templates ────────────────────────────────


def test_env_gets_real_credentials_example_gets_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_name = "mydb"
    config.db_credentials.db_user = "alice"
    config.db_credentials.db_password = "s3cretpw"

    root = get_generator(config).generate()

    env = (root / ".env").read_text()
    example = (root / ".env.example").read_text()
    assert "postgresql+psycopg://alice:s3cretpw@localhost:5432/mydb" in env
    assert "s3cretpw" not in example
    assert "alice:change-me-db-password@localhost:5432/mydb" in example


def test_credentials_default_to_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FLASK)

    root = get_generator(config).generate()

    assert "://demo_app:" in (root / ".env").read_text()
    assert "/demo_app" in (root / ".env").read_text()


def test_django_env_uses_postgres_scheme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.DJANGO)
    config.db_credentials.db_password = "djpw"

    root = get_generator(config).generate()

    assert "DATABASE_URL=postgres://demo_app:djpw@localhost:5432/demo_app" in (
        root / ".env"
    ).read_text()


def test_mongo_only_falls_back_to_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for framework in (Framework.FASTAPI, Framework.FLASK):
        config = _make_config(framework, database=Database.MONGODB)
        config.name = f"demo_{framework.value}"
        root = get_generator(config).generate()
        env = (root / ".env").read_text()
        assert "sqlite:///" in env, framework
        assert "postgresql+psycopg" not in env, framework
        assert "psycopg" not in (root / "pyproject.toml").read_text(), framework


def test_mongo_db_name_flows_into_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI, database=Database.MONGODB)
    config.db_credentials.db_name = "appdata"

    root = get_generator(config).generate()

    assert "MONGODB_DB_NAME=appdata" in (root / ".env").read_text()


def test_invalid_credentials_raise_scaffold_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_user = "bad;user"

    with pytest.raises(base.ScaffoldError):
        get_generator(config)


def test_compose_postgres_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_password = "pgpw"

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "postgres:16-alpine" in compose
    assert "POSTGRES_DB: \"demo_app\"" in compose
    assert "POSTGRES_PASSWORD: \"pgpw\"" in compose
    assert "mongo" not in compose


def test_compose_mongo_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI, database=Database.MONGODB)

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "mongo:7" in compose
    assert "postgres" not in compose


def test_compose_both_and_readme_mentions_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FLASK, database=Database.BOTH)

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "postgres:16-alpine" in compose and "mongo:7" in compose
    assert "docker compose up -d" in (root / "README.md").read_text()


# ─── Django-specific fixes ────────────────────────────────────────────────────


def test_django_migrations_packages_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.DJANGO)).generate()

    assert (root / "apps/users/migrations/__init__.py").is_file()
    assert (root / "apps/authentication/migrations/__init__.py").is_file()


def test_django_pytest_uses_sqlite_test_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.DJANGO)).generate()

    assert 'DJANGO_SETTINGS_MODULE = "config.settings.test"' in (
        root / "pyproject.toml"
    ).read_text()
    test_settings = (root / "config/settings/test.py").read_text()
    assert "TEST_DATABASE_URL" in test_settings
    assert "sqlite" in test_settings


# ─── Bug fixes (alembic & Flask test secrets) ────────────────────────────────


def test_alembic_env_skips_auth_import_when_no_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.FASTAPI, auth=AuthType.NONE)).generate()

    assert "modules.auth" not in (root / "alembic/env.py").read_text()


def test_flask_test_secrets_are_long(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.FLASK)).generate()

    config_py = (root / "src/demo_app/config.py").read_text()
    assert 'JWT_SECRET_KEY: str = "test-secret"' not in config_py
