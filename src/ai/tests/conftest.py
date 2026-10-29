"""Fixtures for the AI app's DB-backed tests."""

import pytest

from accounts.models import User, Workspace
from rounds.tests.conftest import coord_client, make_round, other_workspace, tester

PASSWORD = "Synthetic16Chars"

__all__ = [
    "coord_client",
    "coordinator",
    "make_round",
    "other_workspace",
    "tester",
    "workspace",
]


@pytest.fixture
def workspace(db):
    """The AI tests' workspace."""
    return Workspace.objects.create(name="Demo workspace ai10001")


@pytest.fixture
def coordinator(workspace):
    """The workspace's Test Coordinator."""
    return User.objects.create_user(
        "coord-ai10001", PASSWORD, workspace=workspace, role="coordinator"
    )
