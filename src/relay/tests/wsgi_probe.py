"""Exercise direct-file WSGI startup without project import paths or database IO."""

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from runpy import run_path
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper


def main():
    """Load the hosted entrypoint and request its anonymous start page."""
    run_path(str(Path(__file__).with_name("dotenv_probe.py")))["isolate_dotenv"](
        os.environ.get("DJANGO_SETTINGS_MODULE", "relay.settings.local")
    )
    spec = importlib.util.spec_from_file_location("hosted_wsgi", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with patch.object(
        BaseDatabaseWrapper,
        "ensure_connection",
        side_effect=AssertionError("Database IO"),
    ) as connect:
        spec.loader.exec_module(module)
        environ = {}
        setup_testing_defaults(environ)
        environ.update(
            HTTP_HOST=settings.ALLOWED_HOSTS[0],
            **{"wsgi.url_scheme": "https", "wsgi.input": io.BytesIO()},
        )
        statuses = []
        response = module.application(
            environ, lambda status, headers: statuses.append(status)
        )
        try:
            body = b"".join(response).decode()
        finally:
            response.close()
        assert connect.call_count == 0
    print(
        json.dumps(
            {"status": statuses, "body": body, "settings": settings.SETTINGS_MODULE}
        )
    )


if __name__ == "__main__":
    main()
