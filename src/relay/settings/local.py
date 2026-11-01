"""Local-only settings with optional dotenv defaults below process values."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required for local development.")

_debug = os.environ.get("DJANGO_DEBUG", "false")
if _debug not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be true or false.")
DEBUG = _debug == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
]
if set(ALLOWED_HOSTS) - {"localhost", "127.0.0.1", "[::1]"}:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain loopback hosts only.")

_database_host = os.environ.get("POSTGRES_HOST", "localhost")
if _database_host not in {"localhost", "127.0.0.1", "::1"}:
    raise ImproperlyConfigured("POSTGRES_HOST must be a loopback host.")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "relay"),
        "USER": os.environ.get("POSTGRES_USER", "relay"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "relay"),
        "HOST": _database_host,
        "OPTIONS": {"hostaddr": "::1" if _database_host == "::1" else "127.0.0.1"},
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Local development is served over plain HTTP.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
