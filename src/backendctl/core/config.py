"""ProjectConfig — single source of truth for what the user chose in the wizard."""

from dataclasses import dataclass, field
from enum import Enum


class Framework(str, Enum):
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"


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


@dataclass
class ProjectConfig:
    name: str = ""
    package_manager: PackageManager = PackageManager.UV
    framework: Framework = Framework.FASTAPI
    database: Database = Database.POSTGRES
    auth: AuthType = AuthType.JWT
    user_model: UserModelConfig = field(default_factory=UserModelConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    init_git: bool = True

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
