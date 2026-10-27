"""Inspect settings in a clean process using synthetic environment values only."""

import importlib
import json
import sys

from django.conf import global_settings


def main():
    """Print the selected settings for configuration assertions."""
    settings = importlib.import_module(sys.argv[1])
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
            }
        )
    )


if __name__ == "__main__":
    main()
