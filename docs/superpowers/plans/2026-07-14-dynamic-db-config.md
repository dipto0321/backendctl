# Dynamic DB Config + Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wizard/flag-driven database credentials that flow into generated `.env` and a new `docker-compose.yml`, plus fixes for the six bugs confirmed in the 2026-07-14 review.

**Architecture:** A `DatabaseCredentials` dataclass on `ProjectConfig` is resolved (defaults filled) once in `BaseGenerator.__init__`; template functions read the resolved values. `.env.example` always gets a password placeholder; `.env` gets the real password. `docker-compose.yml` is a new common template.

**Tech Stack:** Python 3.11+, typer, questionary, rich, pytest. Spec: `docs/superpowers/specs/2026-07-14-dynamic-db-config-design.md`.

## Global Constraints

- Repo root: `/Users/dipto/My_Works/Projects/Backend setup cli tool` (note: path contains spaces — always quote it).
- Run tests with `uv run pytest -q`, lint with `uv run ruff check src tests`.
- DB identifier validation regex (names and users): `^[a-zA-Z_][a-zA-Z0-9_]*$`.
- Password placeholder literal (committed files only): `change-me-db-password`.
- The real password must NEVER appear in `.env.example`, `README.md`, or any committed template output. It may appear in `.env` and `docker-compose.yml` (both gitignored? compose is committed — password there is acceptable per spec since compose is the local-dev database).
- Auto-generated password: `secrets.token_urlsafe(16)`.
- Mongo runs unauthenticated at `localhost:27017`; only its db name is configurable.
- URL schemes: FastAPI/Flask `postgresql+psycopg`, Django `postgres`.
- Commit after every task with a conventional-commit message. Work happens on branch `feat/dynamic-db-config`.

---

### Task 1: `DatabaseCredentials` model

**Files:**
- Modify: `src/backendctl/core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `DatabaseCredentials` dataclass with fields `db_name: str = ""`, `db_user: str = ""`, `db_password: str = ""`, `host: str = "localhost"`, `port: int = 5432`; methods `resolve(slug: str) -> None` (fills defaults, raises `ValueError` on invalid name/user) and `url(scheme: str, password: str | None = None) -> str`. Also `ProjectConfig.db_credentials: DatabaseCredentials` and module-level `DB_IDENT_RE`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_config.py`:

```python
import pytest

from backendctl.core.config import DatabaseCredentials, ProjectConfig


def test_credentials_resolve_defaults_to_slug():
    creds = DatabaseCredentials()
    creds.resolve("my_app")
    assert creds.db_name == "my_app"
    assert creds.db_user == "my_app"
    assert len(creds.db_password) >= 16  # auto-generated


def test_credentials_resolve_keeps_explicit_values():
    creds = DatabaseCredentials(db_name="mydb", db_user="alice", db_password="pw")
    creds.resolve("my_app")
    assert (creds.db_name, creds.db_user, creds.db_password) == ("mydb", "alice", "pw")


@pytest.mark.parametrize("bad", ["1db", "my-db", "my db", "db;drop"])
def test_credentials_resolve_rejects_invalid_identifiers(bad):
    creds = DatabaseCredentials(db_name=bad)
    with pytest.raises(ValueError):
        creds.resolve("my_app")


def test_credentials_url_builds_and_percent_encodes():
    creds = DatabaseCredentials(db_name="mydb", db_user="alice", db_password="p@ss:word")
    creds.resolve("x")
    assert creds.url("postgresql+psycopg") == (
        "postgresql+psycopg://alice:p%40ss%3Aword@localhost:5432/mydb"
    )
    # explicit password override (used for .env.example)
    assert creds.url("postgres", password="change-me-db-password").endswith(
        "://alice:change-me-db-password@localhost:5432/mydb"
    )


def test_project_config_has_credentials():
    assert isinstance(ProjectConfig().db_credentials, DatabaseCredentials)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL / ERROR with `ImportError: cannot import name 'DatabaseCredentials'`

- [ ] **Step 3: Implement** — in `src/backendctl/core/config.py`, add imports and the dataclass (above `ProjectConfig`), and the field on `ProjectConfig`:

```python
import re
import secrets
from urllib.parse import quote

