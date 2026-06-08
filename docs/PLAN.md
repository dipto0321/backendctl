# backendctl — Improvement Plan

Status legend: `[ ]` todo · `[x]` done

## Context
`backendctl` is a Typer + Rich + questionary CLI that scaffolds production-ready
Python backends (FastAPI / Flask / Django REST Framework) with auth, DB, rate
limiting, tests, and optional AI-assistant config files. Source lives in
`src/backendctl/`. Templates are plain Python functions returning file contents
(f-strings) under `src/backendctl/templates/`; generators in
`src/backendctl/generators/` write them to disk.

## Findings

### Critical
- [x] `pyproject.toml` sets `readme = "README.md"` but no README exists →
  `uv sync` / `pip install` / build **fail**. Fixed by adding README.md.

### Project hygiene
- [x] No `README.md` (user documentation).
- [x] No `LICENSE` file though `license = MIT` is declared.
- [x] No top-level `.gitignore` → `__pycache__/`, `.DS_Store` get tracked.
- [x] No tests for the CLI itself.
- [x] No CI workflow.

### Bugs in generated templates
- [x] **Flask** `config.py`: class body runs `os.environ["SECRET_KEY"]` at import
  time, so importing the app (incl. pytest) raises `KeyError` when `.env` isn't
  loaded. Fix: `load_dotenv()` in config + keep secrets required for prod.
- [x] **FastAPI** `UserResponse.id: str` while `User.id` is `uuid.UUID`. Pydantic v2
  does not coerce UUID→str → `/register` & `/me` 500. Fix: `id: uuid.UUID`.
- [x] **FastAPI** `session.get(User, payload["sub"])` passes a `str` for a UUID PK.
  Fix: convert to `uuid.UUID(...)` in `deps.py` and `service.py`.
- [x] **FastAPI** CORS `allow_origins` receives `AnyHttpUrl` objects, not `str`.
  Fix: `[str(o) for o in settings.BACKEND_CORS_ORIGINS]`.
- [x] **Django** `config/urls.py` includes `apps.authentication.urls` twice. Remove dup.
- [x] **Django** `authentication/views.py` imports `TokenObtainPairView`,
  `TokenRefreshView` but never uses them (ruff F401). Remove.

## Execution order
1. [x] Save this plan.
2. [x] Add `README.md`, `LICENSE`, top-level `.gitignore`.
3. [x] Fix template bugs (Flask, FastAPI, Django).
4. [x] Add CLI test suite (`tests/`) — config logic + generators produce
   files whose every generated `.py` compiles, across framework/option matrix.
5. [x] Add GitHub Actions CI (lint + test).
6. [x] Verify: `uv sync`, `ruff check`, `pytest` all green.

## Notes / deliberate non-changes
- Django + MongoDB uses `djongo`, which is effectively unmaintained on Django 5;
  left as-is (documented tradeoff, out of scope for this pass).
- Django generator always scaffolds the auth app even when `auth=none`; minor
  inconsistency vs FastAPI/Flask, left for a future pass.
- Generated-project runtime (installing FastAPI/Django/Flask + running their
  test suites) is not exercised here to keep the dependency footprint small;
  generated code is validated via `py_compile` across the option matrix instead.
