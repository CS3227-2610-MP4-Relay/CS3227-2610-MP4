"""WSGI entry point; hosted operators explicitly select production settings."""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relay.settings.local")
application = get_wsgi_application()
