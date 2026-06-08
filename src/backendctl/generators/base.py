"""BaseGenerator — shared scaffolding logic."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from backendctl.core.config import ProjectConfig
from backendctl.core.console import print_info, print_success, print_warning


class BaseGenerator(ABC):
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.root: Path = Path.cwd() / config.name

    # ─── public ───────────────────────────────────────────────────────────

    def generate(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        self._scaffold()
        self._write_common_files()
        if self.config.ai.provider.value != "none":
            self._write_ai_files()
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

    def _touch(self, rel_path: str) -> None:
        self._write(rel_path, "")

    def _write_common_files(self) -> None:
        from backendctl.templates.common import (
            editorconfig,
            gitignore,
            pre_commit_config,
        )

        self._write(".gitignore", gitignore())
        self._write(".editorconfig", editorconfig())
        self._write(".pre-commit-config.yaml", pre_commit_config())
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
                subprocess.run(
                    ["pip", "install", "-e", ".[dev]"],
                    cwd=self.root,
                    check=True,
                )
            print_success("Dependencies installed.")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print_warning(f"Dependency install failed ({exc}). Run it manually after setup.")
