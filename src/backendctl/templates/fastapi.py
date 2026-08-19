"""FastAPI project templates."""

from __future__ import annotations

from backendctl.core.config import ProjectConfig

# ─── pyproject.toml ──────────────────────────────────────────────────────────

_DEV_DEPS = """\
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
"""


def pyproject_toml(c: ProjectConfig) -> str:
    mongo_dep = '    "motor>=3.4.0",\n' if c.uses_mongo else ""
    pg_dep = '    "psycopg[binary]>=3.1.0",\n' if c.uses_sql else ""
    ai_dep = _ai_dep(c)
    mongo_dev = '    "mongomock-motor>=0.3.0",\n' if c.uses_mongo else ""

    return f"""\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{c.name}"
version = "0.1.0"
description = ""
requires-python = ">=3.11"

dependencies = [
    "fastapi[standard]>=0.115.0",
    "sqlmodel>=0.0.22",
    "alembic>=1.14.0",
    "pydantic-settings>=2.5.0",
    "pyjwt[crypto]>=2.9.0",
    "pwdlib[argon2]>=0.2.1",
    "slowapi>=0.1.9",
    "python-multipart>=0.0.9",
    {pg_dep}{mongo_dep}{ai_dep}]

# Dev deps are declared twice on purpose: [dependency-groups] for uv,
# [project.optional-dependencies] so `pip install -e .[dev]` also works.
[dependency-groups]
dev = [
{mongo_dev}{_DEV_DEPS}]

[project.optional-dependencies]
dev = [
{mongo_dev}{_DEV_DEPS}]

[tool.hatch.build.targets.wheel]
packages = ["src/{c.slug}"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.mypy]
python_version = "3.11"
strict = false
"""


def _ai_dep(c: ProjectConfig) -> str:
    if not c.ai.install_sdk:
        return ""
    sdk_map = {
        "claude": '    "anthropic>=0.34.0",\n',
        "openai": '    "openai>=1.45.0",\n',
    }
    return sdk_map.get(c.ai.provider.value, "")


def _health_db(c: ProjectConfig) -> str:
    if not c.uses_mongo:
        return ""
    return f"""\
    from {c.slug}.core.mongo import get_mongo_db

    @app.get("/health/db", tags=["health"])
    async def health_db():
        db = get_mongo_db()
        await db.command("ping")
        return {{"mongodb": "ok"}}

"""


# ─── .env.example ────────────────────────────────────────────────────────────


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

    return f"""\
# ── Security ──────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-me-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Database ──────────────────────────────────────────────
# Production (PostgreSQL)
DATABASE_URL={db_url}

# Test (SQLite — used automatically in tests)
TEST_DATABASE_URL=sqlite:///./test.db
{mongo_line}
# ── App ───────────────────────────────────────────────────
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# ── Rate limiting ─────────────────────────────────────────
RATE_LIMIT_DEFAULT=100/minute
# In-memory storage is per-process; use Redis when running multiple workers,
# e.g. RATE_LIMIT_STORAGE_URI=redis://localhost:6379
RATE_LIMIT_STORAGE_URI=memory://
"""


# ─── app/main.py ─────────────────────────────────────────────────────────────


def app_main(c: ProjectConfig) -> str:
    mongo_import = (
        f"from {c.slug}.core.mongo import close_mongo, init_mongo\n" if c.uses_mongo else ""
    )
    mongo_startup = "    init_mongo()\n" if c.uses_mongo else ""
    mongo_shutdown = "\n    close_mongo()" if c.uses_mongo else ""

    return f"""\
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from {c.slug}.api.v1.router import api_router
from {c.slug}.core.config import settings
from {c.slug}.core.database import create_db_and_tables
{mongo_import}from {c.slug}.middleware.rate_limit import limiter


if settings.DEBUG:
    logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by Alembic in production (run `alembic upgrade head`).
    # create_all() is a convenience for local development and tests only.
    if settings.APP_ENV != "production":
        create_db_and_tables()
{mongo_startup}    yield{mongo_shutdown}


def create_app() -> FastAPI:
    app = FastAPI(
        title="{c.name}",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        return JSONResponse(status_code=500, content={{"detail": "Internal server error"}})

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {{"status": "ok"}}

{_health_db(c)}    return app


app = create_app()
"""


# ─── core/config.py ──────────────────────────────────────────────────────────


def core_config(c: ProjectConfig) -> str:
    mongo_fields = (
        '\n    MONGODB_URL: str = "mongodb://localhost:27017"\n    MONGODB_DB_NAME: str = "mydb"\n'
        if c.uses_mongo
        else ""
    )

    return f"""\
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str = "sqlite:///./test.db"
{mongo_fields}
    # Rate limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


settings = Settings()
"""


