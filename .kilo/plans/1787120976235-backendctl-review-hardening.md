# backendctl — Review Fixes + OpenSpec Adoption

## Goal

Close the remaining correctness/consistency gaps in the scaffolding tool and its
generated output, wire MongoDB for real, and adopt **OpenSpec** (`@fission-ai/openspec`
v1.9.0, installed) as the single source of truth for spec-driven development.

## Decisions (locked with user)

- **Spec tooling:** OpenSpec (initialize `openspec/`, drive every fix as a change proposal).
- **MongoDB:** fully wire it — working client + sample CRUD resource + health check + tests (not "remove").
- **Scope:** full sweep — auth=none consistency, MongoDB wiring, E402, logging + JSON exception
  handlers, repo hygiene (py.typed, mypy in CI, `--verbose`, stale `dist/` cleanup), automated e2e CI.
- **Out of scope (follow-ups):** FastAPI refresh-token revocation (jti/denylist) — keep documented.

## GitHub Flow (must)

All work lands through **GitHub Flow** — no exceptions:

- Each workstream (or logical group) lives on its own feature branch off `main`:
  `feat/auth-none-consistency`, `feat/mongo-full-wiring`,
  `feat/generated-runtime-quality`, `feat/e2e-and-hygiene`.
- Commits use **conventional commits**: `type(scope): summary`.
- Every PR must pass all required checks before merge:
  - `uv run pytest -q` (tool suite)
  - `uv run ruff check src tests`
  - `uv run ruff format --check src tests`
  - `uv run mypy src`
  - New `e2e.yml` job (generated-project runtime checks)
  - `openspec validate --strict` for each change in the PR
- PR description must reference the OpenSpec change(s) it implements.
- Branch protection on `main` (GitHub settings): required checks, required reviews,
  no force pushes. Enforced by GitHub; not code, but the implementing agent should
  document the expected settings in a `CONTRIBUTING.md` update if branch protection
  is not already enabled.
- Do not commit directly to `main`.

## Key findings driving the work

1. **`--auth none` is only honored by FastAPI.** Flask and Django generators always scaffold JWT auth,
   users models, and auth routes. Django always sets `IsAuthenticated` + `SimpleJWT`. Fix both.
2. **MongoDB half-wired.** FastAPI generates a motor client nobody calls; Flask inits `flask-pymongo`
   (unmaintained) but never uses it. No sample usage, no tests.
3. **Generated Django `config/settings/base.py` has a mid-file `from datetime import timedelta`** →
   ruff `E402` → a scaffolded Django project fails its own lint.