# Safe for POSTGRES_DB/POSTGRES_USER and for URLs without quoting.
DB_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass
class DatabaseCredentials:
    """PostgreSQL credentials (Mongo shares db_name; runs unauthenticated locally)."""

    db_name: str = ""  # resolves to project slug
    db_user: str = ""  # resolves to project slug
    db_password: str = ""  # resolves to a random token
    host: str = "localhost"
    port: int = 5432

    def resolve(self, slug: str) -> None:
        """Fill unset fields with defaults; validate identifiers."""
        self.db_name = (self.db_name or slug).strip()
        self.db_user = (self.db_user or slug).strip()
        for label, value in (("database name", self.db_name), ("database user", self.db_user)):
            if not DB_IDENT_RE.match(value):
                raise ValueError(
                    f"Invalid {label} {value!r}: use only letters, digits, and "
                    "underscores; must not start with a digit."
                )
        if not self.db_password:
            self.db_password = secrets.token_urlsafe(16)

    def url(self, scheme: str, password: str | None = None) -> str:
        pw = quote(self.db_password if password is None else password, safe="")
        return f"{scheme}://{self.db_user}:{pw}@{self.host}:{self.port}/{self.db_name}"
```

On `ProjectConfig`, after the `ai` field:

```python
    db_credentials: DatabaseCredentials = field(default_factory=DatabaseCredentials)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config.py -q` → PASS. Then `uv run pytest -q` (whole suite) → all pass.

- [ ] **Step 5: Commit**

```bash
git add src/backendctl/core/config.py tests/test_config.py
git commit -m "feat: add DatabaseCredentials config model"
```

---

### Task 2: Resolve credentials in BaseGenerator; wire into env templates (incl. mongo-only sqlite fallback)

**Files:**
- Modify: `src/backendctl/generators/base.py` (init), `src/backendctl/generators/fastapi_gen.py`, `src/backendctl/generators/flask_gen.py`, `src/backendctl/generators/django_gen.py` (env writes), `src/backendctl/templates/common.py` (placeholder constant), `src/backendctl/templates/fastapi.py`, `src/backendctl/templates/flask.py`, `src/backendctl/templates/django.py` (env_example functions)
- Test: `tests/test_generators.py`

**Interfaces:**
- Consumes: `DatabaseCredentials.resolve/url` from Task 1.
- Produces: `templates.common.DB_PASSWORD_PLACEHOLDER = "change-me-db-password"`; every framework's `env_example(c, db_password: str | None = None)` — `None` means "use the placeholder". Generators resolved credentials are available to all templates as `c.db_credentials`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_generators.py`:

```python
def test_env_gets_real_credentials_example_gets_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_name = "mydb"
    config.db_credentials.db_user = "alice"
    config.db_credentials.db_password = "s3cretpw"

    root = get_generator(config).generate()

    env = (root / ".env").read_text()
    example = (root / ".env.example").read_text()
    assert "postgresql+psycopg://alice:s3cretpw@localhost:5432/mydb" in env
    assert "s3cretpw" not in example
    assert "alice:change-me-db-password@localhost:5432/mydb" in example


def test_credentials_default_to_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FLASK)

    root = get_generator(config).generate()

    assert "://demo_app:" in (root / ".env").read_text()
    assert "/demo_app" in (root / ".env").read_text()


def test_django_env_uses_postgres_scheme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.DJANGO)
    config.db_credentials.db_password = "djpw"

    root = get_generator(config).generate()

    assert "DATABASE_URL=postgres://demo_app:djpw@localhost:5432/demo_app" in (
        root / ".env"
    ).read_text()


def test_mongo_only_falls_back_to_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for framework in (Framework.FASTAPI, Framework.FLASK):
        config = _make_config(framework, database=Database.MONGODB)
        config.name = f"demo_{framework.value}"
        root = get_generator(config).generate()
        env = (root / ".env").read_text()
        assert "sqlite:///" in env, framework
        assert "postgresql+psycopg" not in env, framework
        assert "psycopg" not in (root / "pyproject.toml").read_text(), framework


def test_mongo_db_name_flows_into_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI, database=Database.MONGODB)
    config.db_credentials.db_name = "appdata"

    root = get_generator(config).generate()

    assert "MONGODB_DB_NAME=appdata" in (root / ".env").read_text()


def test_invalid_credentials_raise_scaffold_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_user = "bad;user"

    with pytest.raises(base.ScaffoldError):
        get_generator(config)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generators.py -q` — the six new tests FAIL (old URLs / no resolution).

