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
        "ruff check . && ruff format --check . && pytest",
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
    ):
        assert required in workflow
    for forbidden in ("pull_request_target", "secrets.", "contents: write"):
        assert forbidden not in workflow


@pytest.mark.ac("PLT-1.7")
def test_ci_installs_chromium_and_retains_only_browser_failure_files():
    workflow_path = Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"
    verify = workflow_path.read_text().split("\n  site:", 1)[0]
    install = ".venv/bin/python -m playwright install --with-deps chromium"
    checks = (
        "ruff check . && ruff format --check . && pytest "
        '--basetemp="$RUNNER_TEMP/relay-pytest"'
    )
    upload = "      - name: Retain browser failure diagnostics\n"
    assert verify.index(install) < verify.index(checks) < verify.index(upload)
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
