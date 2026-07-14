"""Rich console helpers for consistent CLI output."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from backendctl.core.config import FRAMEWORK_LABELS, Framework, PackageManager, ProjectConfig

console = Console()


def print_banner() -> None:
    text = Text()
    text.append("backendctl", style="bold cyan")
    text.append("  —  scaffold Python backends in seconds", style="dim")
    console.print(Panel(text, border_style="cyan", padding=(0, 2)))


def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green]  {message}")


def print_info(message: str) -> None:
    console.print(f"[bold blue]→[/bold blue]  {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]![/bold yellow]  {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]✗[/bold red]  {message}")


def print_step(step: str) -> None:
    console.print(f"\n[bold cyan]  {step}[/bold cyan]")


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
