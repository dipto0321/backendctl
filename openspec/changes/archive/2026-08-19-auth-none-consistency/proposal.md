# auth-none-consistency

## Why

`--auth none` was only honored by the FastAPI generator. Flask and Django always
scaffolded JWT auth, user models, and auth routes, causing generated apps to
crash at import time when the auth dependency was not installed.

## What changes

- **Flask**: conditionally skip user model, auth/users blueprints, and auth tests
  when `auth=none`; drop `flask-jwt-extended` from `pyproject.toml`, `env_example`,
  `app_init`, `extensions`, and `config_py` when auth is disabled.
- **Django**: conditionally skip `apps/authentication/*` and
  `apps/users/{serializers,views,urls}.py` (keep `models.py`+`apps.py` for the
  custom User entity); drop `djangorestframework-simplejwt` from dependencies,
  omit JWT settings from `settings_base`, and conditionally include auth URLs.
- Add `tests/test_health.py` to every generated project so `auth=none` suites
  still have a passing test.

## Capabilities

- scaffolding (MODIFIED)

## Impact

- Flask/Django projects with `--auth none` no longer import missing JWT deps.
- Generated `pyproject.toml` is smaller when auth is disabled.
- All frameworks ship a boot-proving health test regardless of auth choice.
