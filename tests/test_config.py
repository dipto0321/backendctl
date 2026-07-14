"""Unit tests for ProjectConfig logic."""

from __future__ import annotations

import pytest

from backendctl.core.config import (
    Database,
    DatabaseCredentials,
    ProjectConfig,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("MyApp", "myapp"),
        ("my-cool-api", "my_cool_api"),
        ("Some Project", "some_project"),
        ("already_snake", "already_snake"),
    ],
)
def test_slug_is_filesystem_safe(name: str, expected: str) -> None:
    assert ProjectConfig(name=name).slug == expected


@pytest.mark.parametrize(
    ("database", "uses_sql", "uses_mongo"),
    [
        (Database.POSTGRES, True, False),
        (Database.MONGODB, False, True),
        (Database.BOTH, True, True),
    ],
)
def test_database_capability_flags(database: Database, uses_sql: bool, uses_mongo: bool) -> None:
    config = ProjectConfig(database=database)
    assert config.uses_sql is uses_sql
    assert config.uses_mongo is uses_mongo


def test_credentials_resolve_defaults_to_slug() -> None:
    creds = DatabaseCredentials()
    creds.resolve("my_app")
    assert creds.db_name == "my_app"
    assert creds.db_user == "my_app"
    assert len(creds.db_password) >= 16  # auto-generated


def test_credentials_resolve_keeps_explicit_values() -> None:
    creds = DatabaseCredentials(db_name="mydb", db_user="alice", db_password="pw")
    creds.resolve("my_app")
    assert (creds.db_name, creds.db_user, creds.db_password) == ("mydb", "alice", "pw")


@pytest.mark.parametrize("bad", ["1db", "my-db", "my db", "db;drop"])
def test_credentials_resolve_rejects_invalid_identifiers(bad: str) -> None:
    creds = DatabaseCredentials(db_name=bad)
    with pytest.raises(ValueError):
        creds.resolve("my_app")


def test_credentials_url_builds_and_percent_encodes() -> None:
    creds = DatabaseCredentials(db_name="mydb", db_user="alice", db_password="p@ss:word")
    creds.resolve("x")
    assert creds.url("postgresql+psycopg") == (
        "postgresql+psycopg://alice:p%40ss%3Aword@localhost:5432/mydb"
    )
    # explicit password override (used for .env.example)
    assert creds.url("postgres", password="change-me-db-password").endswith(
        "://alice:change-me-db-password@localhost:5432/mydb"
    )


def test_project_config_has_credentials() -> None:
    assert isinstance(ProjectConfig().db_credentials, DatabaseCredentials)
