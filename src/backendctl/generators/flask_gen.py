"""Flask project generator."""

from __future__ import annotations

import secrets

from backendctl.generators.base import BaseGenerator
from backendctl.templates import flask as t


class FlaskGenerator(BaseGenerator):
    def _scaffold(self) -> None:
        c = self.config
        s = c.slug

        self._write("pyproject.toml", t.pyproject_toml(c))
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c, db_password=c.db_credentials.db_password)
            .replace("change-me-to-a-long-random-string", secrets.token_hex(32))
            .replace("another-long-random-secret", secrets.token_hex(32)),
        )

        # Package root
        self._write(f"src/{s}/__init__.py", t.app_init(c))
        self._write(f"src/{s}/extensions.py", t.extensions(c))
        self._write(f"src/{s}/config.py", t.config_py(c))

        # Models
        self._write(f"src/{s}/models/__init__.py", "")
        self._write(f"src/{s}/models/user.py", t.user_model(c))

        # Blueprints
        self._write(f"src/{s}/blueprints/__init__.py", "")
        self._write(f"src/{s}/blueprints/auth/__init__.py", "")
        self._write(f"src/{s}/blueprints/auth/schemas.py", t.auth_schemas(c))
        self._write(f"src/{s}/blueprints/auth/routes.py", t.auth_routes(c))
        self._write(f"src/{s}/blueprints/auth/service.py", t.auth_service(c))
        self._write(f"src/{s}/blueprints/users/__init__.py", "")
        self._write(f"src/{s}/blueprints/users/routes.py", t.users_routes(c))

        # Tests
        self._write("tests/__init__.py", "")
        self._write("tests/conftest.py", t.tests_conftest(c))
        self._write("tests/test_auth.py", t.tests_auth(c))

        # Migrations placeholder (Flask-Migrate creates this on first run)
        self._touch("migrations/.gitkeep")

        from backendctl.core.console import print_info

        print_info("Flask project structure written.")
