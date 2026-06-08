"""Unit tests for ProjectConfig logic."""

from __future__ import annotations

import pytest

from backendctl.core.config import (
    Database,
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
