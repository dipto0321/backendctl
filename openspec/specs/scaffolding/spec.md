## Purpose

The scaffolding capability defines what `backendctl new` guarantees: a safe,
valid, batteries-included project is generated for the selected framework and
options, without path traversal, silent data loss, or leaked secrets.

## Requirements

### Requirement: Project names are validated and cannot escape the working directory

The project name, whether from a CLI argument or the wizard, must match a safe
slug and must resolve to a direct child of the current working directory.

#### Scenario: Traversal or absolute paths are rejected
- **WHEN** a user passes a name like `../evil`, `/tmp/evil`, `sub/dir`, or `1app`
- **THEN** the CLI exits non-zero, writes nothing outside the working directory, and no directory is created

#### Scenario: Valid names are accepted
- **WHEN** a user passes a name of letters, digits, hyphens, or underscores starting with a letter
- **THEN** the project is scaffolded under `./<name>`

### Requirement: Scaffolding never silently overwrites user data

A non-empty target directory must not be modified without explicit `--force`,
and secrets in an existing `.env` must be preserved even with `--force`.

#### Scenario: Non-empty directory without force
- **WHEN** the target directory exists and is non-empty and `--force` is not set
- **THEN** generation is refused and existing files are left untouched

#### Scenario: Existing .env is preserved with force
- **WHEN** `--force` is set and the target contains an existing `.env`
- **THEN** the existing `.env` is left intact and not overwritten

### Requirement: Database credentials flow into generated files safely

Resolved database name, user, and password flow into `.env` and
`docker-compose.yml`, while committed files only ever carry a placeholder.

#### Scenario: Real credentials in .env, placeholder in .env.example
- **WHEN** a project is generated with explicit database credentials
- **THEN** `.env` contains the real URL and `.env.example` contains the placeholder `change-me-db-password`

#### Scenario: Defaults resolve from the project slug
- **WHEN** no database name or user is provided
- **THEN** both default to the project slug and a random password is generated

### Requirement: Generated Python files are syntactically valid across the option matrix

Every generated `.py` file must compile, for every framework crossed with
representative option combinations.

#### Scenario: Matrix generation compiles
- **WHEN** generation runs for fastapi/flask/django across postgres/mongodb/both and auth variants
- **THEN** every generated `.py` file passes `py_compile` with no syntax errors

### Requirement: Non-interactive mode respects provided flags

CLI flags must be authoritative: any field set via flag is never re-asked, and
`--yes` accepts defaults for everything else without prompting.

#### Scenario: Flags skip the matching wizard steps
- **WHEN** the user passes `--framework`, `--db`, `--pm`, `--auth`, or `--ai`
- **THEN** the wizard does not prompt for those fields and does not overwrite them

#### Scenario: --yes is fully non-interactive
- **WHEN** `--yes` is passed with a project name
- **THEN** no prompts are shown and the project is generated with defaults

### Requirement: SHALL remove JWT auth artifacts from generated Flask projects when auth=none

When `auth=none` is selected for Flask, the generator SHALL NOT emit any JWT
auth files or dependencies.

#### Scenario: Flask auth=none skips auth files
- **WHEN** a user runs `backendctl new demo --framework flask --auth none --yes`
- **THEN** no `blueprints/auth/`, `blueprints/users/`, `models/user.py`, or
  `tests/test_auth.py` are created, and `pyproject.toml` does not contain
  `flask-jwt-extended`

#### Scenario: Flask auth=none omits JWT from config
- **WHEN** the Flask config template is rendered with `auth=none`
- **THEN** `config.py` does not contain `JWT_SECRET_KEY` or JWT expiry fields,
  and `.env.example` does not contain JWT settings

### Requirement: SHALL remove JWT auth artifacts from generated Django projects when auth=none

When `auth=none` is selected for Django, the generator SHALL NOT emit JWT auth
files or dependencies, but MUST keep the custom User model.

#### Scenario: Django auth=none skips auth files
- **WHEN** a user runs `backendctl new demo --framework django --auth none --yes`
- **THEN** no `apps/authentication/` content (except migrations/__init__.py),
  no `apps/users/serializers.py`, `views.py`, or `urls.py` are created,
  and `pyproject.toml` does not contain `djangorestframework-simplejwt`

