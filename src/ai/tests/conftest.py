"""Fixtures for the AI app's DB-backed tests."""

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User, Workspace
from ai.gateway import DEPLOYMENT_SCOPE
from ai.models import CallSlot
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


@pytest.fixture(autouse=True)
def deployment_slots(request):
    """Ensure the two migration-seeded deployment slots for DB-backed tests.

    A transactional test elsewhere (ACC-3's, or a browser test's live server)
    flushes every table, seeded rows included, so these tests recreate them
    instead of depending on test order.
    """
    if not {"db", "transactional_db"} & set(request.fixturenames):
        return
    request.getfixturevalue("db")
    for key in ("0", "1"):
        CallSlot.objects.get_or_create(
            scope=DEPLOYMENT_SCOPE,
            key=key,
            defaults={"expires_at": timezone.now() - timedelta(seconds=1)},
        )
