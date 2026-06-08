"""Entry point for the backendctl CLI."""

import typer

from backendctl import __version__
from backendctl.cli.new import new_command

app = typer.Typer(
    name="backendctl",
    help="Scaffold production-ready Python backend projects.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

app.command("new", help="Create a new backend project.")(new_command)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"backendctl v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


if __name__ == "__main__":
    app()
