"""Django REST Framework project generator."""

from __future__ import annotations

import secrets

from backendctl.generators.base import BaseGenerator
from backendctl.templates import django as t


class DjangoGenerator(BaseGenerator):
    def _scaffold(self) -> None:
        c = self.config

        self._write("pyproject.toml", t.pyproject_toml(c))
        self._write(".env.example", t.env_example(c))
        self._write_if_absent(
            ".env",
            t.env_example(c, db_password=c.db_credentials.db_password).replace(
                "change-me-to-a-long-random-string", secrets.token_hex(32)
            ),
        )

        # manage.py
        self._write("manage.py", t.manage_py(c))

        # config/
        self._write("config/__init__.py", "")
        self._write("config/settings/__init__.py", "")
        self._write("config/settings/base.py", t.settings_base(c))
        self._write("config/settings/development.py", t.settings_development())
        self._write("config/settings/production.py", t.settings_production())
        self._write("config/settings/test.py", t.settings_test())
        self._write("config/urls.py", t.config_urls(c))
        self._write("config/wsgi.py", t.config_wsgi(c))
        self._write("config/asgi.py", t.config_asgi(c))

        # apps/__init__.py
        self._write("apps/__init__.py", "")

        # apps/users/
        self._write("apps/users/__init__.py", "")
        self._write("apps/users/apps.py", t.users_apps(c))
        self._write("apps/users/models.py", t.users_model(c))
        if c.auth.value != "none":
            self._write("apps/users/serializers.py", t.users_serializers(c))
            self._write("apps/users/views.py", t.users_views())
            self._write("apps/users/urls.py", t.users_urls())
        self._write("apps/users/migrations/__init__.py", "")

        # apps/authentication/
        if c.auth.value != "none":
            self._write("apps/authentication/__init__.py", "")
            self._write("apps/authentication/apps.py", t.auth_apps())
            self._write("apps/authentication/serializers.py", t.auth_serializers(c))
            self._write("apps/authentication/views.py", t.auth_views(c))
            self._write("apps/authentication/urls.py", t.auth_urls())
            self._write("apps/authentication/migrations/__init__.py", "")

        # core/
        self._write("core/__init__.py", "")
        self._write("core/pagination.py", t.core_pagination())
        self._write("core/exceptions.py", t.core_exceptions())

        # Tests
        self._write("tests/__init__.py", "")
        self._write("tests/conftest.py", t.tests_conftest(c))
        self._write("tests/test_health.py", t.tests_health(c))
        if c.auth.value != "none":
            self._write("tests/test_auth.py", t.tests_auth())

        from backendctl.core.console import print_info

        print_info("DRF project structure written.")