- [ ] **Step 3: Implement.**

`src/backendctl/generators/base.py` — at the end of `__init__` (after the parent-dir check):

```python
        try:
            config.db_credentials.resolve(config.slug)
        except ValueError as exc:
            raise ScaffoldError(str(exc)) from exc
```

`src/backendctl/templates/common.py` — add near the top:

```python
DB_PASSWORD_PLACEHOLDER = "change-me-db-password"
```

`src/backendctl/templates/fastapi.py` — replace `env_example` signature/body:

```python
def env_example(c: ProjectConfig, db_password: str | None = None) -> str:
    from backendctl.templates.common import DB_PASSWORD_PLACEHOLDER

    creds = c.db_credentials
    mongo_line = (
        f"\nMONGODB_URL=mongodb://localhost:27017\nMONGODB_DB_NAME={creds.db_name}\n"
        if c.uses_mongo
        else ""
    )
    if c.uses_sql:
        db_url = creds.url("postgresql+psycopg", password=db_password or DB_PASSWORD_PLACEHOLDER)
    else:
        # No PostgreSQL selected: auth/user data lives in SQLite (no extra driver).
        db_url = "sqlite:///./app.db"
```

…and in the returned f-string replace the hardcoded line
`DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/{c.slug}` with `DATABASE_URL={db_url}`.

`src/backendctl/templates/flask.py` — same pattern:

```python
def env_example(c: ProjectConfig, db_password: str | None = None) -> str:
    from backendctl.templates.common import DB_PASSWORD_PLACEHOLDER

    creds = c.db_credentials
    mongo_block = (
        f"\n# MongoDB\nMONGO_URI=mongodb://localhost:27017/{creds.db_name}\n"
        if c.uses_mongo
        else ""
    )
    if c.uses_sql:
        db_url = creds.url("postgresql+psycopg", password=db_password or DB_PASSWORD_PLACEHOLDER)
    else:
        db_url = "sqlite:///app.db"
```

…and `DATABASE_URL={db_url}` in the body.

`src/backendctl/templates/django.py` — same pattern (Django always uses SQL):

```python
def env_example(c: ProjectConfig, db_password: str | None = None) -> str:
    from backendctl.templates.common import DB_PASSWORD_PLACEHOLDER

    db_url = c.db_credentials.url("postgres", password=db_password or DB_PASSWORD_PLACEHOLDER)
```

…and `DATABASE_URL={db_url}` in the body (delete the old `pg = ...` line).

Generators — pass the real password when writing `.env` (keep the existing secret-key replaces):

`fastapi_gen.py`:

```python
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c, db_password=c.db_credentials.db_password).replace(
                "change-me-to-a-long-random-string", _random_key()
            ),
        )
```

`flask_gen.py`:

```python
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c, db_password=c.db_credentials.db_password)
            .replace("change-me-to-a-long-random-string", secrets.token_hex(32))
            .replace("another-long-random-secret", secrets.token_hex(32)),
        )
```

`django_gen.py`:

```python
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c, db_password=c.db_credentials.db_password).replace(
                "change-me-to-a-long-random-string", secrets.token_hex(32)
            ),
        )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass (matrix compile tests cover the changed templates).

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "feat: wire database credentials into generated .env files

Mongo-only projects fall back to SQLite for the SQL layer instead of
shipping a postgres URL without the psycopg driver."
```

---

### Task 3: docker-compose.yml template + generated README quickstart

**Files:**
- Modify: `src/backendctl/templates/common.py` (new `docker_compose()`, README changes), `src/backendctl/generators/base.py` (`_write_common_files`)
- Test: `tests/test_generators.py`

**Interfaces:**
- Consumes: resolved `c.db_credentials` (Task 2).
- Produces: `templates.common.docker_compose(c: ProjectConfig) -> str`; `docker-compose.yml` written by `_write_common_files`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_generators.py`:

```python
def test_compose_postgres_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI)
    config.db_credentials.db_password = "pgpw"

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "postgres:16-alpine" in compose
    assert "POSTGRES_DB: \"demo_app\"" in compose
    assert "POSTGRES_PASSWORD: \"pgpw\"" in compose
    assert "mongo" not in compose


