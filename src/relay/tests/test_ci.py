from pathlib import Path

import pytest


@pytest.mark.ac("PLT-1.7")
def test_ci_runs_isolated_application_verification():
    workflow_path = Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"
    workflow = workflow_path.read_text()
    for required in (
        "pull_request:",
        "push:",
        "- main",
        "contents: read",
        "persist-credentials: false",
        "postgres:17.6",
        '"55432:5432"',
        "POSTGRES_DB: relay_test",
        "POSTGRES_USER: relay_test",
        "POSTGRES_PASSWORD: relay_test",
        "python src/manage.py check --settings=relay.settings.test",
        "ruff check . && ruff format --check .",
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
    ):
        assert required in workflow
    for forbidden in ("pull_request_target", "contents: write"):
        assert forbidden not in workflow
    validation = workflow.split("\n  production:\n", 1)[0]
    assert "secrets." not in validation


@pytest.mark.ac("PLT-1.7")
def test_ci_installs_chromium_and_retains_only_browser_failure_files():
    workflow_path = Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"
    verify = workflow_path.read_text().split("\n  site:", 1)[0]
    install = ".venv/bin/python -m playwright install --with-deps chromium"
    checks = "ruff check . && ruff format --check ."
    injection = 'pytest -m prompt_injection --basetemp="$RUNNER_TEMP/relay-pytest"'
    remaining = (
        "pytest -m 'not prompt_injection' --basetemp=\"$RUNNER_TEMP/relay-pytest\""
    )
    upload = "      - name: Retain browser failure diagnostics\n"
    assert (
        verify.index(install)
        < verify.index(checks)
        < verify.index(injection)
        < verify.index(remaining)
        < verify.index(upload)
    )
    assert [
        line.strip()
        for line in verify.splitlines()
        if line.strip().startswith("pytest ")
    ] == [injection, remaining]
    assert "      - name: Run prompt-injection regressions\n" in verify
    assert "      - name: Run remaining regression suite\n" in verify
    artifact = verify.split(upload, 1)[1]
    assert "        if: failure()\n" in artifact
    assert (
        "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9" in artifact
    )
    paths = {
        line.strip()
        for line in artifact.splitlines()
        if line.startswith("            ")
    }
    assert paths == {
        "${{ runner.temp }}/relay-pytest/**/browser-failure.png",
        "${{ runner.temp }}/relay-pytest/**/browser-trace.zip",
    }
    assert "          if-no-files-found: ignore\n" in artifact
    assert "          retention-days: 3\n" in artifact
    assert "continue-on-error" not in verify


@pytest.mark.ac("PLT-1.9", "PLT-1.10", "PLT-1.11")
def test_production_job_is_opt_in_verified_main_only_and_secret_scoped():
    workflow = (
        Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"
    ).read_text()
    production = workflow.split("\n  production:\n", 1)[1]
    for condition in (
        "github.event_name == 'push'",
        "github.ref == 'refs/heads/main'",
        "vars.PRODUCTION_DEPLOY_ENABLED == 'true'",
    ):
        assert condition in production.split("    needs:", 1)[0]
    for required in (
        "needs: [verify, site]",
        "name: production",
        "contents: read",
        "group: production",
        "cancel-in-progress: false",
        "ref: ${{ github.sha }}",
        "persist-credentials: false",
    ):
        assert required in production
    for forbidden in ("always()", "continue-on-error", "workflow_dispatch", "secrets."):
        assert forbidden not in workflow.split("\n  production:\n", 1)[0]
    assert "always()" not in production and "continue-on-error" not in production
    install, migration = production.split("      - name: Check and migrate", 1)
    migration, deploy = migration.split("      - name: Deploy and smoke", 1)
    assert "secrets." not in install
    assert "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e" in install
    assert 'node-version: "24.18.0"' in install
    assert "package-manager-cache: false" in install
    assert "npm install --global vercel@64.3.1" in install
    assert "VERCEL_TOKEN" not in migration
    assert (
        "secrets.DATABASE_URL" in migration and "secrets.DJANGO_SECRET_KEY" in migration
    )
    assert "python src/release.py migrate" in migration
    assert "python src/release.py deploy" in deploy
    assert "secrets.VERCEL_TOKEN" in deploy
    assert "DATABASE_URL" not in deploy and "DJANGO_SECRET_KEY" not in deploy
