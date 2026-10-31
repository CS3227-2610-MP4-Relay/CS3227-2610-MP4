"""Redirect configuration probes before local settings can read a real dotenv."""

import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def isolate_dotenv(module_name, path=None):
    """Preload only the loader, preserving WSGI's isolated project-path test."""
    source = Path(__file__).parents[1] / "settings" / "dotenv.py"
    spec = importlib.util.spec_from_file_location("relay.settings.dotenv", source)
    loader = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loader
    spec.loader.exec_module(loader)
    loader._probe_directory = TemporaryDirectory()
    loader.DOTENV_PATH = (
        Path(path) if path else Path(loader._probe_directory.name) / "missing.env"
    )
    if module_name != "relay.settings.local":
        loader.load_dotenv = forbidden


def forbidden():
    """Make test/production settings fail if they try to invoke the loader."""
    raise AssertionError("Nonlocal settings invoked the dotenv loader.")