4. **No logging config / JSON error handler** in generated FastAPI/Flask; Django's `core/exceptions.py`
   handler is never wired into `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
5. **No end-to-end CI.** CI only `py_compile`s templates + runs the tool's tests; generated projects
   are never installed/run/tested.
6. **Hygiene:** no `py.typed`, mypy not in CI (`strict=false`), broad `except Exception` in
   `src/backendctl/cli/new.py:434` hides tracebacks (no `--verbose`), stale `dist/` (0.1.0 artifacts).

---

## Workstream 0 — Baseline + OpenSpec bootstrap

- [x] Run `uv sync`, `uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy src` to establish
      a green baseline. Done: 82 tests pass, ruff clean, mypy has 1 pre-existing error in
      `generators/__init__.py:17` to fix in WS4.
- [x] `openspec init --tools kilocode --no-animation` in repo root → created `openspec/config.yaml`,
      `openspec/{specs,changes,archive}/`, `.kilocode/{skills,workflows}/`.
- [x] Filled `openspec/config.yaml` `context:` field with project purpose, stack, commands, invariants.
- [x] Author baseline capability spec `openspec/specs/scaffolding/spec.md` capturing current invariants:
      path-traversal guard, non-empty-dir guard, `.env`-preservation on `--force`, DB-credential flow
      (`resolve`/`url`), placeholder `change-me-db-password`, e2e `py_compile` across the option matrix.
- [x] Create a root `AGENTS.md` pointing at the OpenSpec workflow + build/test commands (none existed).

## Workstream 1 — `feat/auth-none-consistency`: honor `--auth none` in Flask + Django

Change: `openspec/changes/auth-none-consistency/` (proposal.md + tasks.md + spec delta on `scaffolding`).

- [ ] **Flask** (`src/backendctl/generators/flask_gen.py`): wrap user model, `blueprints/auth/*`,
      `blueprints/users/*`, and `tests/test_auth.py` writes in `if c.auth.value != "none"`.
- [ ] **Flask templates** (`src/backendctl/templates/flask.py`): conditionally drop
      `flask-jwt-extended` from `pyproject_toml`, JWT lines from `env_example`, `jwt` import/init from
      `app_init`+`extensions`, JWT settings from `config_py`/`TestConfig`.
- [ ] **Django** (`src/backendctl/generators/django_gen.py`): wrap `apps/authentication/*` writes in
      `if c.auth.value != "none"`; drop `apps/users/{serializers,views,urls}.py` when auth=none (keep
      `models.py`+`apps.py` for the custom User entity).
- [ ] **Django templates** (`src/backendctl/templates/django.py`): conditionally include
      `rest_framework_simplejwt`, `token_blacklist`, `apps.authentication` in `INSTALLED_APPS`; omit
      `DEFAULT_AUTHENTICATION_CLASSES` + `SIMPLE_JWT` when auth=none; set `DEFAULT_PERMISSION_CLASSES`
      to `AllowAny` when auth=none; drop `simplejwt` dep from `pyproject_toml`; omit auth urls from
      `config_urls`.
- [ ] Add `tests/test_health.py` to **every** generated project (all frameworks): asserts `/health`
      returns 200. Gives auth=none suites a non-empty, boot-proving test. Add a Django health view
      (`core/views.py` + `config/urls.py` path) since Django has no `/health` today.
- [ ] Extend `tests/test_generators.py` matrix: add `auth=AuthType.NONE` cases for Flask + Django and
      assert no auth files/imports remain and the health test exists + compiles.

## Workstream 2 — `feat/mongo-full-wiring`: working MongoDB for FastAPI + Flask

Change: `openspec/changes/mongo-full-wiring/` (spec delta on `scaffolding`).

- [ ] **FastAPI** (`src/backendctl/templates/fastapi.py`):
  - New `items_router(c)` → `src/{slug}/modules/items/__init__.py` + `router.py` (GET/POST on a fixed
    `items` collection via `get_mongo_db()`, pydantic `ItemCreate`/`ItemResponse`).
  - `api_v1_router` includes items router under `/items` when `c.uses_mongo`.
  - Add `mongomock-motor` to dev deps when `c.uses_mongo`; `tests_conftest` patches `core.mongo` to use
    `AsyncMongoMockClient`; add `tests/test_items.py` when `c.uses_mongo`.
- [ ] **Flask** (`src/backendctl/templates/flask.py`):
  - Replace `flask-pymongo` with `pymongo` in `pyproject_toml`; new `src/{slug}/mongo.py`
    (`get_db()` via lazy `pymongo.MongoClient(app.config["MONGO_URI"])` + teardown).
  - `extensions.py` drops `PyMongo`; `app_init` registers a `blueprints/items` blueprint when
    `c.uses_mongo`; add `blueprints/items/routes.py` (GET/POST via `get_db()`).
  - Add `mongomock` to dev deps when `c.uses_mongo`; `tests/test_items.py` patches the client.
- [ ] Health: extend generated `/health` (or add `/health/db`) to ping Mongo when `c.uses_mongo`.
- [ ] Tests: extend `tests/test_generators.py` to assert mongo files exist + compile for both frameworks
      and that `flask-pymongo` no longer appears in the Flask `pyproject.toml`.

## Workstream 3 — `feat/generated-runtime-quality`: E402 + logging + error handlers

Change: `openspec/changes/generated-runtime-quality/`.

- [ ] **E402** (`templates/django.py`): move `from datetime import timedelta` to the top of
      `settings_base()` (with the other imports); delete the mid-file line.
- [ ] **FastAPI logging + handler**: add a JSON `@app.exception_handler(Exception)` in `main.py` (or a
      `core/exceptions.py`) returning `{"detail": "Internal server error"}` with 500, and a
      `logging.basicConfig`/`dictConfig` (gated on `settings.DEBUG`).
- [ ] **Flask logging + handler**: register `@app.errorhandler(Exception)` → JSON in `app_init`;
      configure logging in `create_app`.
- [ ] **Django**: wire `REST_FRAMEWORK["EXCEPTION_HANDLER"] = "core.exceptions.custom_exception_handler"`;
      add a `LOGGING` dict to `settings_base`.
- [ ] Tests: assert generated files still compile; spot-check the handler wiring string in each template
      via `tests/test_generators.py`.

## Workstream 4 — `feat/e2e-and-hygiene`: e2e CI + repo hygiene

Change: `openspec/changes/e2e-and-hygiene/`.

- [ ] **Automated e2e job** (`.github/workflows/e2e.yml`): matrix over
      `{fastapi,flask,django} × postgres`, `{fastapi,flask} × mongodb`, and `auth=none` for each
      framework. Per entry: `uv run backendctl new <name> --framework <f> --db <d> --yes --no-git --no-ai`,
      then in the generated dir `uv sync` + `uv run pytest -q`. FastAPI additionally runs
      `DATABASE_URL=sqlite:///./app.db uv run alembic revision --autogenerate -m init`; Django runs
      `uv run python manage.py makemigrations --noinput` + `migrate --noinput` (SQLite). Enable uv caching.
      Note: generated tests already use in-memory SQLite/mongomock, so no services are needed.
- [ ] **`py.typed`**: add empty `src/backendctl/py.typed`; confirm hatchling includes it in the wheel.
- [ ] **mypy in CI**: add `uv run mypy src` to `ci.yml`; fix the pre-existing error in
      `generators/__init__.py:17` ("Cannot instantiate abstract class BaseGenerator").
      Keep `strict=false`.
- [ ] **`--verbose`**: add a `--verbose` flag to `new_command`; when set, re-raise instead of swallowing
      in the `except Exception` block (`src/backendctl/cli/new.py:434`).
- [ ] **Stale artifacts**: delete `dist/backendctl-0.1.0.*` (gitignored; local cleanup only).
- [ ] Tests: add a `test_cli.py` case asserting `--verbose` re-raises (passes through traceback).
- [ ] `ci.yml`: add mypy step; ensure all existing steps are listed as required checks.

## Workstream 5 — Spec-driven wrap-up

- [ ] For each change, write `proposal.md` (Why / What changes / Impact), `tasks.md` (checkbox list
      mirroring the tasks above), and the `specs/scaffolding/spec.md` delta (`## ADDED/MODIFIED Requirements`).
- [ ] Run `openspec validate <change> --strict` for each change (and `openspec list` to confirm discovery).
- [ ] After implementation + green CI, `openspec archive <change>` each change to `openspec/archive/`.

---

## Validation plan

- `uv run pytest -q` (tool suite) green, including the new auth-none + mongo matrix cases.
- `uv run ruff check src tests` and `uv run ruff format --check src tests` clean.
- `uv run mypy src` clean (new CI step).
- `openspec validate --strict` passes for all changes.
- New `e2e.yml` job green in CI (each generated project's own pytest passes; migrations generate).
- All PRs land on feature branches, pass required checks, and merge via GitHub PR.

## Risks / notes

- **mypy** may surface pre-existing errors on first CI run; fix incrementally, do not loosen config
  below current `strict=false` without cause.
- **`mongomock-motor`/`mongomock`** are the standard test doubles for motor/pymongo; if a version clash
  appears, fall back to overriding `get_mongo_db`/`get_db` with an in-memory fake.
- **Django `auth=none`** keeps the custom User model (no JWT endpoints); this intentionally differs from
  FastAPI/Flask (which drop the User model entirely). Document this asymmetry in `project.md`.
- **Alembic autogenerate in e2e** must override `DATABASE_URL` to SQLite (Postgres isn't available in CI).
- **OpenSpec v1.9.0** uses `openspec/config.yaml` for project context (not `project.md`); the
  `openspec new change` scaffold creates proposal + spec delta + design + tasks artifacts.
  Validate each change with `openspec validate <name> --strict` before implementation.

## Open questions (non-blocking)

- Should the FastAPI refresh token gain a `jti` claim now, or remain documented-only? (deferred)
