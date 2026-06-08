"""Shared templates: .gitignore, .editorconfig, pre-commit."""


def gitignore() -> str:
    return """\
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/
*.whl

# Virtual environments
.venv/
venv/
env/
ENV/

# uv
.uv/
uv.lock

# Environment variables
.env
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
coverage.xml
htmlcov/
.tox/

# Mypy
.mypy_cache/
.dmypy.json

# Ruff / linting
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*.iml

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Logs
*.log
logs/

# Database
*.sqlite3
*.db

# Alembic (keep versions, ignore generated)
# alembic/versions/*.py  <- keep these tracked

# Docker
.dockerignore

# Distribution / packaging
*.tar.gz
*.zip
"""


def editorconfig() -> str:
    return """\
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true

[*.{json,yaml,yml,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab
"""


def pre_commit_config() -> str:
    return """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
"""
