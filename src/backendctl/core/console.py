"""Rich console helpers for consistent CLI output."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

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


def print_done(project_name: str, framework: str, path: str) -> None:
    lines = [
        f"[bold green]Project [cyan]{project_name}[/cyan] created![/bold green]",
        "",
        f"  [dim]Framework :[/dim]  {framework}",
        f"  [dim]Location  :[/dim]  {path}",
        "",
        "  [bold]Next steps:[/bold]",
        f"    [cyan]cd {project_name}[/cyan]",
        "    [cyan]cp .env.example .env[/cyan]  [dim]# fill in your secrets[/dim]",
        "    [cyan]uv run fastapi dev[/cyan]     "
        "[dim]# or flask run / python manage.py runserver[/dim]",
    ]
    console.print(Panel("\n".join(lines), border_style="green", padding=(0, 2)))
