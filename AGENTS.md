# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

`backendctl` is a Typer + Rich + questionary CLI that scaffolds production-ready
Python backends (FastAPI, Flask, Django REST Framework) with JWT auth, a database
choice, migrations, rate limiting, tests, linting, and optional AI-assistant
config files.

## Commands

```bash
uv sync                              # install dependencies
uv run pytest -q                     # run the test suite
uv run ruff check src tests          # lint
uv run ruff format --check src tests # format check
uv run mypy src                      # type-check
```

## Layout

```
src/backendctl/
├── main.py              # Typer entry point
├── cli/new.py           # `new` command + interactive wizard + flag parsing
├── core/                # config dataclasses, console helpers, pre-flight checks
├── generators/          # per-framework file writers (BaseGenerator + subclasses)
└── templates/           # pure functions returning file contents
```

Generators write files to disk; templates are pure functions that return file
contents. To change generated output, edit the matching function in
`templates/` and the corresponding `_scaffold()` in `generators/`.

## Hard rules

- Never use `shell=True`; `subprocess.run` always takes a list of arguments.
- Secrets are generated with `secrets.token_hex` / `secrets.token_urlsafe` and
  written only into the gitignored `.env`. Committed files carry placeholders
  only. The real database password must never appear in `.env.example`,
  `README.md`, or any committed template output.
- Project names must match `^[a-zA-Z][a-zA-Z0-9_-]*$` and must not escape the
  current directory (path-traversal guard lives in `BaseGenerator`).
- Use conventional commits: `type(scope): summary`.

## Spec-driven development (OpenSpec)

This project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for
spec-driven development. Specs live in `openspec/specs/`; in-flight work is
proposed as changes in `openspec/changes/` and archived to
`openspec/changes/archive/` when done.

Start a change with `/opsx-propose`, implement with `/opsx-apply`, and archive
with `/opsx-archive`. Validate with `openspec validate <change> --strict`.
