## ADDED Requirements

### Requirement: SHALL validate generated projects in end-to-end CI

Every generated project MUST be created, installed, and tested in CI across
representative framework and database combinations.

#### Scenario: Matrix e2e job succeeds for each framework/database combo
- **WHEN** the e2e CI matrix runs for `{fastapi,flask,django} × postgres`,
  `{fastapi,flask} × mongodb`, and `auth=none` for each framework
- **THEN** `backendctl new`, `uv sync`, and `uv run pytest -q` all succeed
  in the generated project directory

#### Scenario: FastAPI migrations generate in e2e
- **WHEN** the e2e job runs for FastAPI
- **THEN** `DATABASE_URL=sqlite:///./app.db uv run alembic revision --autogenerate -m init` succeeds

#### Scenario: Django migrations run in e2e
- **WHEN** the e2e job runs for Django
- **THEN** `manage.py makemigrations --noinput` and `migrate --noinput` succeed against SQLite

### Requirement: SHALL declare the tool package as typed

A `py.typed` marker MUST be present and included in the built wheel.

#### Scenario: py.typed exists and is packaged
- **WHEN** the tool is built with hatchling
- **THEN** `src/backendctl/py.typed` is included in the wheel

### Requirement: SHALL enforce mypy in CI

The CI pipeline MUST run mypy and fail on type errors.

#### Scenario: CI runs mypy
- **WHEN** a PR is opened or pushed to main
- **THEN** the `mypy` job in `ci.yml` runs `uv run mypy src` and passes

### Requirement: SHALL support --verbose for debugging generation failures

The `new` command MUST accept `--verbose` and propagate exceptions when set.

#### Scenario: --verbose re-raises exceptions
- **WHEN** generation fails and `--verbose` is passed
- **THEN** the full traceback is propagated to the caller instead of being swallowed
