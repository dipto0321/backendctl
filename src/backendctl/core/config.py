"""ProjectConfig — single source of truth for what the user chose in the wizard."""

import re
import secrets
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import quote


class Framework(str, Enum):
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"


FRAMEWORK_LABELS = {
    Framework.FASTAPI: "FastAPI",
    Framework.FLASK: "Flask",
    Framework.DJANGO: "Django REST Framework",
}


class PackageManager(str, Enum):
    UV = "uv"
    PIP = "pip"


class Database(str, Enum):
    POSTGRES = "postgres"  # PostgreSQL (prod) + SQLite (test)
    MONGODB = "mongodb"
    BOTH = "both"  # PostgreSQL + MongoDB


class AuthType(str, Enum):
    JWT = "jwt"
    NONE = "none"


class AIProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    NONE = "none"


@dataclass
class UserModelConfig:
    has_name: bool = False
    extra_fields: list[str] = field(default_factory=list)


@dataclass
class AIConfig:
    provider: AIProvider = AIProvider.NONE
    create_instructions_file: bool = False  # CLAUDE.md / AGENTS.md
    create_cursorrules: bool = False  # .cursorrules / .windsurfrules
    create_mcp_config: bool = False  # .claude/mcp.json
    install_sdk: bool = False  # add SDK to dependencies


# Safe for POSTGRES_DB/POSTGRES_USER and for URLs without quoting.
DB_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\Z")


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


@dataclass
class ProjectConfig:
    name: str = ""
    package_manager: PackageManager = PackageManager.UV
    framework: Framework = Framework.FASTAPI
    database: Database = Database.POSTGRES
    auth: AuthType = AuthType.JWT
    user_model: UserModelConfig = field(default_factory=UserModelConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    db_credentials: DatabaseCredentials = field(default_factory=DatabaseCredentials)
    init_git: bool = True
    force: bool = False  # allow scaffolding into a non-empty directory

    @property
    def slug(self) -> str:
        """Filesystem-safe project name (snake_case)."""
        return self.name.lower().replace("-", "_").replace(" ", "_")

    @property
    def uses_sql(self) -> bool:
        return self.database in (Database.POSTGRES, Database.BOTH)

    @property
    def uses_mongo(self) -> bool:
        return self.database in (Database.MONGODB, Database.BOTH)
