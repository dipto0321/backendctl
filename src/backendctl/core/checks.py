"""Pre-flight checks — verify required tools are available."""

from __future__ import annotations

import shutil
import subprocess
import sys

from backendctl.core.console import console, print_error, print_success, print_warning


def _cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _python_version() -> tuple[int, int]:
    return sys.version_info.major, sys.version_info.minor


def check_python() -> bool:
    major, minor = _python_version()
    if major < 3 or (major == 3 and minor < 11):
        print_error(f"Python 3.11+ required (found {major}.{minor}).")
        console.print(
            "  Install it from [link=https://python.org]python.org[/link] "
            "or via [cyan]pyenv[/cyan]."
        )
        return False
    print_success(f"Python {major}.{minor} detected.")
    return True


def check_uv() -> bool:
    if not _cmd_exists("uv"):
        print_error("`uv` not found.")
        console.print(
            "  Install it with:  [cyan]curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]\n"
            "  Docs: [link=https://docs.astral.sh/uv]https://docs.astral.sh/uv[/link]"
        )
        return False
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        print_success(f"uv {result.stdout.strip()} detected.")
    except Exception:
        print_warning("Found `uv` but could not determine version.")
    return True


def check_pip() -> bool:
    if not _cmd_exists("pip") and not _cmd_exists("pip3"):
        print_error("`pip` not found — it should ship with Python.")
        return False
    print_success("pip detected.")
    return True


def check_git() -> bool:
    if not _cmd_exists("git"):
        print_warning("`git` not found — git init will be skipped.")
        return False
    print_success("git detected.")
    return True


def run_preflight(package_manager: str, need_git: bool) -> bool:
    """Run all required checks. Returns True only if everything passes."""
    console.print("\n[bold]Checking required tools…[/bold]")

    ok = check_python()

    if package_manager == "uv":
        ok = check_uv() and ok
    else:
        ok = check_pip() and ok

    if need_git:
        check_git()  # non-fatal — just warns

    return ok
