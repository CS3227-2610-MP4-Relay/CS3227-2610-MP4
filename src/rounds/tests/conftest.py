import pytest
from django.conf import settings as django_settings
from django.test import Client

from accounts.models import User, Workspace
from rounds.models import Round

PASSWORD = "Synthetic16Chars"
NEW = "/coordinator/rounds/new/"
DENIED = "You do not have access to this page."
NOT_FOUND = "Page not found."
UNAVAILABLE = "Relay is temporarily unavailable. Try again later."
TITLE_MESSAGE = "Enter 1 to 120 characters."
LIMIT_MESSAGE = "This workspace has reached its limit of 20 rounds."


def detail(round_id):
    """The round page URL."""
    return f"/coordinator/rounds/{round_id}/"


def edit(round_id):
    """The edit-round URL."""
    return f"/coordinator/rounds/{round_id}/edit/"


def page(response):
    """The response body as text."""
    return response.content.decode()


def signed_in(user, **kwargs):
    """A test client signed in as `user`."""
    client = Client(**kwargs)
    client.force_login(user)
    return client


def csrf_token(client):
    """Load a page that sets the CSRF cookie and return its token."""
    client.get("/sign-in/")
    return client.cookies[django_settings.CSRF_COOKIE_NAME].value


@pytest.fixture
def workspace(db):
    """The signed-in coordinator's workspace."""
    return Workspace.objects.create(name="Demo workspace rnd10001")


@pytest.fixture
def other_workspace(db):
    """Another workspace."""
    return Workspace.objects.create(name="Demo workspace rnd10002")


@pytest.fixture
def coordinator(workspace):
    """The workspace's Test Coordinator."""
    return User.objects.create_user(
        "coord-rnd10001", PASSWORD, workspace=workspace, role="coordinator"
    )


@pytest.fixture
def tester(workspace):
    """A Beta Tester in the same workspace."""
    return User.objects.create_user(
        "tester1-rnd10001", PASSWORD, workspace=workspace, role="tester"
    )


@pytest.fixture
def other_coordinator(other_workspace):
    """The other workspace's Test Coordinator."""
    return User.objects.create_user(
        "coord-rnd10002", PASSWORD, workspace=other_workspace, role="coordinator"
    )


@pytest.fixture
def coord_client(coordinator):
    """A client signed in as the coordinator."""
    return signed_in(coordinator)


@pytest.fixture
def make_round(workspace):
    """Create a round directly, in any state and workspace."""

    def make(title="Synthetic round", state=Round.State.DRAFT, owner=None):
        return Round.objects.create(
            workspace=owner or workspace, title=title, state=state
        )

    return make
