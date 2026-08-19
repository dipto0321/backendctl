# Tasks: auth-none-consistency

## Implementation

- [x] Flask generator: wrap user model, auth/users blueprints, and auth tests in `if c.auth.value != "none"`
- [x] Flask templates: conditionally drop JWT from pyproject, env, app_init, extensions, config
- [x] Django generator: wrap apps/authentication/* and apps/users/{serializers,views,urls}.py
- [x] Django templates: conditionally include JWT apps, auth classes, SIMPLE_JWT, auth URLs
- [x] Add `tests/test_health.py` to FastAPI, Flask, Django templates
- [x] Extend `tests/test_generators.py` matrix with Flask + Django auth=none cases
- [x] Add specific auth=none assertion tests

## Validation

- [x] `uv run pytest -q` passes (91 tests)
- [x] `uv run ruff check src tests` clean
- [x] `uv run mypy src` clean
