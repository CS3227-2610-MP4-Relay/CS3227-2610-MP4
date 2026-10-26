"""Inspect settings in a clean process using synthetic environment values only."""

import importlib
import json
import sys


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
            }
        )
    )


if __name__ == "__main__":
    main()
