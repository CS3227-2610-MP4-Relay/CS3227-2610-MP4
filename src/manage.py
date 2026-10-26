"""Run Django management commands with local settings by default."""

import os
import sys

from django.core.management import execute_from_command_line


def main():
    """Select local settings unless the operator explicitly selects another module."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relay.settings.local")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
