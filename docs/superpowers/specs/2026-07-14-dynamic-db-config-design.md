# Dynamic database configuration + review fixes — Design

**Date:** 2026-07-14 · **Status:** Approved · **Target version:** 0.3.0

## Goal

Generated projects currently hardcode `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/<slug>` — placeholder credentials that never match a real database, so a fresh project crashes on first boot. This design makes DB configuration dynamic (wizard prompts + flags), generates a matching `docker-compose.yml`, and fixes six bugs confirmed in the 2026-07-14 end-to-end review.

## Non-goals

- No live DB connection test during scaffolding (backendctl stays dependency-light).
- No Mongo-backed auth. Auth/users remain SQL-backed in all configurations.
- No Mongo authentication (root user/password) in generated compose or URIs — local dev Mongo runs unauthenticated; the db name is configurable.

## 1. Config model (`core/config.py`)

New dataclass, attached to `ProjectConfig` as `db_credentials`:

```python
@dataclass
class DatabaseCredentials:
    db_name: str = ""      # resolves to slug
    db_user: str = ""      # resolves to slug (postgres only)
    db_password: str = ""  # resolves to secrets.token_urlsafe(16) (postgres only)
    host: str = "localhost"
    port: int = 5432
```

Empty fields are resolved once, at generation time, by a `resolve_credentials(config)` step (or equivalent property logic) so templates always see final values. Mongo uses the same `db_name` and its own fixed defaults (`localhost:27017`).

Validation: `db_name` and `db_user` must match `^[a-zA-Z_][a-zA-Z0-9_]*$` (safe for `POSTGRES_DB`/`POSTGRES_USER` and URL without quoting). Password is generated with `token_urlsafe`, which is URL-safe; user-supplied passwords containing characters that require URL-encoding are percent-encoded via `urllib.parse.quote` when building `DATABASE_URL`.

## 2. Wizard + flags (`cli/new.py`)

After the database selection step, when the choice includes PostgreSQL:

1. `Database name:` (default: slug)
2. `Database user:` (default: slug)
3. `Database password:` — masked input (`questionary.password`); empty answer means "auto-generate".

When the choice includes MongoDB: `MongoDB database name:` (default: slug).

New flags, all usable with `--yes`:

| Flag | Meaning |
|------|---------|
| `--db-name` | Database name (both engines) |
| `--db-user` | PostgreSQL user |
| `--db-password` | PostgreSQL password |

Flags mark the field as provided → never re-asked. `--yes` without flags → defaults (slug/slug/random). Invalid `--db-name`/`--db-user` → exit 1 with the validation message.

## 3. Rendered outputs

- **`.env`** — real `DATABASE_URL` (and `MONGODB_URL`/`MONGODB_DB_NAME` or `MONGO_URI`) built from resolved credentials, plus existing generated secrets.
- **`.env.example`** — identical URL shape but password is the literal `change-me-db-password`. The real password never appears in a committed file.
- **`docker-compose.yml`** (new, `templates/common.py`, written whenever the project uses postgres or mongo):
  - postgres: `postgres:16-alpine`, `POSTGRES_DB/USER/PASSWORD` from credentials, `5432:5432`, named volume, `pg_isready` healthcheck.
  - mongo: `mongo:7`, `27017:27017`, named volume.
- **Generated README** — quickstart gains `docker compose up -d` before the migrations step.

Implementation note: `.env` is currently produced by string-replacing placeholders in `env_example(c)`. Template functions gain an explicit `db_password` parameter (defaulting to the placeholder) instead; generators call once for `.env.example` and once with the real password for `.env`. `_write_if_absent` semantics for `.env` are unchanged.

## 4. Bug fixes (from the 2026-07-14 review)

| # | Bug | Fix |
|---|-----|-----|
| 1 | FastAPI mongo-only crashes (`No module named 'psycopg'`) | When `uses_sql` is false, `.env`/`.env.example` set `DATABASE_URL=sqlite:///./app.db`; no psycopg dep (unchanged); compose has only the mongo service. Generated README notes auth/users are stored in SQLite while Mongo serves app data via `get_mongo_db()`. |
| 2 | Django bare `makemigrations` detects nothing | Generator writes empty `apps/users/migrations/__init__.py` and `apps/authentication/migrations/__init__.py`. |
| 3 | Django `pytest` requires running Postgres | New `config/settings/test.py`: `DATABASES` from `TEST_DATABASE_URL` (default `sqlite:///test.db`); `pyproject.toml` sets `DJANGO_SETTINGS_MODULE = "config.settings.test"`. |
| 4 | `alembic revision --autogenerate` crashes with `--auth none` | The `from <slug>.modules.auth.models import User` line in `alembic/env.py` is emitted only when auth ≠ none. |
| 5 | First-run boot crash (no local Postgres) | Solved by docker-compose + README step (section 3). |
| 6 | Success box: always `cp .env.example .env` + `uv run fastapi dev` | `print_done` takes the config: framework-correct run command (fastapi dev / flask run / manage.py runserver, pip variants without `uv run`), and the `.env` line becomes "review .env — secrets were generated for you". Also: Flask `TestConfig` gets 64-char static test secrets (silences `InsecureKeyLengthWarning`). |

## 5. Testing

Extend the repo suite (`tests/`):

- Compose file exists iff a DB is used; contains the right services and credentials per DB choice.
- `.env` contains resolved credentials; `.env.example` never contains the real password.
- Mongo-only FastAPI: pyproject has no psycopg, `.env` uses sqlite URL.
- Django: both `migrations/__init__.py` files exist; pyproject points pytest at `config.settings.test`.
- FastAPI `--auth none`: `alembic/env.py` has no auth import.
- CLI: `--db-name/--db-user/--db-password` seed config; invalid names rejected.
- Existing "every generated .py compiles" test keeps covering new/changed templates.

Final verification: regenerate the e2e matrix (fastapi/flask/django × postgres, fastapi×mongo-only, fastapi×auth-none) in the scratchpad; run each generated test suite; boot FastAPI against `docker compose up -d db` if Docker is available, otherwise verify compose config statically (`docker compose config`).
