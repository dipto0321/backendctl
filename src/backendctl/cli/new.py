"""backendctl new — interactive wizard + flags for project creation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import questionary
import typer

from backendctl.core.checks import run_preflight
from backendctl.core.config import (
    DB_IDENT_RE,
    AIConfig,
    AIProvider,
    AuthType,
    Database,
    Framework,
    PackageManager,
    ProjectConfig,
    UserModelConfig,
)
from backendctl.core.console import (
    console,
    print_banner,
    print_done,
    print_error,
    print_step,
)
from backendctl.generators import get_generator
from backendctl.generators.base import ScaffoldError

# ─── helpers ─────────────────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

_Q_STYLE = questionary.Style(
    [
        ("qmark", "fg:#00d7ff bold"),
        ("question", "bold"),
        ("answer", "fg:#00d7ff bold"),
        ("pointer", "fg:#00d7ff bold"),
        ("highlighted", "fg:#00d7ff bold"),
        ("selected", "fg:#5fd7ff"),
        ("separator", "fg:#6c6c6c"),
        ("instruction", "fg:#858585"),
    ]
)


def _ask(prompt_fn, **kwargs):
    """Wrap questionary calls; exit cleanly on Ctrl-C / EOF."""
    try:
        result = prompt_fn(**kwargs, style=_Q_STYLE).ask()
        if result is None:
            raise typer.Exit(0)
        return result
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled.[/dim]")
        raise typer.Exit(0)


def _validate_project_name(value: str) -> bool | str:
    if not value.strip():
        return "Project name cannot be empty."
    if not _SLUG_RE.match(value.strip()):
        return "Use only letters, digits, hyphens, and underscores; must start with a letter."
    return True


def _validate_db_identifier(value: str) -> bool | str:
    if not value.strip():
        return "Value cannot be empty."
    if not DB_IDENT_RE.match(value.strip()):
        return "Use only letters, digits, and underscores; must not start with a digit."
    return True


def _parse_enum(enum_cls, raw: str, flag: str, allowed: str):
    try:
        return enum_cls(raw.lower())
    except ValueError:
        print_error(f"Unknown {flag} '{raw}'. Choose: {allowed}.")
        raise typer.Exit(1)


# ─── wizard ──────────────────────────────────────────────────────────────────


def _run_wizard(config: ProjectConfig, provided: set[str], assume_yes: bool) -> None:
    """Fill in config interactively.

    Fields named in ``provided`` were set via CLI flags and are never re-asked.
    With ``assume_yes`` every unset field keeps its default and no prompt is shown.
    """

    # 1. Project name
    if "name" not in provided:
        config.name = _ask(
            questionary.text,
            message="Project name:",
            validate=_validate_project_name,
        ).strip()

    # 2. Target directory check
    target = Path.cwd() / config.name
    if target.exists() and any(target.iterdir()) and not config.force:
        if assume_yes:
            print_error(f"Directory '{config.name}' is not empty. Re-run with --force to continue.")
            raise typer.Exit(1)
        overwrite = _ask(
            questionary.confirm,
            message=(
                f"Directory '{config.name}' already exists and is not empty. "
                "Existing files may be overwritten (.env is preserved). Continue?"
            ),
            default=False,
        )
        if not overwrite:
            raise typer.Exit(0)
        config.force = True

    # 3. Package manager
    if "package_manager" not in provided and not assume_yes:
        config.package_manager = PackageManager(
            _ask(
                questionary.select,
                message="Package manager:",
                choices=[
                    questionary.Choice("uv  (recommended)", value="uv"),
                    questionary.Choice("pip", value="pip"),
                ],
            )
        )

    # 4. Framework
    if "framework" not in provided and not assume_yes:
        config.framework = Framework(
            _ask(
                questionary.select,
                message="Framework:",
                choices=[
                    questionary.Choice("FastAPI", value="fastapi"),
                    questionary.Choice("Flask", value="flask"),
                    questionary.Choice("Django REST Framework (DRF)", value="django"),
                ],
            )
        )

    # 5. Database (MongoDB is not offered for Django — djongo is unmaintained)
    if "database" not in provided and not assume_yes:
        db_choices = [
            questionary.Choice(
                "PostgreSQL  (prod) + SQLite  (tests)  [SQL]",
                value="postgres",
            ),
        ]
        if config.framework != Framework.DJANGO:
            db_choices += [
                questionary.Choice("MongoDB  [NoSQL]", value="mongodb"),
                questionary.Choice(
                    "PostgreSQL + MongoDB  [SQL + NoSQL]",
                    value="both",
                ),
            ]
        config.database = Database(
            _ask(
                questionary.select,
                message="Database:",
                choices=db_choices,
            )
        )

    # 5b. Database credentials
    _ask_db_credentials(config, provided, assume_yes)

    # 6. Auth
    if "auth" not in provided and not assume_yes:
        config.auth = AuthType(
            _ask(
                questionary.select,
                message="Authentication:",
                choices=[
                    questionary.Choice("JWT (access + refresh tokens)", value="jwt"),
                    questionary.Choice("None — I'll add auth later", value="none"),
                ],
            )
        )

    # 7. User model fields
    if config.auth != AuthType.NONE and not assume_yes:
        name_field = _ask(
            questionary.confirm,
            message="Include a 'name' field on the User model?",
            default=False,
        )
        config.user_model = UserModelConfig(has_name=name_field)

    # 8. AI setup
    if "ai" not in provided and not assume_yes:
        ai_provider = _ask(
            questionary.select,
            message="AI assistant setup:",
            choices=[
                questionary.Choice("None — skip", value="none"),
                questionary.Choice("Claude (Anthropic)", value="claude"),
                questionary.Choice("OpenAI", value="openai"),
            ],
        )
        if ai_provider != "none":
            ai_files = _ask(
                questionary.checkbox,
                message="Which AI config files should be generated?",
                choices=[
                    questionary.Choice(
                        "Instructions file (CLAUDE.md / AGENTS.md)",
                        value="instructions",
                        checked=True,
                    ),
                    questionary.Choice(
                        ".cursorrules  (Cursor IDE)",
                        value="cursorrules",
                        checked=True,
                    ),
                    questionary.Choice(
                        "mcp.json  (MCP tool config)",
                        value="mcp",
                        checked=False,
                    ),
                    questionary.Choice(
                        "Install AI SDK as a dependency",
                        value="sdk",
                        checked=False,
                    ),
                ],
            )
            config.ai = AIConfig(
                provider=AIProvider(ai_provider),
                create_instructions_file="instructions" in ai_files,
                create_cursorrules="cursorrules" in ai_files,
                create_mcp_config="mcp" in ai_files,
                install_sdk="sdk" in ai_files,
            )

    # 9. Git init
    if "init_git" not in provided and not assume_yes:
        config.init_git = _ask(
            questionary.confirm,
            message="Initialise a git repository?",
            default=True,
        )


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


# ─── command ─────────────────────────────────────────────────────────────────


def new_command(
    project_name: Optional[str] = typer.Argument(None, help="Name of the new project."),
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        "-f",
        help="Framework: fastapi | flask | django",
    ),
    db: Optional[str] = typer.Option(
        None,
        "--db",
        help="Database: postgres | mongodb | both",
    ),
    package_manager: Optional[str] = typer.Option(
        None,
        "--pm",
        help="Package manager: uv | pip",
    ),
    auth: Optional[str] = typer.Option(
        None,
        "--auth",
        help="Authentication: jwt | none",
    ),
    ai: Optional[str] = typer.Option(
        None,
        "--ai",
        help="AI assistant setup: none | claude | openai",
    ),
    db_name: Optional[str] = typer.Option(
        None, "--db-name", help="Database name (default: project slug)."
    ),
    db_user: Optional[str] = typer.Option(
        None, "--db-user", help="PostgreSQL user (default: project slug)."
    ),
    db_password: Optional[str] = typer.Option(
        None, "--db-password", help="PostgreSQL password (default: auto-generated)."
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Non-interactive: accept defaults for every option not set via flags.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow scaffolding into an existing non-empty directory.",
    ),
    no_git: bool = typer.Option(
        False,
        "--no-git",
        help="Skip git initialisation.",
    ),
    no_ai: bool = typer.Option(
        False,
        "--no-ai",
        help="Skip AI assistant setup.",
    ),
) -> None:
    print_banner()

    # Seed config from flags; remember which fields were explicitly provided
    # so the wizard never re-asks (and never overwrites) them.
    config = ProjectConfig()
    provided: set[str] = set()

    if project_name:
        result = _validate_project_name(project_name)
        if result is not True:
            print_error(f"Invalid project name '{project_name}': {result}")
            raise typer.Exit(1)
        config.name = project_name.strip()
        provided.add("name")
    elif yes:
        print_error("A project name is required with --yes (non-interactive mode).")
        raise typer.Exit(1)

    if framework:
        config.framework = _parse_enum(Framework, framework, "framework", "fastapi, flask, django")
        provided.add("framework")
    if db:
        config.database = _parse_enum(Database, db, "db", "postgres, mongodb, both")
        provided.add("database")
    if package_manager:
        config.package_manager = _parse_enum(
            PackageManager, package_manager, "package manager", "uv, pip"
        )
        provided.add("package_manager")
    if auth:
        config.auth = _parse_enum(AuthType, auth, "auth", "jwt, none")
        provided.add("auth")
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
    if no_ai:
        config.ai = AIConfig(provider=AIProvider.NONE)
        provided.add("ai")
    elif ai:
        provider = _parse_enum(AIProvider, ai, "ai", "none, claude, openai")
        config.ai = (
            AIConfig(provider=AIProvider.NONE)
            if provider == AIProvider.NONE
            else AIConfig(
                provider=provider,
                create_instructions_file=True,
                create_cursorrules=True,
            )
        )
        provided.add("ai")
    if no_git:
        config.init_git = False
        provided.add("init_git")
    if force:
        config.force = True

    # Interactive wizard for anything not already set
    _run_wizard(config, provided, assume_yes=yes)

    # MongoDB with Django is not supported (djongo is unmaintained and
    # incompatible with Django 5).
    if config.framework == Framework.DJANGO and config.uses_mongo:
        print_error(
            "MongoDB is not supported with Django (djongo is unmaintained). "
            "Use --db postgres, or choose FastAPI/Flask for MongoDB."
        )
        raise typer.Exit(1)

    # Pre-flight checks
    if not run_preflight(config.package_manager.value, config.init_git):
        raise typer.Exit(1)

    # Generate
    print_step("Generating project…")
    try:
        generator = get_generator(config)
        project_path = generator.generate()
    except ScaffoldError as exc:
        print_error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:  # noqa: BLE001
        print_error(f"Generation failed: {exc}")
        raise typer.Exit(1)

    framework_label = {
        Framework.FASTAPI: "FastAPI",
        Framework.FLASK: "Flask",
        Framework.DJANGO: "Django REST Framework",
    }[config.framework]

    print_done(config.name, framework_label, str(project_path))