# ─── core/mongo.py ───────────────────────────────────────────────────────────


def core_mongo(c: ProjectConfig) -> str:
    return f"""\
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from {c.slug}.core.config import settings

_client: AsyncIOMotorClient | None = None


def init_mongo() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)


def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Mongo client not initialised — is the app running?")
    return _client[settings.MONGODB_DB_NAME]
"""


# ─── core/database.py ────────────────────────────────────────────────────────


def core_database(c: ProjectConfig) -> str:
    return f"""\
from sqlmodel import SQLModel, create_engine, Session
from {c.slug}.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
"""


# ─── core/security.py ────────────────────────────────────────────────────────


def core_security(c: ProjectConfig) -> str:
    return f"""\
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from {c.slug}.core.config import settings

pwd_context = PasswordHash((Argon2Hasher(),))


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {{"sub": str(subject), "exp": expire, "type": "access"}}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {{"sub": str(subject), "exp": expire, "type": "refresh"}}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
"""


# ─── middleware/rate_limit.py ─────────────────────────────────────────────────


def middleware_rate_limit(c: ProjectConfig) -> str:
    return f"""\
from slowapi import Limiter
from slowapi.util import get_remote_address

from {c.slug}.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
)
"""


# ─── api/v1/router.py ────────────────────────────────────────────────────────


def api_v1_router(c: ProjectConfig) -> str:
    auth_import = (
        f"from {c.slug}.modules.auth.router import router as auth_router\n"
        f"from {c.slug}.modules.users.router import router as users_router\n"
        if c.auth.value != "none"
        else ""
    )
    auth_include = (
        'api_router.include_router(auth_router, prefix="/auth", tags=["auth"])\n'
        'api_router.include_router(users_router, prefix="/users", tags=["users"])\n'
        if c.auth.value != "none"
        else ""
    )
    mongo_import = (
        f"from {c.slug}.modules.items.router import router as items_router\n"
        if c.uses_mongo
        else ""
    )
    mongo_include = (
        'api_router.include_router(items_router, prefix="/items", tags=["items"])\n'
        if c.uses_mongo
        else ""
    )

    return f"""\
from fastapi import APIRouter

{auth_import}{mongo_import}api_router = APIRouter()

{auth_include}{mongo_include}"""


# ─── modules/auth/models.py ──────────────────────────────────────────────────


def auth_models(c: ProjectConfig) -> str:
    name_field = "    name: str | None = None\n" if c.user_model.has_name else ""
    extra_fields = "".join(f"    {f}: str | None = None\n" for f in c.user_model.extra_fields)

    return f"""\
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
{name_field}{extra_fields}

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
"""


# ─── modules/auth/schemas.py ─────────────────────────────────────────────────


def auth_schemas(c: ProjectConfig) -> str:
    name_field = "    name: str | None = None\n" if c.user_model.has_name else ""

    return f"""\
import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
{name_field}    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
{name_field}    is_active: bool

    model_config = {{"from_attributes": True}}
"""


# ─── modules/auth/service.py ─────────────────────────────────────────────────


def auth_service(c: ProjectConfig) -> str:
    return f"""\
import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from {c.slug}.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from {c.slug}.modules.auth.models import User
from {c.slug}.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse


def register_user(data: RegisterRequest, session: Session) -> User:
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        **({{"name": data.name}} if hasattr(data, "name") and data.name else {{}}),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login_user(data: LoginRequest, session: Session) -> TokenResponse:
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


def refresh_tokens(refresh_token: str, session: Session) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type.")
    user = session.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
"""


# ─── modules/auth/deps.py ────────────────────────────────────────────────────


def auth_deps(c: ProjectConfig) -> str:
    return f"""\
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from {c.slug}.core.database import get_session
from {c.slug}.core.security import decode_token
from {c.slug}.modules.auth.models import User

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type.")
    user = session.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions.")
    return current_user
"""


# ─── modules/auth/router.py ──────────────────────────────────────────────────


def auth_router(c: ProjectConfig) -> str:
    return f"""\
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from {c.slug}.core.database import get_session
from {c.slug}.middleware.rate_limit import limiter
from {c.slug}.modules.auth import service
from {c.slug}.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    session: Session = Depends(get_session),
):
    user = service.register_user(data, session)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    session: Session = Depends(get_session),
):
    return service.login_user(data, session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    session: Session = Depends(get_session),
):
    return service.refresh_tokens(data.refresh_token, session)
"""


# ─── modules/users/router.py ─────────────────────────────────────────────────


