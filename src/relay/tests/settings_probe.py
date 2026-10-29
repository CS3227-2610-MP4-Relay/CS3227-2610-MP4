"""Inspect settings in a clean process using synthetic environment values only."""

import importlib
import json
import os
import sys

import django
from django.conf import global_settings
from django.conf import settings as django_settings
from django.core import checks
from django.db import connection
from django.test import Client
from psycopg import pq


def production_checks(module):
    """Exercise synthetic hosted settings without opening a database connection."""
    os.environ["DJANGO_SETTINGS_MODULE"] = module
    django.setup()
    client = Client(
        enforce_csrf_checks=True, HTTP_HOST=django_settings.ALLOWED_HOSTS[0]
    )
    responses = [
        client.get(path, secure=True) for path in ("/", "/sign-in/", "/missing/")
    ]
    proxy_response = client.get("/", HTTP_X_FORWARDED_PROTO="https")
    return {
        "headers": [dict(response.headers) for response in responses],
        "statuses": [response.status_code for response in responses],
        "csrf_secure": client.cookies["csrftoken"]["secure"],
        "csrf_origins": django_settings.CSRF_TRUSTED_ORIGINS,
        "foreign_origin": client.post(
            "/sign-in/",
            {"csrfmiddlewaretoken": client.cookies["csrftoken"].value},
            secure=True,
            HTTP_ORIGIN="https://foreign.invalid",
        ).status_code,
        "hostile_host": client.get(
            "/", secure=True, HTTP_HOST="foreign.invalid"
        ).status_code,
        "proxy_https": proxy_response.status_code,
        "proxy_hsts": proxy_response.get("Strict-Transport-Security", ""),
        "plain_http": client.get("/").status_code,
        "deployment_checks": [
            issue.id
            for issue in checks.run_checks(include_deployment_checks=True)
            if issue.id not in django_settings.SILENCED_SYSTEM_CHECKS
        ],
        "silenced_checks": django_settings.SILENCED_SYSTEM_CHECKS,
        "connection": {
            key: connection.get_connection_params()[key]
            for key in ("sslmode", "sslrootcert", "connect_timeout")
        },
        "libpq": pq.version(),
    }


def main():
    """Print the selected settings for configuration assertions."""
    settings = importlib.import_module(sys.argv[1])
    runtime = (
        production_checks(sys.argv[1]) if sys.argv[1].endswith(".production") else {}
    )
    print(
        json.dumps(
            {
                "secret": settings.SECRET_KEY,
                "debug": settings.DEBUG,
                "hosts": settings.ALLOWED_HOSTS,
                "database": settings.DATABASES["default"],
                "hashers": getattr(
                    settings, "PASSWORD_HASHERS", global_settings.PASSWORD_HASHERS
                ),
                "framing": {
                    "middleware": settings.MIDDLEWARE,
                    "x_frame_options": getattr(
                        settings, "X_FRAME_OPTIONS", global_settings.X_FRAME_OPTIONS
                    ),
                },
                "cookies": {
                    "session_secure": settings.SESSION_COOKIE_SECURE,
                    "csrf_secure": settings.CSRF_COOKIE_SECURE,
                },
                "runtime": runtime,
            }
        )
    )


if __name__ == "__main__":
    main()
