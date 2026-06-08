"""Tests for project-name validation in the wizard."""

from __future__ import annotations

import pytest

from backendctl.cli.new import _validate_project_name


@pytest.mark.parametrize(
    "name",
    ["myapp", "my-app", "my_app", "App123", "a"],
)
def test_valid_names(name: str) -> None:
    assert _validate_project_name(name) is True


@pytest.mark.parametrize(
    "name",
    ["", "   ", "1app", "-app", "_app", "my app", "my.app", "app!"],
)
def test_invalid_names_return_error_message(name: str) -> None:
    result = _validate_project_name(name)
    assert isinstance(result, str)  # an error message, not True