def users_router(c: ProjectConfig) -> str:
    return f"""\
from fastapi import APIRouter, Depends

from {c.slug}.modules.auth.deps import get_current_user
from {c.slug}.modules.auth.models import User
from {c.slug}.modules.auth.schemas import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
"""


# ─── alembic/env.py ──────────────────────────────────────────────────────────


def alembic_env(c: ProjectConfig) -> str:
    models_import = (
        f"\n# Import all models so Alembic can detect them\n"
        f"from {c.slug}.modules.auth.models import User  # noqa: F401\n"
        if c.auth.value != "none"
        else ""
    )
    return f"""\
import os
from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel
{models_import}
config = context.config
fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./app.db")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connectable = create_engine(get_url())
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""


def alembic_ini(c: ProjectConfig) -> str:
    return f"""\
[alembic]
script_location = alembic
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %%H:%%M:%%S
"""


def alembic_script_mako() -> str:
    # This is a Mako template — ${} is Mako syntax, not Python
    lines = [
        '"""${message}',
        "",
        "Revision ID: ${up_revision}",
        "Revises: ${down_revision | comma,n}",
        "Create Date: ${create_date}",
        "",
        '"""',
        "from typing import Sequence, Union",
        "",
        "from alembic import op",
        "import sqlalchemy as sa",
        "import sqlmodel",
        "${imports if imports else ''}",
        "",
        "revision: str = ${repr(up_revision)}",
        "down_revision: Union[str, None] = ${repr(down_revision)}",
        "branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}",
        "depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}",
        "",
        "",
        "def upgrade() -> None:",
        "    ${upgrades if upgrades else 'pass'}",
        "",
        "",
        "def downgrade() -> None:",
        "    ${downgrades if downgrades else 'pass'}",
    ]
    return "\n".join(lines) + "\n"


# ─── tests/conftest.py ───────────────────────────────────────────────────────


def tests_conftest(c: ProjectConfig) -> str:
    mongo_patch = (
        "\n\n@pytest.fixture(autouse=True)\ndef mock_mongo(monkeypatch):\n"
        "    import mongomock_motor\n"
        "    monkeypatch.setattr(\n"
        f'        "{c.slug}.core.mongo._client",\n'
        "        mongomock_motor.AsyncMongoMockClient(),\n"
        "    )\n"
        if c.uses_mongo
        else ""
    )
    return f"""\
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from {c.slug}.core.database import get_session
from {c.slug}.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={{"check_same_thread": False}},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
{mongo_patch}"""


def tests_auth(c: ProjectConfig) -> str:
    return f"""\
def test_register(client):
    response = client.post(
        "/api/v1/auth/register",
        json={{"email": "test@example.com", "password": "secret123"}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


def test_register_duplicate(client):
    payload = {{"email": "dup@example.com", "password": "secret123"}}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_register_short_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={{"email": "weak@example.com", "password": "short"}},
    )
    assert response.status_code == 422


def test_login(client):
    client.post(
        "/api/v1/auth/register",
        json={{"email": "login@example.com", "password": "secret123"}},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={{"email": "login@example.com", "password": "secret123"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid(client):
    response = client.post(
        "/api/v1/auth/login",
        json={{"email": "nobody@example.com", "password": "wrong"}},
    )
    assert response.status_code == 401


def test_get_me(client):
    client.post(
        "/api/v1/auth/register",
        json={{"email": "me@example.com", "password": "secret123"}},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={{"email": "me@example.com", "password": "secret123"}},
    )
    token = login.json()["access_token"]
    response = client.get("/api/v1/users/me", headers={{"Authorization": f"Bearer {{token}}"}})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
"""


def tests_health(c: ProjectConfig) -> str:
    db_test = (
        "\n\n"
        "def test_health_db(client):\n"
        '    r = client.get("/health/db")\n'
        "    assert r.status_code == 200\n"
        '    assert r.json() == {"mongodb": "ok"}\n'
        if c.uses_mongo
        else ""
    )
    return f"""\
from fastapi.testclient import TestClient

from {c.slug}.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {{"status": "ok"}}
{db_test}"""


def tests_items(c: ProjectConfig) -> str:
    return f"""\
def test_create_and_list_item(client):
    r = client.post("/api/v1/items", json={{"name": "Widget"}})
    assert r.status_code == 201
    r = client.get("/api/v1/items")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
"""


def items_router(c: ProjectConfig) -> str:
    return f"""\
from fastapi import APIRouter

from {c.slug}.core.mongo import get_mongo_db

router = APIRouter()


@router.get("/items")
async def list_items():
    items = []
    async for doc in get_mongo_db().items.find():
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items


@router.post("/items")
async def create_item():
    data = {{}}
    get_mongo_db().items.insert_one(data)
    return data, 201
"""
