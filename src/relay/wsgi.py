"""WSGI entry point for local development; no hosted settings are supplied."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relay.settings.local")
application = get_wsgi_application()