#### Scenario: Django auth=none sets permissive default permissions
- **WHEN** the Django settings template is rendered with `auth=none`
- **THEN** `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is set to
  `AllowAny` and `DEFAULT_AUTHENTICATION_CLASSES` is omitted

### Requirement: SHALL include a health test in all generated projects

Every generated project MUST contain a `tests/test_health.py` that asserts
`/health` returns 200, giving `auth=none` suites a non-empty, boot-proving test.

#### Scenario: Health test exists for all frameworks
- **WHEN** generation completes for any framework
- **THEN** `tests/test_health.py` exists and compiles

### Requirement: SHALL include a working items CRUD module in FastAPI projects with MongoDB

When `uses_mongo` is true for FastAPI, the generator MUST emit a functional
items module and wire it into the API router.

#### Scenario: FastAPI MongoDB items module exists
- **WHEN** a user runs `backendctl new demo --framework fastapi --db mongodb --yes`
- **THEN** `src/<slug>/modules/items/__init__.py`, `router.py`, and
  `tests/test_items.py` exist and compile

#### Scenario: FastAPI MongoDB health check endpoint exists
- **WHEN** the FastAPI main template is rendered with `uses_mongo=true`
- **THEN** a `/health/db` route is registered that pings MongoDB

### Requirement: SHALL use plain pymongo instead of flask-pymongo in Flask projects with MongoDB

When `uses_mongo` is true for Flask, the generator MUST use `pymongo` directly
with a `get_db()` helper and teardown.

#### Scenario: Flask MongoDB uses pymongo
- **WHEN** a user runs `backendctl new demo --framework flask --db mongodb --yes`
- **THEN** `pyproject.toml` contains `pymongo` but not `flask-pymongo`,
  `src/<slug>/mongo.py` exists with `get_db()` and `close_mongo()`,
  and `src/<slug>/blueprints/items/routes.py` provides GET/POST

#### Scenario: Flask MongoDB health check endpoint exists
- **WHEN** the Flask app template is rendered with `uses_mongo=true`
- **THEN** a `/health/db` route is registered that pings MongoDB via `mongo.db.command("ping")`

### Requirement: SHALL run MongoDB tests without a live server

Generated test suites MUST use `mongomock` (Flask) or `mongomock-motor` (FastAPI)
so CI does not need a running MongoDB instance.

#### Scenario: FastAPI MongoDB tests patch the client
- **WHEN** `tests/conftest.py` is rendered for FastAPI with `uses_mongo=true`
- **THEN** it monkeypatches `core.mongo._client` with `AsyncMongoMockClient`

#### Scenario: Flask MongoDB tests patch the client
- **WHEN** `tests/conftest.py` is rendered for Flask with `uses_mongo=true`
- **THEN** it monkeypatches `pymongo.MongoClient` with `mongomock.MongoClient()`

### Requirement: SHALL NOT trigger ruff E402 in generated Django settings

The `settings_base()` template MUST have all imports at the top of the file.

#### Scenario: No mid-file imports in Django settings
- **WHEN** the Django settings template is rendered
- **THEN** `config/settings/base.py` compiles without `E402` violations

### Requirement: SHALL return JSON 500 errors from generated FastAPI apps

FastAPI apps MUST have a generic exception handler that returns JSON instead of
HTML tracebacks.

#### Scenario: FastAPI unhandled exception returns JSON
- **WHEN** an unhandled exception occurs in a generated FastAPI app
- **THEN** the response is `{"detail": "Internal server error"}` with status 500

### Requirement: SHALL return JSON 500 errors from generated Flask apps

Flask apps MUST have a generic error handler that returns JSON instead of HTML
tracebacks.

#### Scenario: Flask unhandled exception returns JSON
- **WHEN** an unhandled exception occurs in a generated Flask app
- **THEN** the response is `{"detail": "Internal server error"}` with status 500

### Requirement: SHALL wire custom exception handler in generated Django DRF apps

Django settings MUST wire `core.exceptions.custom_exception_handler` into
`REST_FRAMEWORK`.

#### Scenario: Django DRF exception handler is configured
- **WHEN** the Django settings template is rendered
- **THEN** `REST_FRAMEWORK["EXCEPTION_HANDLER"]` equals `"core.exceptions.custom_exception_handler"`

### Requirement: SHALL configure development logging in generated apps

When `DEBUG=true`, generated apps MUST configure basic logging to stdout.

#### Scenario: FastAPI logs in debug mode
- **WHEN** a generated FastAPI app starts with `DEBUG=true`
- **THEN** `logging.basicConfig(level=logging.INFO)` is called

#### Scenario: Flask logs in debug mode
- **WHEN** a generated Flask app starts with `DEBUG=true`
- **THEN** `logging.basicConfig(level=logging.INFO)` is called

#### Scenario: Django logging dict is present
- **WHEN** the Django settings template is rendered
- **THEN** a `LOGGING` dict with a console handler is defined

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
