"""AI config file templates: CLAUDE.md, .cursorrules, mcp.json."""

from __future__ import annotations

from backendctl.core.config import Framework, ProjectConfig


def claude_md(config: ProjectConfig) -> str:
    framework_label = {
        Framework.FASTAPI: "FastAPI",
        Framework.FLASK: "Flask",
        Framework.DJANGO: "Django REST Framework",
    }[config.framework]

    provider_note = {
        "claude": "This project uses Claude as the AI coding assistant.",
        "openai": "This project uses OpenAI models as the AI coding assistant.",
    }.get(config.ai.provider.value, "")

    return f"""\
# {config.name}

{provider_note}

## Project

- Framework: {framework_label}
- Language: Python 3.11+
- Package manager: {config.package_manager.value}

## Git Rules

- Use Conventional Commits for commit messages: `type(scope): summary`
- Keep the subject short, imperative, and lowercase unless a proper noun needs capitals
- Use a body with bullet points when the change spans multiple files or has important context
- Commit reproducible project files together when they belong to the same change
  (e.g. `pyproject.toml` and `uv.lock`)
- Do not commit local-only editor or environment files unless intentionally shared
- Prefer focused commits: one logical change per commit

### Commit types

| Type       | When to use                                     |
|------------|-------------------------------------------------|
| `feat`     | A new feature                                   |
| `fix`      | A bug fix                                       |
| `chore`    | Build process, tooling, dependency updates      |
| `docs`     | Documentation only changes                     |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test`     | Adding or updating tests                        |
| `perf`     | Performance improvement                         |
| `ci`       | CI/CD configuration                             |

## Code Style

- Follow PEP 8; line length 100
- Use type hints everywhere
- Prefer `pathlib.Path` over `os.path`
- Use dataclasses or Pydantic models for structured data
- Keep functions small and single-purpose (KISS + SRP)
- Avoid duplicating logic (DRY)
- No magic numbers — use named constants

## Architecture

- Follow the existing folder structure — do not reorganise without discussing first
- Keep business logic in services, not in route handlers
- Keep models thin; avoid fat models
- Write tests for all new public-facing behaviour

## Environment

- Secrets go in `.env` (never commit this file)
- All config is read via `pydantic-settings` (or equivalent)
- `.env.example` documents every variable with safe placeholder values

## Testing

- Use `pytest` for all tests
- Write at least one happy-path and one error-path test per endpoint
- Use fixtures for DB setup/teardown — never share state between tests
"""


def cursorrules(config: ProjectConfig) -> str:
    framework_label = {
        Framework.FASTAPI: "FastAPI",
        Framework.FLASK: "Flask",
        Framework.DJANGO: "Django REST Framework",
    }[config.framework]

    return f"""\
# {config.name} — Cursor Rules

## Stack
- Python 3.11+, {framework_label}
- Package manager: {config.package_manager.value}
- Follow PEP 8, line length 100

## Conventions
- Conventional Commits: `type(scope): summary`
- Type hints everywhere
- Keep route handlers thin — business logic in service layer
- All config via environment variables (pydantic-settings or equivalent)
- No secrets in code or comments

## File structure
- Do not reorganise existing folder structure without explicit instruction
- New features get their own module/blueprint/app folder
- Tests mirror the source structure

## Code quality
- KISS: simple over clever
- DRY: extract repeated logic into helpers/services
- No magic numbers or hardcoded strings — use constants
- Prefer explicit over implicit

## When in doubt
- Ask before making architectural changes
- Prefer smaller, focused commits
- Document non-obvious decisions with inline comments
"""


def mcp_json() -> str:
    return """\
{
  "mcpServers": {}
}
"""
