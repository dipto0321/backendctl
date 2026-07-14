"""Shared templates: .gitignore, .editorconfig, pre-commit, README, Dockerfile."""

from __future__ import annotations

import json

from backendctl.core.config import FRAMEWORK_LABELS, Framework, ProjectConfig

DB_PASSWORD_PLACEHOLDER = "change-me-db-password"


def gitignore() -> str:
    return """\
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/
*.whl

# Virtual environments
.venv/
venv/
env/
ENV/

# uv (uv.lock is committed on purpose — applications need reproducible installs)
.uv/

# Environment variables
.env
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
coverage.xml
htmlcov/
.tox/

# Mypy
.mypy_cache/
.dmypy.json

# Ruff / linting
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*.iml

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Logs
*.log
logs/

# Database
*.sqlite3
*.db

# Alembic (keep versions, ignore generated)
# alembic/versions/*.py  <- keep these tracked

# Distribution / packaging
*.tar.gz
*.zip
"""


def editorconfig() -> str:
    return """\
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true

[*.{json,yaml,yml,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab
"""


def pre_commit_config() -> str:
    return """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
"""


def readme(c: ProjectConfig) -> str:
    label = FRAMEWORK_LABELS[c.framework]

    run_dev = {
        Framework.FASTAPI: f"uv run fastapi dev src/{c.slug}/main.py",
        Framework.FLASK: f'uv run flask --app "{c.slug}:create_app()" run --debug',
        Framework.DJANGO: "uv run python manage.py runserver",
    }[c.framework]

    migrate = {
        Framework.FASTAPI: (
            "uv run alembic revision --autogenerate -m 'init'\nuv run alembic upgrade head"
        ),
        Framework.FLASK: "uv run flask db init && uv run flask db migrate && uv run flask db upgrade",
        Framework.DJANGO: "uv run python manage.py makemigrations && uv run python manage.py migrate",
    }[c.framework]

    pip_alt = (
        ""
        if c.package_manager.value == "uv"
        else """\

> Using pip? A virtualenv was created at `.venv` during scaffolding:
> `source .venv/bin/activate && pip install -e ".[dev]"`
"""
    )

    mongo_note = (
        "\n> **Note:** auth/user data is stored in SQLite (`app.db`); MongoDB is wired "
        "for application data.\n"
        if c.uses_mongo and not c.uses_sql
        else ""
    )

    return f"""\
# {c.name}

A {label} backend scaffolded with [backendctl](https://github.com/dipto0321/backendctl).

## Quickstart

```bash
# 1. Install dependencies
uv sync
{pip_alt}
# 2. Configure environment
#    A .env with freshly generated secrets was created for you.
#    Review it and point DATABASE_URL at your database.

# 3. Start the database (Docker)
docker compose up -d

# 4. Apply database migrations
{migrate}

# 5. Run the dev server
{run_dev}
```
{mongo_note}
## Testing

```bash
uv run pytest
```

## Production notes

- Set `APP_ENV=production` / `DEBUG=false` and use real secrets (never the scaffolded `.env` from another machine).
- Schema changes go through migrations — don't rely on auto table creation.
- The default rate-limit storage is in-process memory; point it at Redis when running multiple workers.
- Refresh tokens are stateless JWTs{" (Django: rotated tokens are blacklisted via the token_blacklist app)" if c.framework == Framework.DJANGO else " — a stolen refresh token stays valid until it expires; add server-side revocation (e.g. a jti denylist) if you need instant logout"}.
- A `Dockerfile` is included: `docker build -t {c.slug} . && docker run -p 8000:8000 --env-file .env {c.slug}`
"""


def dockerfile(c: ProjectConfig) -> str:
    if c.framework == Framework.DJANGO:
        copy_lines = "COPY manage.py ./\nCOPY config ./config\nCOPY apps ./apps\nCOPY core ./core"
        cmd = 'CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]'
    elif c.framework == Framework.FLASK:
        copy_lines = "COPY src ./src"
        cmd = f'CMD ["gunicorn", "--bind", "0.0.0.0:8000", "{c.slug}:create_app()"]'
    else:
        copy_lines = "COPY src ./src\nCOPY alembic ./alembic\nCOPY alembic.ini ./"
        cmd = f'CMD ["uvicorn", "{c.slug}.main:app", "--host", "0.0.0.0", "--port", "8000"]'

    return f"""\
FROM python:3.12-slim

# Don't run as root
RUN useradd --create-home appuser
WORKDIR /app

COPY pyproject.toml ./
{copy_lines}

RUN pip install --no-cache-dir .

USER appuser
EXPOSE 8000

{cmd}
"""


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
