from pathlib import Path

import pytest


@pytest.mark.ac("PLT-1.7")
def test_ci_runs_isolated_application_verification():
    workflow_path = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
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