def test_compose_mongo_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FASTAPI, database=Database.MONGODB)

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "mongo:7" in compose
    assert "postgres" not in compose


def test_compose_both_and_readme_mentions_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = _make_config(Framework.FLASK, database=Database.BOTH)

    root = get_generator(config).generate()

    compose = (root / "docker-compose.yml").read_text()
    assert "postgres:16-alpine" in compose and "mongo:7" in compose
    assert "docker compose up -d" in (root / "README.md").read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generators.py -q` — new tests FAIL (`docker-compose.yml` missing).

- [ ] **Step 3: Implement.**

`src/backendctl/templates/common.py` — add (uses `json.dumps` so any password is a valid YAML scalar):

```python
import json


def docker_compose(c: ProjectConfig) -> str:
    creds = c.db_credentials
    services: list[str] = []
    volumes: list[str] = []

    if c.uses_sql:
        services.append(
            f"""\
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: {json.dumps(creds.db_name)}
      POSTGRES_USER: {json.dumps(creds.db_user)}
      POSTGRES_PASSWORD: {json.dumps(creds.db_password)}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {creds.db_user} -d {creds.db_name}"]
      interval: 5s
      timeout: 3s
      retries: 10
"""
        )
        volumes.append("  postgres_data:")

    if c.uses_mongo:
        services.append(
            """\
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
"""
        )
        volumes.append("  mongo_data:")

    return "services:\n" + "\n".join(services) + "\nvolumes:\n" + "\n".join(volumes) + "\n"
```

`src/backendctl/generators/base.py` — in `_write_common_files`, import `docker_compose` alongside the others and add before `print_info`:

```python
        self._write("docker-compose.yml", docker_compose(self.config))
```

(Every `Database` value uses at least one engine, so it is always written.)

`common.py` `readme()` — in the Quickstart block, insert between step 2 (env) and the migrations step:

```
# 3. Start the database (Docker)
docker compose up -d
```

renumber migrations to 4 and dev server to 5. Also append to the mongo case: inside `readme()`, after the Quickstart block, add when `c.uses_mongo and not c.uses_sql`:

```python
    mongo_note = (
        "\n> **Note:** auth/user data is stored in SQLite (`app.db`); MongoDB is wired "
        "for application data.\n"
        if c.uses_mongo and not c.uses_sql
        else ""
    )
```

and interpolate `{mongo_note}` right after the Quickstart code fence.

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass. Sanity: `uv run python -c "from backendctl.core.config import ProjectConfig; from backendctl.templates.common import docker_compose; c=ProjectConfig(name='x'); c.db_credentials.resolve(c.slug); print(docker_compose(c))"` prints valid YAML.

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "feat: generate docker-compose.yml for the selected database"
```

---

### Task 4: Wizard prompts + CLI flags for credentials

**Files:**
- Modify: `src/backendctl/cli/new.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `DB_IDENT_RE` from `core.config` (Task 1); `provided` set mechanism already in `new_command`.
- Produces: flags `--db-name`, `--db-user`, `--db-password`; wizard prompts after the database step; provided-keys `"db_name"`, `"db_user"`, `"db_password"`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_cli.py`:

```python
def _stub_generation(monkeypatch):
    from backendctl.generators import base

    monkeypatch.setattr(base.BaseGenerator, "_install_deps", lambda self: None)
    monkeypatch.setattr(base.BaseGenerator, "_git_init", lambda self: None)
    monkeypatch.setattr("backendctl.cli.new.run_preflight", lambda *a, **k: True)


def test_db_flags_flow_into_generated_env(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(
        app,
        [
            "new", "demo", "--framework", "fastapi", "--db", "postgres",
            "--db-name", "customdb", "--db-user", "alice", "--db-password", "pw12345",
            "--yes", "--no-git", "--no-ai",
        ],
    )

    assert result.exit_code == 0, result.output
    env = (tmp_path / "demo" / ".env").read_text()
    assert "postgresql+psycopg://alice:pw12345@localhost:5432/customdb" in env


@pytest.mark.parametrize("flag", ["--db-name", "--db-user"])
def test_invalid_db_identifier_flags_rejected(flag: str, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(app, ["new", "demo", flag, "bad;name", "--yes", "--no-git", "--no-ai"])

    assert result.exit_code == 1
    assert not (tmp_path / "demo").exists()


def test_yes_generates_random_password(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(app, ["new", "demo", "--yes", "--no-git", "--no-ai"])

    assert result.exit_code == 0, result.output
    env = (tmp_path / "demo" / ".env").read_text()
    assert "change-me-db-password" not in env
    assert "user:password@" not in env
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -q` — FAIL (`No such option: --db-name`; the `--yes` test fails on the old placeholder URL only if Task 2 missed it — it should already pass; keep it as a regression guard).

