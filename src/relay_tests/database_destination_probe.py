"""Probe the actual database destination using synthetic, isolated test values."""

import os
import sys

from django.db import connections


def main():
    """Connect with Django's driver parameters and report the resolved address."""
    os.environ["DJANGO_SETTINGS_MODULE"] = sys.argv[1]
    wrapper = connections["default"]
    parameters = wrapper.get_connection_params()
    parameters["connect_timeout"] = 1
    for key in list(os.environ):
        if key.startswith("PG"):
            del os.environ[key]
    os.environ["PGHOSTADDR"] = "192.0.2.1"
    with wrapper.Database.connect(**parameters) as connection:
        print(connection.info.hostaddr)


if __name__ == "__main__":
    main()
