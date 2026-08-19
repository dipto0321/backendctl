# e2e-and-hygiene

## Why

The repository had no end-to-end CI to verify that generated projects actually
install and run. Mypy was not checked in CI, there was no `py.typed` marker,
the CLI swallowed tracebacks on failure, and stale `dist/` artifacts cluttered
the workspace.

## What changes

- **e2e CI**: new `.github/workflows/e2e.yml` matrix over
  `{fastapi,flask,django} × postgres`, `{fastapi,flask} × mongodb`,
  and `auth=none` for each framework. Each job generates a project, runs
  `uv sync` + `uv run pytest -q`, and for FastAPI/Django runs migrations.
- **py.typed**: add empty `src/backendctl/py.typed`; hatchling includes it
  via the existing wheel packages config.
- **mypy in CI**: add `uv run mypy src` to `ci.yml`; fix the pre-existing
  `generators/__init__.py:17` abstract class instantiation error.
- **--verbose**: add `--verbose` flag to `new_command`; when set, re-raise
  exceptions instead of swallowing them in the `except Exception` block.
- **dist cleanup**: delete stale `dist/backendctl-0.1.0.*` artifacts.

## Capabilities

- scaffolding (MODIFIED)

## Impact

- Generated projects are verified end-to-end on every PR.
- The tool package declares itself typed.
- CI catches type regressions.
- Debugging generation failures is easier with `--verbose`.
