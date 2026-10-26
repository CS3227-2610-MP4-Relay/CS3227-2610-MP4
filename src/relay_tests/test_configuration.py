import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1]
PROBE = SRC / "relay_tests" / "settings_probe.py"


def probe(module, **values):
    """Inspect settings without inheriting any runtime configuration."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "POSTGRES_", "SOC_LLM_"))
    }
    environment.update(PYTHONPATH=str(SRC), **values)
    return subprocess.run(
        [sys.executable, str(PROBE), module],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.ac("PLT-1.5")
def test_test_settings_ignore_runtime_environment():
    result = probe(
        "relay.settings.test",
        DJANGO_SECRET_KEY="synthetic-runtime-key",
        DJANGO_DEBUG="true",
        DJANGO_ALLOWED_HOSTS="production.invalid",
        POSTGRES_HOST="production.invalid",
        POSTGRES_PORT="1111",
        POSTGRES_DB="synthetic-production",
        POSTGRES_USER="synthetic-user",
        POSTGRES_PASSWORD="synthetic-password",
        SOC_LLM_API_KEY="synthetic-provider-key",
    )
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["secret"] == "relay-test-only-not-a-production-secret"
    assert settings["debug"] is False
    assert settings["hosts"] == ["testserver", "localhost", "127.0.0.1"]
    assert settings["database"] == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "relay_test",
        "USER": "relay_test",
        "PASSWORD": "relay_test",
        "HOST": "127.0.0.1",
        "OPTIONS": {"hostaddr": "127.0.0.1"},
        "PORT": "55432",
        "TEST": {"NAME": "test_relay_test"},
    }


@pytest.mark.ac("PLT-1.5")
def test_pytest_startup_overrides_inherited_settings_module():
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "synthetic_nonexistent_production_settings",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(SRC / "relay_tests" / "pytest_startup_probe.py"),
            "-q",
        ],
        cwd=SRC.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.ac("PLT-1.4", "PLT-1.5")
@pytest.mark.parametrize(
    "module,host",
    [
        ("relay.settings.test", "127.0.0.1"),
        ("relay.settings.local", "localhost"),
        ("relay.settings.local", "127.0.0.1"),
    ],
)
def test_driver_ignores_inherited_hostaddr(module, host):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "POSTGRES_", "SOC_LLM_", "PG"))
    }
    environment.update(
        PYTHONPATH=str(SRC),
        DJANGO_SECRET_KEY="synthetic-local-key",
        POSTGRES_HOST=host,
        POSTGRES_PORT="55432",
        POSTGRES_DB="relay_test",
        POSTGRES_USER="relay_test",
        POSTGRES_PASSWORD="relay_test",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SRC / "relay_tests/database_destination_probe.py"),
            module,
        ],
        cwd=SRC.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "127.0.0.1"


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize("debug", ["true", "false"])
def test_local_settings_accept_explicit_loopback_configuration(debug):
    result = probe(
        "relay.settings.local",
        DJANGO_SECRET_KEY="synthetic-local-key",
        DJANGO_DEBUG=debug,
        DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,[::1]",
        POSTGRES_HOST="::1",
    )
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["debug"] is (debug == "true")
    assert settings["database"]["HOST"] == "::1"
    assert settings["database"]["OPTIONS"]["hostaddr"] == "::1"


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize(
    "invalid",
    [
        {"DJANGO_SECRET_KEY": ""},
        {"DJANGO_SECRET_KEY": "   "},
        {"DJANGO_DEBUG": "yes"},
        {"DJANGO_ALLOWED_HOSTS": "*"},
        {"DJANGO_ALLOWED_HOSTS": "localhost,production.invalid"},
        {"DJANGO_ALLOWED_HOSTS": ""},
        {"POSTGRES_HOST": "production.invalid"},
    ],
)
def test_local_settings_reject_invalid_values(invalid):
    values = {"DJANGO_SECRET_KEY": "synthetic-local-key", **invalid}
    result = probe("relay.settings.local", **values)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


@pytest.mark.ac("PLT-1.4")
def test_local_settings_require_key_and_default_debug_off():
    assert probe("relay.settings.local").returncode != 0
    result = probe("relay.settings.local", DJANGO_SECRET_KEY="synthetic-local-key")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["debug"] is False