- [ ] **Step 3: Implement** in `src/backendctl/cli/new.py`.

Import `DB_IDENT_RE` in the existing `core.config` import block. Add helpers next to `_validate_project_name`:

```python
def _validate_db_identifier(value: str) -> bool | str:
    if not value.strip():
        return "Value cannot be empty."
    if not DB_IDENT_RE.match(value.strip()):
        return "Use only letters, digits, and underscores; must not start with a digit."
    return True
```

Add a wizard step function (below `_run_wizard`'s step 5, called from inside `_run_wizard` right after the database step):

```python
def _ask_db_credentials(config: ProjectConfig, provided: set[str], assume_yes: bool) -> None:
    """Prompt for DB name/user/password. Unset fields resolve to defaults later."""
    if assume_yes:
        return
    if "db_name" not in provided:
        config.db_credentials.db_name = _ask(
            questionary.text,
            message="Database name:",
            default=config.slug,
            validate=_validate_db_identifier,
        ).strip()
    if config.uses_sql:
        if "db_user" not in provided:
            config.db_credentials.db_user = _ask(
                questionary.text,
                message="Database user:",
                default=config.slug,
                validate=_validate_db_identifier,
            ).strip()
        if "db_password" not in provided:
            config.db_credentials.db_password = _ask(
                questionary.password,
                message="Database password (leave empty to auto-generate):",
            )
```

In `_run_wizard`, after the `# 5. Database` block ends, add:

```python
    # 5b. Database credentials
    _ask_db_credentials(config, provided, assume_yes)
```

In `new_command`, add the three options (after the `ai` option):

```python
    db_name: Optional[str] = typer.Option(
        None, "--db-name", help="Database name (default: project slug)."
    ),
    db_user: Optional[str] = typer.Option(
        None, "--db-user", help="PostgreSQL user (default: project slug)."
    ),
    db_password: Optional[str] = typer.Option(
        None, "--db-password", help="PostgreSQL password (default: auto-generated)."
    ),
```

…and in the flag-seeding section (after the `auth` block):

```python
    for flag, field_name, value in (
        ("--db-name", "db_name", db_name),
        ("--db-user", "db_user", db_user),
    ):
        if value:
            check = _validate_db_identifier(value)
            if check is not True:
                print_error(f"Invalid {flag} '{value}': {check}")
                raise typer.Exit(1)
            setattr(config.db_credentials, field_name, value.strip())
            provided.add(field_name)
    if db_password:
        config.db_credentials.db_password = db_password
        provided.add("db_password")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add src/backendctl/cli/new.py tests/test_cli.py
git commit -m "feat: add --db-name/--db-user/--db-password flags and wizard prompts"
```

---

### Task 5: Django fixes — migrations packages + SQLite test settings

**Files:**
- Modify: `src/backendctl/generators/django_gen.py`, `src/backendctl/templates/django.py`
- Test: `tests/test_generators.py`

**Interfaces:**
- Produces: `templates.django.settings_test() -> str`; generated files `apps/users/migrations/__init__.py`, `apps/authentication/migrations/__init__.py`, `config/settings/test.py`; pytest settings module `config.settings.test`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_generators.py`:

```python
def test_django_migrations_packages_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.DJANGO)).generate()

    assert (root / "apps/users/migrations/__init__.py").is_file()
    assert (root / "apps/authentication/migrations/__init__.py").is_file()


