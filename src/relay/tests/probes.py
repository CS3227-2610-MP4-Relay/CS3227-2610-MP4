"""Run settings_probe.py in a clean process, for tests of settings modules."""

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
PROBE = SRC / "relay" / "tests" / "settings_probe.py"


def probe(module, dotenv=None, **values):
    """Inspect settings without inheriting any runtime configuration."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "POSTGRES_", "SOC_LLM_", "DATABASE_URL"))
    }
    environment.update(PYTHONPATH=str(SRC), **values)
    return subprocess.run(
        [sys.executable, str(PROBE), module, *([str(dotenv)] if dotenv else [])],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
