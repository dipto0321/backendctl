"""backendctl new — interactive wizard + flags for project creation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import questionary
import typer

from backendctl.core.checks import run_preflight
from backendctl.core.config import (
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


# ─── wizard ──────────────────────────────────────────────────────────────────


def _run_wizard(config: ProjectConfig) -> None:
    """Fill in config interactively for any field not already set via flags."""

    # 1. Project name
    if not config.name:
        config.name = _ask(
            questionary.text,
            message="Project name:",
            validate=_validate_project_name,
        ).strip()

    # 2. Target directory check
    target = Path.cwd() / config.name
    if target.exists():
        overwrite = _ask(
            questionary.confirm,
            message=f"Directory '{config.name}' already exists. Continue anyway?",
            default=False,
        )
        if not overwrite:
            raise typer.Exit(0)

    # 3. Package manager
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

    # 5. Database
    config.database = Database(
        _ask(
            questionary.select,
            message="Database:",
            choices=[
                questionary.Choice(
                    "PostgreSQL  (prod) + SQLite  (tests)  [SQL]",
                    value="postgres",
                ),
                questionary.Choice("MongoDB  [NoSQL]", value="mongodb"),
                questionary.Choice(
                    "PostgreSQL + MongoDB  [SQL + NoSQL]",
                    value="both",
                ),
            ],
        )
    )

    # 6. Auth
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
    if config.auth != AuthType.NONE:
        name_field = _ask(
            questionary.confirm,
            message="Include a 'name' field on the User model?",
            default=False,
        )
        config.user_model = UserModelConfig(has_name=name_field)

    # 8. AI setup
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
    config.init_git = _ask(
        questionary.confirm,
        message="Initialise a git repository?",
        default=True,
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

    # Seed config from flags (wizard fills the rest)
    config = ProjectConfig()

    if project_name:
        config.name = project_name
    if framework:
        try:
            config.framework = Framework(framework.lower())
        except ValueError:
            print_error(f"Unknown framework '{framework}'. Choose: fastapi, flask, django.")
            raise typer.Exit(1)
    if db:
        try:
            config.database = Database(db.lower())
        except ValueError:
            print_error(f"Unknown db '{db}'. Choose: postgres, mongodb, both.")
            raise typer.Exit(1)
    if package_manager:
        try:
            config.package_manager = PackageManager(package_manager.lower())
        except ValueError:
            print_error(f"Unknown package manager '{package_manager}'. Choose: uv, pip.")
            raise typer.Exit(1)
    if no_git:
        config.init_git = False
    if no_ai:
        config.ai = AIConfig(provider=AIProvider.NONE)

    # Interactive wizard for anything not already set
    _run_wizard(config)

    # Pre-flight checks
    if not run_preflight(config.package_manager.value, config.init_git):
        raise typer.Exit(1)

    # Generate
    print_step("Generating project…")
    generator = get_generator(config)
    try:
        project_path = generator.generate()
    except Exception as exc:  # noqa: BLE001
        print_error(f"Generation failed: {exc}")
        raise typer.Exit(1)

    framework_label = {
        Framework.FASTAPI: "FastAPI",
        Framework.FLASK: "Flask",
        Framework.DJANGO: "Django REST Framework",
    }[config.framework]

    print_done(config.name, framework_label, str(project_path))
