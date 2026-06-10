"""FastAPI project generator."""

from __future__ import annotations

from backendctl.generators.base import BaseGenerator
from backendctl.templates import fastapi as t


class FastAPIGenerator(BaseGenerator):
    def _scaffold(self) -> None:
        c = self.config
        s = c.slug

        # Root files
        self._write("pyproject.toml", t.pyproject_toml(c))
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c).replace("change-me-to-a-long-random-string", _random_key()),
        )

        # Package __init__
        self._write(f"src/{s}/__init__.py", "")

        # main.py
        self._write(f"src/{s}/main.py", t.app_main(c))

        # core/
        self._write(f"src/{s}/core/__init__.py", "")
        self._write(f"src/{s}/core/config.py", t.core_config(c))
        self._write(f"src/{s}/core/database.py", t.core_database(c))
        self._write(f"src/{s}/core/security.py", t.core_security(c))
        if c.uses_mongo:
            self._write(f"src/{s}/core/mongo.py", t.core_mongo(c))

        # middleware/
        self._write(f"src/{s}/middleware/__init__.py", "")
        self._write(f"src/{s}/middleware/rate_limit.py", t.middleware_rate_limit(c))

        # api/v1/
        self._write(f"src/{s}/api/__init__.py", "")
        self._write(f"src/{s}/api/v1/__init__.py", "")
        self._write(f"src/{s}/api/v1/router.py", t.api_v1_router(c))

        # modules/
        self._write(f"src/{s}/modules/__init__.py", "")

        if c.auth.value != "none":
            # auth module
            self._write(f"src/{s}/modules/auth/__init__.py", "")
            self._write(f"src/{s}/modules/auth/models.py", t.auth_models(c))
            self._write(f"src/{s}/modules/auth/schemas.py", t.auth_schemas(c))
            self._write(f"src/{s}/modules/auth/service.py", t.auth_service(c))
            self._write(f"src/{s}/modules/auth/deps.py", t.auth_deps(c))
            self._write(f"src/{s}/modules/auth/router.py", t.auth_router(c))

            # users module
            self._write(f"src/{s}/modules/users/__init__.py", "")
            self._write(f"src/{s}/modules/users/router.py", t.users_router(c))

        # Alembic
        self._write("alembic.ini", t.alembic_ini(c))
        self._write("alembic/env.py", t.alembic_env(c))
        self._write("alembic/script.py.mako", t.alembic_script_mako())
        self._touch("alembic/versions/.gitkeep")

        # Tests
        self._write("tests/__init__.py", "")
        self._write("tests/conftest.py", t.tests_conftest(c))
        if c.auth.value != "none":
            self._write("tests/test_auth.py", t.tests_auth(c))

        from backendctl.core.console import print_info

        print_info("FastAPI project structure written.")


def _random_key() -> str:
    import secrets

    return secrets.token_hex(32)