def test_django_pytest_uses_sqlite_test_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.DJANGO)).generate()

    assert 'DJANGO_SETTINGS_MODULE = "config.settings.test"' in (
        root / "pyproject.toml"
    ).read_text()
    test_settings = (root / "config/settings/test.py").read_text()
    assert "TEST_DATABASE_URL" in test_settings
    assert "sqlite" in test_settings
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generators.py -q` — both FAIL.

- [ ] **Step 3: Implement.**

`src/backendctl/templates/django.py`:
- In `pyproject_toml`, change `DJANGO_SETTINGS_MODULE = "config.settings.development"` to `DJANGO_SETTINGS_MODULE = "config.settings.test"`.
- Add after `settings_production()`:

```python
def settings_test() -> str:
    return """\
from config.settings.base import *  # noqa: F401, F403
from config.settings.base import env

DEBUG = True

# Tests run on SQLite by default — no PostgreSQL server required.
DATABASES = {"default": env.db("TEST_DATABASE_URL", default="sqlite:///test.db")}
"""
```

`src/backendctl/generators/django_gen.py` — in `_scaffold`:
- after the `settings/production.py` write: `self._write("config/settings/test.py", t.settings_test())`
- after the users-app writes: `self._write("apps/users/migrations/__init__.py", "")`
- after the authentication-app writes: `self._write("apps/authentication/migrations/__init__.py", "")`

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "fix: Django scaffold gets migrations packages and SQLite test settings

Bare 'manage.py makemigrations' previously detected nothing (no
migrations package), and 'pytest' required a running PostgreSQL."
```

---

### Task 6: Alembic conditional auth import + Flask test secrets

**Files:**
- Modify: `src/backendctl/templates/fastapi.py` (`alembic_env`), `src/backendctl/templates/flask.py` (`config_py`)
- Test: `tests/test_generators.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_generators.py`:

```python
def test_alembic_env_skips_auth_import_when_no_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.FASTAPI, auth=AuthType.NONE)).generate()

    assert "modules.auth" not in (root / "alembic/env.py").read_text()


def test_flask_test_secrets_are_long(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = get_generator(_make_config(Framework.FLASK)).generate()

    config_py = (root / "src/demo_app/config.py").read_text()
    assert 'JWT_SECRET_KEY: str = "test-secret"' not in config_py
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generators.py -q` — both FAIL.

- [ ] **Step 3: Implement.**

`templates/fastapi.py` `alembic_env` — replace the unconditional import line with an interpolated one:

```python
def alembic_env(c: ProjectConfig) -> str:
    models_import = (
        f"\n# Import all models so Alembic can detect them\n"
        f"from {c.slug}.modules.auth.models import User  # noqa: F401\n"
        if c.auth.value != "none"
        else ""
    )
```

…and in the template body replace the two lines

```
# Import all models so Alembic can detect them
from {c.slug}.modules.auth.models import User  # noqa: F401
```

with `{models_import}`.

`templates/flask.py` `config_py` — in `TestConfig`, replace both `"test-secret"` values with a 64-char literal:

```python
    JWT_SECRET_KEY: str = "test-secret-key-0123456789abcdef0123456789abcdef0123456789abcdef"
    SECRET_KEY: str = "test-secret-key-0123456789abcdef0123456789abcdef0123456789abcdef"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "fix: alembic env skips auth import when auth is disabled; longer Flask test secrets"
```

---

### Task 7: Framework-aware success panel, docs, version bump, e2e verification

