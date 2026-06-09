# backendctl

> Stop rewriting the same boilerplate. Start with a solid foundation.

`backendctl` is an interactive CLI that generates a batteries-included backend
project — auth, database, migrations, rate limiting, tests, linting, and optional
AI-assistant config — for the framework of your choice. Pick **FastAPI**,
**Flask**, or **Django REST Framework**, answer a few questions, and start coding
your actual business logic.

## Features

- **Three frameworks** — FastAPI (SQLModel), Flask (SQLAlchemy), or Django REST Framework.
- **JWT auth out of the box** — register / login / refresh, Argon2 password hashing,
  a `User` model, and a `/users/me` endpoint.
- **Database choice** — PostgreSQL (with SQLite for tests), MongoDB, or both.
- **Sane defaults** — rate limiting, CORS, env-based config, layered settings.
- **Migrations** — Alembic (FastAPI), Flask-Migrate, or Django migrations.
- **Tests included** — `pytest` suite wired up with fixtures.
- **Tooling** — `ruff`, `mypy`, `.pre-commit-config.yaml`, `.editorconfig`.
- **AI-assistant ready** — optional `CLAUDE.md`/`AGENTS.md`, `.cursorrules`,
  `mcp.json`, and SDK dependency.
- **`uv` or `pip`** — your choice of package manager.

## Installation

Requires **Python 3.11+**.

```bash
# Run without installing (recommended)
uvx backendctl new

# Or install as a tool
uv tool install backendctl

# Or with pip
pip install backendctl
```

### From source

```bash
git clone https://github.com/dipto0321/backendctl
cd backendctl
uv sync
uv run backendctl --help
```

## Usage

### Interactive wizard

```bash
backendctl new
```

You'll be guided through:

1. Project name
2. Package manager (`uv` / `pip`)
3. Framework (FastAPI / Flask / Django REST Framework)
4. Database (PostgreSQL+SQLite / MongoDB / both)
5. Authentication (JWT / none)
6. Optional `name` field on the `User` model
7. AI-assistant config (Claude / OpenAI / none)
8. Git initialization

### Non-interactive flags

Any flag you pass skips the matching wizard step:

```bash
backendctl new myapi --framework fastapi --db postgres --pm uv --no-ai
```

| Flag | Values | Description |
|------|--------|-------------|
| `project_name` | string | Name of the new project (positional). |
| `--framework`, `-f` | `fastapi` \| `flask` \| `django` | Web framework. |
| `--db` | `postgres` \| `mongodb` \| `both` | Database. |
| `--pm` | `uv` \| `pip` | Package manager. |
| `--no-git` | flag | Skip git initialization. |
| `--no-ai` | flag | Skip AI-assistant setup. |
| `--version`, `-v` | flag | Print version and exit. |

### What you get

After generation, `backendctl` runs pre-flight checks, writes the project, sets up
git (optional), and installs dependencies. Then:

```bash
cd myapi
cp .env.example .env      # fill in your secrets
uv run fastapi dev        # or: flask run / python manage.py runserver
```

## Generated project layout

<details>
<summary>FastAPI</summary>

```
myapi/
├── src/myapi/
│   ├── main.py                 # app factory + lifespan
│   ├── core/                   # config, database, security
│   ├── middleware/             # rate limiting
│   ├── api/v1/router.py        # versioned router
│   └── modules/
│       ├── auth/               # models, schemas, service, deps, router
│       └── users/              # /me endpoint
├── alembic/                    # migrations
├── tests/                      # pytest suite
├── pyproject.toml
└── .env.example
```
</details>

<details>
<summary>Flask</summary>

```
myapi/
├── src/myapi/
│   ├── __init__.py             # app factory
│   ├── config.py               # Config / TestConfig
│   ├── extensions.py           # db, jwt, limiter, migrate
│   ├── models/user.py
│   └── blueprints/
│       ├── auth/               # routes + service
│       └── users/              # /me endpoint
├── migrations/                 # Flask-Migrate
├── tests/
├── pyproject.toml
└── .env.example
```
</details>

<details>
<summary>Django REST Framework</summary>

```
myapi/
├── config/
│   ├── settings/               # base / development / production
│   ├── urls.py, wsgi.py, asgi.py
├── apps/
│   ├── users/                  # custom User model + /me
│   └── authentication/         # register + JWT token views
├── core/                       # pagination, exception handler
├── tests/
├── manage.py
├── pyproject.toml
└── .env.example
```
</details>

## Development

```bash
uv sync                 # install dev dependencies
uv run pytest           # run the test suite
uv run ruff check src   # lint
uv run ruff format src  # format
uv run mypy src         # type-check
```

The repository is laid out as:

```
src/backendctl/
├── main.py              # Typer entry point
├── cli/new.py           # `new` command + interactive wizard
├── core/                # config dataclasses, console helpers, pre-flight checks
├── generators/          # per-framework file writers (BaseGenerator + subclasses)
└── templates/           # pure functions returning file contents
```

To add or change generated output, edit the relevant function in
`templates/` and the matching `_scaffold()` in `generators/`. The test suite
compiles every generated `.py` file, so syntax regressions are caught
automatically.

## License

[MIT](LICENSE) © Dipto Karmakar
