"""Inspect settings in a clean process using synthetic environment values only."""

import importlib
import json
import logging
import os
import sys
from pathlib import Path
from runpy import run_path

import django
from django.conf import global_settings
from django.conf import settings as django_settings
from django.core import checks
from django.db import connection
from django.http import HttpResponseServerError
from django.test import Client, RequestFactory
from django.utils.log import log_response
from psycopg import pq

# Created before Django configures logging, as module loggers are.
EARLY_LOGGER = logging.getLogger("relay.synthetic_early")


def emit_log_records(host):
    """Log a synthetic 500, an early-logger warning and a gateway INFO outcome."""
    request = RequestFactory().get(
        "/synthetic-failure/?query=synthetic-query", HTTP_HOST=host
    )
    try:
        raise RuntimeError("synthetic failure")
    except RuntimeError as error:
        log_response(
            "%s: %s",
            "Internal Server Error",
            request.path,
            response=HttpResponseServerError(),
            request=request,
            exception=error,
        )
    EARLY_LOGGER.warning("Synthetic early warning")
    logging.getLogger("ai.gateway").info("LLM gateway outcome: %s", "live-off")


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
    emit_log_records(django_settings.ALLOWED_HOSTS[0])
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
    run_path(str(Path(__file__).with_name("dotenv_probe.py")))["isolate_dotenv"](
        sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
    )
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
                "logging": getattr(settings, "LOGGING", None),
                "runtime": runtime,
            }
        )
    )


if __name__ == "__main__":
    main()
