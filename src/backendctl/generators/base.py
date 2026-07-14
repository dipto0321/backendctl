"""BaseGenerator — shared scaffolding logic."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from backendctl.core.config import ProjectConfig
from backendctl.core.console import print_info, print_success, print_warning

# Mirrors the wizard's validation; enforced here as defense in depth so a
# generator can never be constructed with a name that escapes the cwd.
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


class ScaffoldError(RuntimeError):
    """Raised when generation cannot proceed safely."""


class BaseGenerator(ABC):
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config

        if not _SAFE_NAME_RE.match(config.name):
            raise ScaffoldError(
                f"Unsafe project name {config.name!r}: use only letters, digits, "
                "hyphens, and underscores; must start with a letter."
            )

        self.root: Path = Path.cwd() / config.name

        # Defense in depth: the target must be a direct child of the cwd.
        if self.root.resolve().parent != Path.cwd().resolve():
            raise ScaffoldError(f"Refusing to scaffold outside the current directory: {self.root}")

        try:
            config.db_credentials.resolve(config.slug)
        except ValueError as exc:
            raise ScaffoldError(str(exc)) from exc

    # ─── public ───────────────────────────────────────────────────────────

    def generate(self) -> Path:
        pre_existing = self.root.exists()

        if pre_existing and any(self.root.iterdir()) and not self.config.force:
            raise ScaffoldError(
                f"Directory '{self.config.name}' is not empty. "
                "Re-run with --force to scaffold into it anyway."
            )

        self.root.mkdir(parents=True, exist_ok=True)

        try:
            self._scaffold()
            self._write_common_files()
            if self.config.ai.provider.value != "none":
                self._write_ai_files()
        except Exception:
            # Don't leave a half-written project behind — but only remove
            # directories this run created.
            if not pre_existing:
                shutil.rmtree(self.root, ignore_errors=True)
            raise

        if self.config.init_git:
            self._git_init()
        self._install_deps()
        print_success(f"Project ready at {self.root}")
        return self.root

    # ─── abstract ─────────────────────────────────────────────────────────

    @abstractmethod
    def _scaffold(self) -> None:
        """Write all framework-specific files."""

    # ─── shared helpers ───────────────────────────────────────────────────

    def _write(self, rel_path: str, content: str) -> None:
        target = self.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def _write_if_absent(self, rel_path: str, content: str) -> None:
        """Write a file only if it doesn't exist (used for secrets like .env)."""
        target = self.root / rel_path
        if target.exists():
            print_warning(f"{rel_path} already exists — left untouched.")
            return
        self._write(rel_path, content)

    def _touch(self, rel_path: str) -> None:
        self._write(rel_path, "")

    def _write_common_files(self) -> None:
        from backendctl.templates.common import (
            docker_compose,
            dockerfile,
            editorconfig,
            gitignore,
            pre_commit_config,
            readme,
        )

        self._write(".gitignore", gitignore())
        self._write(".editorconfig", editorconfig())
        self._write(".pre-commit-config.yaml", pre_commit_config())
        self._write("README.md", readme(self.config))
        self._write("Dockerfile", dockerfile(self.config))
        self._write("docker-compose.yml", docker_compose(self.config))
        print_info("Common files written.")

    def _write_ai_files(self) -> None:
        from backendctl.templates.ai import (
            claude_md,
            cursorrules,
            mcp_json,
        )

        ai = self.config.ai
        provider = ai.provider.value

        if ai.create_instructions_file:
            filename = "CLAUDE.md" if provider == "claude" else "AGENTS.md"
            self._write(filename, claude_md(self.config))
            print_info(f"{filename} written.")

        if ai.create_cursorrules:
            self._write(".cursorrules", cursorrules(self.config))
            print_info(".cursorrules written.")

        if ai.create_mcp_config:
            self._write(".claude/mcp.json", mcp_json())
            print_info(".claude/mcp.json written.")

    def _git_init(self) -> None:
        try:
            subprocess.run(
                ["git", "init", "--initial-branch=main"],
                cwd=self.root,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=self.root,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "chore: initial project scaffold"],
                cwd=self.root,
                capture_output=True,
                check=True,
            )
            print_success("Git repository initialised (conventional-commits ready).")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_warning("Could not initialise git — skipping.")

    def _install_deps(self) -> None:
        pm = self.config.package_manager.value
        print_info(f"Installing dependencies with {pm}…")
        try:
            if pm == "uv":
                subprocess.run(
                    ["uv", "sync"],
                    cwd=self.root,
                    check=True,
                )
            else:
                self._pip_install_in_venv()
            print_success("Dependencies installed.")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print_warning(f"Dependency install failed ({exc}). Run it manually after setup.")

    def _pip_install_in_venv(self) -> None:
        """Create a project-local venv and install into it (never the global env)."""
        venv_dir = self.root / ".venv"
        if not venv_dir.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", ".venv"],
                cwd=self.root,
                check=True,
            )
        bin_dir = "Scripts" if os.name == "nt" else "bin"
        python_exe = "python.exe" if os.name == "nt" else "python"
        venv_python = venv_dir / bin_dir / python_exe
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", ".[dev]"],
            cwd=self.root,
            check=True,
        )
