import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2]
PROBE = SRC / "relay" / "tests" / "settings_probe.py"


@pytest.mark.ac("PLT-1.4", "PLT-1.8", "PLT-1.12")
@pytest.mark.parametrize("production", [True, False])
def test_wsgi_file_import_starts_without_pythonpath(tmp_path, production):
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    environment["DJANGO_SECRET_KEY"] = "synthetic-startup-key-" * 4
    if production:
        environment.update(
            DJANGO_SETTINGS_MODULE="relay.settings.production",
            DJANGO_PRODUCTION_HOST="relay.example.com",
            DATABASE_URL="postgresql://synthetic:synthetic@db.example.com/relay",
            DJANGO_TRUST_PROXY_SSL_HEADER="false",
        )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(PROBE.with_name("wsgi_probe.py")),
            str(SRC / "relay/wsgi.py"),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert (
        response["settings"]
        == f"relay.settings.{'production' if production else 'local'}"
    )
    assert response["status"] == ["200 OK"]
    assert "A beta-testing portal for small software teams." in response["body"]


def probe(module, **values):
    """Inspect settings without inheriting any runtime configuration."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "POSTGRES_", "SOC_LLM_", "DATABASE_URL"))
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
        DATABASE_URL="postgresql://synthetic:synthetic@production.invalid/production",
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
            str(SRC / "relay" / "tests" / "pytest_startup_probe.py"),
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
            str(SRC / "relay/tests/database_destination_probe.py"),
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


PRODUCTION = {
    "DJANGO_SECRET_KEY": "synthetic-production-key-long-enough-for-checks-123456789",
    "DJANGO_PRODUCTION_HOST": "relay.example.com",
    "DATABASE_URL": "postgresql://user:p%40ss@ep-synthetic-pooler.neon.tech/relay",
    "DJANGO_TRUST_PROXY_SSL_HEADER": "true",
}


@pytest.mark.ac("PLT-1.8")
@pytest.mark.parametrize("pooled", [True, False])
def test_production_configuration_uses_verified_tls_and_secure_responses(pooled):
    values = {**PRODUCTION, "DJANGO_DEBUG": "true", "DJANGO_ALLOWED_HOSTS": "*"}
    if not pooled:
        values["DATABASE_URL"] = values["DATABASE_URL"].replace("-pooler", "")
    result = probe("relay.settings.production", **values)
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["debug"] is False
    assert settings["hosts"] == ["relay.example.com"]
    database = settings["database"]
    assert database["USER"] == "user" and database["PASSWORD"] == "p@ss"
    assert database["NAME"] == "relay" and database["PORT"] == 5432
    assert ("-pooler" in database["HOST"]) is pooled
    assert database["CONN_MAX_AGE"] == 0
    assert database["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert database["OPTIONS"] == {
        "sslmode": "verify-full",
        "sslrootcert": "system",
        "connect_timeout": 10,
    }
    runtime = settings["runtime"]
    assert runtime["statuses"] == [200, 200, 404]
    assert runtime["csrf_secure"] is True
    assert runtime["csrf_origins"] == ["https://relay.example.com"]
    assert runtime["foreign_origin"] == 403
    assert runtime["hostile_host"] == 400
    assert runtime["proxy_https"] == 200
    assert runtime["proxy_hsts"] == "max-age=31536000"
    assert runtime["plain_http"] == 301
    assert runtime["deployment_checks"] == []
    assert runtime["silenced_checks"] == ["security.W005", "security.W021"]
    for headers in runtime["headers"]:
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Strict-Transport-Security"] == "max-age=31536000"
        assert headers["X-Content-Type-Options"] == "nosniff"
    for key, value in database["OPTIONS"].items():
        assert runtime["connection"][key] == value
    assert runtime["libpq"] >= 160000  # sslrootcert=system support.


@pytest.mark.ac("PLT-1.8")
def test_bootstrap_does_not_implicitly_trust_a_proxy_header():
    values = {**PRODUCTION, "DJANGO_TRUST_PROXY_SSL_HEADER": "false"}
    for flag in ("false", None):
        if flag is None:
            values.pop("DJANGO_TRUST_PROXY_SSL_HEADER")
        result = probe("relay.settings.production", **values)
        assert result.returncode == 0, result.stderr
        runtime = json.loads(result.stdout)["runtime"]
        assert runtime["plain_http"] == 200
        assert runtime["proxy_hsts"] == ""
        assert "security.W008" in runtime["deployment_checks"]


@pytest.mark.ac("PLT-1.8")
@pytest.mark.parametrize(
    "name,value",
    [
        ("DJANGO_SECRET_KEY", ""),
        ("DJANGO_SECRET_KEY", "   "),
        ("DJANGO_PRODUCTION_HOST", ""),
        *[
            ("DJANGO_PRODUCTION_HOST", value)
            for value in (
                "*",
                "https://relay.example.com",
                "relay.example.com/path",
                "relay.example.com:443",
                "localhost",
                "127.0.0.1",
                "[::1]",
                "relay.example.com,foreign.invalid",
                "relay.example.com\n",
                "a" * 64 + ".example.com",
                ".".join(["a" * 63] * 3 + ["b" * 62]),
            )
        ],
        ("DJANGO_TRUST_PROXY_SSL_HEADER", "yes"),
        *[
            ("DATABASE_URL", value)
            for value in (
                "",
                "not-a-url",
                "mysql://user:pass@ep-synthetic.neon.tech/relay",
                "postgresql://user@ep-synthetic.neon.tech/relay",
                "postgresql://user:pass@localhost/relay",
                "postgresql://user:pass@127.0.0.1/relay",
                "postgresql://user:pass@ep-synthetic.neon.tech/",
                "postgresql://user:pass@ep-synthetic.neon.tech:bad/relay",
                "postgresql://user:pass@ep-synthetic.neon.tech/relay?sslmode=disable",
                "postgresql://user:pass@ep-synthetic.neon.tech/relay?host=foreign.invalid",
                "postgresql://user:pass@ep-synthetic.neon.tech/relay#fragment",
            )
        ],
    ],
)
def test_production_rejects_invalid_configuration_without_values(name, value):
    result = probe("relay.settings.production", **{**PRODUCTION, name: value})
    assert result.returncode != 0
    assert f"ImproperlyConfigured: {name} is invalid or missing." in result.stderr
    assert PRODUCTION["DJANGO_SECRET_KEY"] not in result.stderr
    assert "user:p%40ss" not in result.stderr
    if value.strip() and len(value) > 10:
        assert value not in result.stderr


@pytest.mark.ac("PLT-1.8", "PLT-1.10")
def test_native_vercel_configuration_disables_unverified_git_deployment():
    root = SRC.parent
    configuration = json.loads((root / "vercel.json").read_text())
    assert configuration["git"]["deploymentEnabled"] is False
    assert configuration["functions"] == {"src/relay/wsgi.py": {"maxDuration": 60}}
    assert "builds" not in configuration and "routes" not in configuration
    assert (root / ".python-version").read_text().strip() == "3.14"


@pytest.mark.ac("PLT-1.8")
@pytest.mark.parametrize(
    "port,valid", [(0, False), (1, True), (65535, True), (65536, False)]
)
def test_production_database_port_boundaries(port, valid):
    values = {
        **PRODUCTION,
        "DATABASE_URL": f"postgresql://user:pass@ep-synthetic.neon.tech:{port}/relay",
    }
    result = probe("relay.settings.production", **values)
    if valid:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["database"]["PORT"] == port
    else:
        assert result.returncode != 0
        assert (
            "ImproperlyConfigured: DATABASE_URL is invalid or missing." in result.stderr
        )


@pytest.mark.ac("PLT-1.8")
def test_production_accepts_maximum_dns_host_length_and_safe_url_query():
    host = ".".join(["a" * 63] * 3 + ["b" * 61])
    assert len(host) == 253
    result = probe(
        "relay.settings.production",
        **{
            **PRODUCTION,
            "DJANGO_PRODUCTION_HOST": host,
            "DATABASE_URL": PRODUCTION["DATABASE_URL"] + "?sslmode=verify-full",
        },
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hosts"] == [host]
