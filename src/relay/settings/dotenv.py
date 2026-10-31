"""Literal, allowlisted dotenv loading for local settings only."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables

DOTENV_PATH = Path(__file__).resolve().parents[3] / ".env"
NAMES = frozenset(
    {
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "SOC_LLM_ENDPOINT",
        "SOC_LLM_MODEL",
        "SOC_LLM_API_KEY",
    }
)
ERROR = "Invalid local dotenv configuration."


@sensitive_variables()
def load_dotenv():
    """Fill absent allowed environment names from the fixed local dotenv path."""
    try:
        text = DOTENV_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError):
        raise ImproperlyConfigured(ERROR) from None
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("export ", "export\t")):
            line = line[6:].strip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if name not in NAMES:
            if name.split(maxsplit=1)[:1] and name.split(maxsplit=1)[0] in NAMES:
                raise ImproperlyConfigured(ERROR)
            continue
        if not separator:
            raise ImproperlyConfigured(ERROR)
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ImproperlyConfigured(ERROR)
            value = value[1:-1]
        elif value.endswith(("'", '"')):
            raise ImproperlyConfigured(ERROR)
        if "\x00" in value:
            raise ImproperlyConfigured(ERROR)
        values[name] = value
    for name, value in values.items():
        os.environ.setdefault(name, value)
