"""Explicit hosted configuration; no dotenv loading or local fallbacks."""

import os
import re
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *


def _required(name):
    value = os.environ.get(name, "")
    if not value.strip():
        raise ImproperlyConfigured(f"{name} is invalid or missing.")
    return value


def _hostname(value):
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    return (
        len(value) <= 253
        and re.fullmatch(rf"(?:{label}\.)+[a-z]{{2,63}}", value) is not None
        and not value.endswith(".localhost")
    )


SECRET_KEY = _required("DJANGO_SECRET_KEY")
DEBUG = False
_host = _required("DJANGO_PRODUCTION_HOST")
if not _hostname(_host):
    raise ImproperlyConfigured("DJANGO_PRODUCTION_HOST is invalid or missing.")
ALLOWED_HOSTS = [_host]
CSRF_TRUSTED_ORIGINS = [f"https://{_host}"]

_proxy = os.environ.get("DJANGO_TRUST_PROXY_SSL_HEADER", "false")
if _proxy not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_TRUST_PROXY_SSL_HEADER is invalid or missing.")
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if _proxy == "true" else None
)
SECURE_SSL_REDIRECT = _proxy == "true"
SECURE_HSTS_SECONDS = 31536000
# The configured host does not authorize HSTS for sibling/subdomains or preload.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

_url = _required("DATABASE_URL")
try:
    _database = urlsplit(_url)
    _port = 5432 if _database.port is None else _database.port
    _valid = (
        _database.scheme in {"postgres", "postgresql"}
        and 1 <= _port <= 65535
        and _database.hostname is not None
        and _hostname(_database.hostname)
        and bool(_database.username and _database.password)
        and _database.path.startswith("/")
        and len(_database.path) > 1
        and "/" not in unquote(_database.path[1:])
        and _database.query in {"", "sslmode=verify-full"}
        and not _database.fragment
        and not any(character.isspace() for character in _url)
    )
except ValueError:
    _valid = False
if not _valid:
    raise ImproperlyConfigured("DATABASE_URL is invalid or missing.") from None
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(_database.path[1:]),
        "USER": unquote(_database.username),
        "PASSWORD": unquote(_database.password),
        "HOST": _database.hostname,
        "PORT": _port,
        "CONN_MAX_AGE": 0,
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "OPTIONS": {
            "sslmode": "verify-full",
            "sslrootcert": "system",
            "connect_timeout": 10,
        },
    }
}
