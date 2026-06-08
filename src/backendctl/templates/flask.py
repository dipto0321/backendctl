"""Flask project templates."""

from __future__ import annotations

from backendctl.core.config import ProjectConfig


def pyproject_toml(c: ProjectConfig) -> str:
    pg_dep = '    "psycopg[binary]>=3.1.0",\n' if c.uses_sql else ""
    mongo_dep = '    "pymongo>=4.8.0",\n    "flask-pymongo>=2.3.0",\n' if c.uses_mongo else ""
    ai_dep = _ai_dep(c)

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
    "flask>=3.0.0",
    "flask-sqlalchemy>=3.1.0",
    "flask-migrate>=4.0.0",
    "flask-jwt-extended>=4.6.0",
    "flask-limiter>=3.7.0",
    "pydantic[email]>=2.7.0",
    "pydantic-settings>=2.5.0",
    "pwdlib[argon2]>=0.2.1",
    "python-dotenv>=1.0.0",
{pg_dep}{mongo_dep}{ai_dep}]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{c.slug}"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
"""


def _ai_dep(c: ProjectConfig) -> str:
    if not c.ai.install_sdk:
        return ""
    return {
        "claude": '    "anthropic>=0.34.0",\n',
        "openai": '    "openai>=1.45.0",\n',
    }.get(c.ai.provider.value, "")


def env_example(c: ProjectConfig) -> str:
    mongo_block = (
        "\n# MongoDB\nMONGODB_URI=mongodb://localhost:27017/mydb\n" if c.uses_mongo else ""
    )
    return f"""\
FLASK_ENV=development
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=true

# Database (PostgreSQL)
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/{c.slug}
TEST_DATABASE_URL=sqlite:///test.db
{mongo_block}
# JWT
JWT_SECRET_KEY=another-long-random-secret
JWT_ACCESS_TOKEN_EXPIRES=1800
JWT_REFRESH_TOKEN_EXPIRES=604800

# Rate limiting (uses in-memory storage by default)
RATELIMIT_DEFAULT=100 per minute
"""


def app_init(c: ProjectConfig) -> str:
    return f"""\
from flask import Flask

from {c.slug}.config import Config
from {c.slug}.extensions import db, jwt, limiter, migrate


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # Blueprints
    from {c.slug}.blueprints.auth.routes import auth_bp
    from {c.slug}.blueprints.users.routes import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")

    @app.get("/health")
    def health():
        return {{"status": "ok"}}

    return app
"""


def extensions(c: ProjectConfig) -> str:
    return f"""\
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
"""


def config_py(c: ProjectConfig) -> str:
    return f"""\
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    SQLALCHEMY_DATABASE_URI: str = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    JWT_SECRET_KEY: str = os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "1800"))
    )
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800"))
    )

    RATELIMIT_DEFAULT: str = os.getenv("RATELIMIT_DEFAULT", "100 per minute")
    RATELIMIT_STORAGE_URI: str = "memory://"


class TestConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv("TEST_DATABASE_URL", "sqlite:///test.db")
    JWT_SECRET_KEY: str = "test-secret"
    SECRET_KEY: str = "test-secret"
    RATELIMIT_ENABLED: bool = False
"""


def user_model(c: ProjectConfig) -> str:
    name_col = (
        "    name = db.Column(db.String(255), nullable=True)\n" if c.user_model.has_name else ""
    )
    return f"""\
import uuid
from datetime import datetime, timezone

from {c.slug}.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
{name_col}    hashed_password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User {{self.email}}>"
"""


def auth_routes(c: ProjectConfig) -> str:
    return f"""\
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity

from {c.slug}.blueprints.auth.service import login_user, register_user
from {c.slug}.extensions import limiter

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    user = register_user(data)
    return jsonify({{"id": user.id, "email": user.email}}), 201


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    user = login_user(data)
    return jsonify({{
        "access_token": create_access_token(identity=user.id),
        "refresh_token": create_refresh_token(identity=user.id),
        "token_type": "bearer",
    }})


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({{"access_token": create_access_token(identity=identity)}})
"""


def auth_service(c: ProjectConfig) -> str:
    return f"""\
from flask import abort

from {c.slug}.extensions import db
from {c.slug}.models.user import User
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

pwd = PasswordHash((Argon2Hasher(),))


def register_user(data: dict) -> User:
    if User.query.filter_by(email=data["email"]).first():
        abort(409, description="Email already registered.")
    user = User(
        email=data["email"],
        hashed_password=pwd.hash(data["password"]),
        **({{"name": data["name"]}} if "name" in data else {{}}),
    )
    db.session.add(user)
    db.session.commit()
    return user


def login_user(data: dict) -> User:
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not pwd.verify(data.get("password", ""), user.hashed_password):
        abort(401, description="Invalid credentials.")
    if not user.is_active:
        abort(403, description="Account is inactive.")
    return user
"""


def users_routes(c: ProjectConfig) -> str:
    return f"""\
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from {c.slug}.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    return jsonify({{"id": user.id, "email": user.email, "is_active": user.is_active}})
"""


def tests_conftest(c: ProjectConfig) -> str:
    return f"""\
import pytest
from {c.slug} import create_app
from {c.slug}.config import TestConfig
from {c.slug}.extensions import db as _db


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
"""


def tests_auth(c: ProjectConfig) -> str:
    return """\
def test_register(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "pw"})
    assert r.status_code == 201

def test_register_duplicate(client):
    payload = {"email": "d@b.com", "password": "pw"}
    client.post("/api/v1/auth/register", json=payload)
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409

def test_login(client):
    client.post("/api/v1/auth/register", json={"email": "l@b.com", "password": "pw"})
    r = client.post("/api/v1/auth/login", json={"email": "l@b.com", "password": "pw"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()

def test_login_invalid(client):
    r = client.post("/api/v1/auth/login", json={"email": "x@b.com", "password": "wrong"})
    assert r.status_code == 401
"""
