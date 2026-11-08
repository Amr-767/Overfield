"""Shared Django settings for AgroSpace Quest."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

# backend/ → repository root (where Phase 1A `.env` lives)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

_ENV_FILE = REPO_ROOT / ".env"
if _ENV_FILE.exists():
    # Prefer UTF-8; fall back for older Windows-created .env files.
    try:
        load_dotenv(_ENV_FILE, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(_ENV_FILE, encoding="cp1252")


def env(key: str, default: str | None = None) -> str | None:
    """Read an environment variable with an optional default."""
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value


def env_bool(key: str, default: bool = False) -> bool:
    raw = env(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: list[str] | None = None) -> list[str]:
    raw = env(key)
    if raw is None or raw.strip() == "":
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set. Copy .env.example to .env and set a unique local value."
    )

DEBUG = env_bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # GeoDjango (Phase 2 Step 0) — PostGIS backend + spatial fields.
    "django.contrib.gis",
    # Third-party
    "corsheaders",
    "rest_framework",
    # Local
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.farms.apps.FarmsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL/PostGIS via Phase 1A Docker Compose.
# The Django container sets POSTGRES_HOST=postgres and POSTGRES_PORT=5432
# (Compose network). A host-local Django would use 127.0.0.1 + 55432 instead.
DATABASES = {
    "default": {
        # GeoDjango backend — enables spatial fields, GiST indexes and PostGIS
        # functions (ST_Area/ST_Intersects/geography casts).
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("POSTGRES_DB", "agrospace"),
        "USER": env("POSTGRES_USER", "agrospace"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "55432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# GeoDjango native library discovery (optional overrides).
# In the Phase 2 Docker image GEOS/GDAL/PROJ are installed system-wide, so the
# defaults resolve automatically; set these only for non-standard installs.
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH")
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS / CSRF — React Vite defaults (Phase 1C will consume these).
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)

REST_FRAMEWORK = {
    # Phase 2: JWT is the only authentication mechanism and everything is
    # private by default. Public endpoints (health, registration, token
    # obtain/refresh) opt out explicitly on the view.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# JWT lifetimes (ADR-009). Tokens are short-lived; the SPA keeps the access
# token in memory and refreshes it through /api/v1/auth/token/refresh/.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Celery (Phase 1D) — reuses the Phase 1A Redis service as broker + result store.
# Connection parameters come from the environment. Never log REDIS_PASSWORD.
# ---------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST", "127.0.0.1")
REDIS_PORT = env("REDIS_PORT", "6379")
REDIS_PASSWORD = env("REDIS_PASSWORD", "") or ""
CELERY_BROKER_DB = env("CELERY_BROKER_DB", "0")
CELERY_RESULT_DB = env("CELERY_RESULT_DB", "1")


def _redis_url(db: str) -> str:
    auth = f":{quote(REDIS_PASSWORD, safe='')}@" if REDIS_PASSWORD else ""
    return f"redis://{auth}{REDIS_HOST}:{REDIS_PORT}/{db}"


# Explicit CELERY_BROKER_URL / CELERY_RESULT_BACKEND env vars override the
# derived defaults (useful for a future in-Compose worker using host `redis`).
CELERY_BROKER_URL = env("CELERY_BROKER_URL") or _redis_url(CELERY_BROKER_DB)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND") or _redis_url(CELERY_RESULT_DB)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
