"""Django REST Framework project templates."""

from __future__ import annotations

from backendctl.core.config import ProjectConfig


def pyproject_toml(c: ProjectConfig) -> str:
    pg_dep = '    "psycopg[binary]>=3.1.0",\n' if c.uses_sql else ""
    mongo_dep = '    "pymongo>=4.8.0",\n    "djongo>=1.3.6",\n' if c.uses_mongo else ""
    ai_dep = _ai_dep(c)

    return f"""\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{c.name}"
version = "0.1.0"
description = ""
requires-python = ">=3.11"

dependencies = [
    "django>=5.0.0",
    "djangorestframework>=3.15.0",
    "djangorestframework-simplejwt>=5.3.0",
    "django-cors-headers>=4.3.0",
    "django-environ>=0.11.0",
    "django-filter>=24.0",
{pg_dep}{mongo_dep}{ai_dep}]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-django>=4.8.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "factory-boy>=3.3.0",
]

[tool.hatch.build.targets.wheel]
packages = ["config", "apps", "core"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.development"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
"""


def _ai_dep(c: ProjectConfig) -> str:
    if not c.ai.install_sdk:
        return ""
    return {
        "claude": '    "anthropic>=0.34.0",\n',
        "openai": '    "openai>=1.45.0",\n',
    }.get(c.ai.provider.value, "")


def env_example(c: ProjectConfig) -> str:
    pg = f"postgres://user:password@localhost:5432/{c.slug}" if c.uses_sql else ""
    return f"""\
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL={pg}
TEST_DATABASE_URL=sqlite:///test.db

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=30
REFRESH_TOKEN_LIFETIME_DAYS=7
"""


def manage_py(c: ProjectConfig) -> str:
    return f"""\
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
"""


def settings_base(c: ProjectConfig) -> str:
    return f"""\
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "apps.users",
    "apps.authentication",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {{
    "default": env.db("DATABASE_URL"),
}}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {{
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {{
        "anon": "100/day",
        "user": "1000/day",
    }},
}}

from datetime import timedelta

SIMPLE_JWT = {{
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
"""


def settings_development() -> str:
    return """\
from config.settings.base import *  # noqa: F401, F403

DEBUG = True
"""


def settings_production() -> str:
    return """\
from config.settings.base import *  # noqa: F401, F403

DEBUG = False

# Add security headers, HTTPS redirects, etc. for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
"""


def config_urls(c: ProjectConfig) -> str:
    return f"""\
from django.urls import include, path

urlpatterns = [
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/users/", include("apps.users.urls")),
]
"""


def config_wsgi(c: ProjectConfig) -> str:
    return f"""\
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()
"""


def config_asgi(c: ProjectConfig) -> str:
    return f"""\
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_asgi_application()
"""


def users_model(c: ProjectConfig) -> str:
    name_field = (
        '    name = models.CharField(max_length=255, blank=True, default="")\n'
        if c.user_model.has_name
        else ""
    )
    return f"""\
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
{name_field}    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email
"""


def users_serializers(c: ProjectConfig) -> str:
    name_field = (
        '        fields = ["id", "email", "name", "is_active", "date_joined"]\n'
        if c.user_model.has_name
        else '        fields = ["id", "email", "is_active", "date_joined"]\n'
    )
    return f"""\
from rest_framework import serializers
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
{name_field}        read_only_fields = ["id", "date_joined"]
"""


def users_views() -> str:
    return """\
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.users.serializers import UserSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user
"""


def users_urls() -> str:
    return """\
from django.urls import path
from apps.users.views import MeView

urlpatterns = [
    path("me/", MeView.as_view(), name="users-me"),
]
"""


def users_apps(c: ProjectConfig) -> str:
    return f"""\
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
"""


def auth_serializers(c: ProjectConfig) -> str:
    name_field = (
        "    name = serializers.CharField(required=False, allow_blank=True)\n"
        if c.user_model.has_name
        else ""
    )
    return f"""\
from rest_framework import serializers
from apps.users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
{name_field}
    class Meta:
        model = User
        fields = ["email", "password"{', "name"' if c.user_model.has_name else ""}]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
"""


def auth_views(c: ProjectConfig) -> str:
    return f"""\
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "anon"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {{"id": str(user.id), "email": user.email}},
            status=status.HTTP_201_CREATED,
        )
"""


def auth_urls() -> str:
    return """\
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.authentication.views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
]
"""


def auth_apps() -> str:
    return """\
from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
"""


def core_pagination() -> str:
    return """\
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
"""


def core_exceptions() -> str:
    return """\
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": response.data,
            "status_code": response.status_code,
        }
    return response
"""


def tests_conftest(c: ProjectConfig) -> str:
    return f"""\
import pytest
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="test@example.com", password="secret123")


@pytest.fixture
def auth_client(api_client, user):
    r = api_client.post("/api/v1/auth/login/", {{"email": user.email, "password": "secret123"}})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {{r.data['access']}}")
    return api_client
"""


def tests_auth() -> str:
    return """\
import pytest


@pytest.mark.django_db
def test_register(api_client):
    r = api_client.post("/api/v1/auth/register/", {"email": "a@b.com", "password": "pass1234"})
    assert r.status_code == 201


@pytest.mark.django_db
def test_login(api_client, user):
    r = api_client.post("/api/v1/auth/login/", {"email": user.email, "password": "secret123"})
    assert r.status_code == 200
    assert "access" in r.data


@pytest.mark.django_db
def test_get_me(auth_client):
    r = auth_client.get("/api/v1/users/me/")
    assert r.status_code == 200
    assert r.data["email"] == "test@example.com"
"""