**Files:**
- Modify: `src/backendctl/core/config.py` (labels), `src/backendctl/core/console.py` (`print_done`), `src/backendctl/cli/new.py` (call site), `src/backendctl/templates/common.py` + `src/backendctl/templates/ai.py` (use shared labels), `README.md`, `pyproject.toml` + `src/backendctl/__init__.py` (version 0.3.0)
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `core.config.FRAMEWORK_LABELS: dict[Framework, str]`; `print_done(config: ProjectConfig, path: str) -> None`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_cli.py`:

```python
def test_success_panel_is_framework_aware(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _stub_generation(monkeypatch)

    result = runner.invoke(
        app, ["new", "demo", "-f", "flask", "--yes", "--no-git", "--no-ai"]
    )

    assert result.exit_code == 0, result.output
    assert "flask" in result.output
    assert "cp .env.example" not in result.output
    assert "fastapi dev" not in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -q` — FAILS (panel still says `cp .env.example` / `fastapi dev`).

- [ ] **Step 3: Implement.**

`core/config.py` — add below the `Framework` enum:

```python
FRAMEWORK_LABELS = {
    Framework.FASTAPI: "FastAPI",
    Framework.FLASK: "Flask",
    Framework.DJANGO: "Django REST Framework",
}
```

`core/console.py` — replace `print_done` (add imports `from backendctl.core.config import FRAMEWORK_LABELS, Framework, PackageManager, ProjectConfig`):

```python
def print_done(config: ProjectConfig, path: str) -> None:
    run_cmd = {
        Framework.FASTAPI: f"fastapi dev src/{config.slug}/main.py",
        Framework.FLASK: f'flask --app "{config.slug}:create_app()" run --debug',
        Framework.DJANGO: "python manage.py runserver",
    }[config.framework]
    if config.package_manager is PackageManager.UV:
        run_cmd = f"uv run {run_cmd}"
    else:
        run_cmd = f"source .venv/bin/activate && {run_cmd}"

    lines = [
        f"[bold green]Project [cyan]{config.name}[/cyan] created![/bold green]",
        "",
        f"  [dim]Framework :[/dim]  {FRAMEWORK_LABELS[config.framework]}",
        f"  [dim]Location  :[/dim]  {path}",
        "",
        "  [bold]Next steps:[/bold]",
        f"    [cyan]cd {config.name}[/cyan]",
        "    [cyan]docker compose up -d[/cyan]  [dim]# start the database[/dim]",
        "    [dim]# .env was created with generated secrets — review it[/dim]",
        f"    [cyan]{run_cmd}[/cyan]",
    ]
    console.print(Panel("\n".join(lines), border_style="green", padding=(0, 2)))
```

`cli/new.py` — delete the local `framework_label` mapping at the end of `new_command` and call `print_done(config, str(project_path))`.

`templates/common.py` and `templates/ai.py` — replace their local label dicts with `from backendctl.core.config import FRAMEWORK_LABELS` (`label = FRAMEWORK_LABELS[c.framework]`).

`README.md` (tool repo) — in the flag table add:

```
| `--db-name` | string | Database name (default: project slug). |
| `--db-user` | string | PostgreSQL user (default: project slug). |
| `--db-password` | string | PostgreSQL password (default: auto-generated). |
```

In the wizard step list, after step 4 add: `5. Database name / user / password (defaults: slug / slug / auto-generated)` (renumber the rest). In "What you get", mention the generated `docker-compose.yml` and that `.env` ships with working credentials matching it.

Version bump: `pyproject.toml` `version = "0.3.0"`; `src/backendctl/__init__.py` `__version__ = "0.3.0"`.

- [ ] **Step 4: Run full suite + lint**

Run: `uv run pytest -q` → all pass. `uv run ruff check src tests` → clean.

- [ ] **Step 5: End-to-end verification** (scratchpad, real installs):

```bash
cd <scratchpad>/e2e-v2
REPO="/Users/dipto/My_Works/Projects/Backend setup cli tool"
uv run --project "$REPO" backendctl new fastapiapp -f fastapi --db postgres --yes --no-ai --no-git
uv run --project "$REPO" backendctl new flaskapp   -f flask   --db postgres --yes --no-ai --no-git
uv run --project "$REPO" backendctl new djangoapp  -f django  --db postgres --yes --no-ai --no-git
uv run --project "$REPO" backendctl new mongoapp   -f fastapi --db mongodb  --yes --no-ai --no-git
uv run --project "$REPO" backendctl new noauthapp  -f fastapi --auth none   --yes --no-ai --no-git
for d in fastapiapp flaskapp djangoapp mongoapp; do (cd $d && uv run pytest -q); done
(cd noauthapp && uv run alembic revision --autogenerate -m init)   # must NOT crash
(cd djangoapp && uv run python manage.py makemigrations)           # must create 0001_initial
docker compose -f fastapiapp/docker-compose.yml config              # valid YAML (if docker present)
```

Expected: every generated suite passes with no PostgreSQL running; makemigrations creates the users migration; alembic autogenerate succeeds.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: framework-aware success panel, docs, bump to 0.3.0"
```

---

## Final step: PR (GitHub flow)

```bash
git push -u origin feat/dynamic-db-config
gh pr create --title "feat: dynamic database credentials + docker-compose generation" --body "..."
```

PR body summarizes the feature and the six review fixes; ends with the standard generation footer.
