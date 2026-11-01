import threading
import time
from unittest import mock

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import MessageEncoder
from django.contrib.messages.storage.session import SessionStorage
from django.db import connection, transaction
from django.test import Client

from accounts.models import User, Workspace
from rounds import services
from rounds.models import Case, Round
from rounds.templatetags.rounds_text import retest_message

PASSWORD = "Synthetic16Chars"
NEW = "/coordinator/rounds/new/"
DENIED = "You do not have access to this page."
NOT_FOUND = "Page not found."
UNAVAILABLE = "Relay is temporarily unavailable. Try again later."
TITLE_MESSAGE = "Enter 1 to 120 characters."
LIMIT_MESSAGE = "This workspace has reached its limit of 20 rounds."

# Red-team markup payload and the raw tags it must never leave in a page. Markup
# characters are stored as \x escapes (AGENTS.md: payloads are stored escaped);
# Python decodes them only when a test module loads.
MARKUP = (
    "\x3cscript\x3ealert(1)\x3c/script\x3e\x22\x27\x3e"
    "\x3cimg src=x onerror=alert(2)\x3e\x26amp;"
)
SCRIPT_TAG = "\x3cscript\x3e"
IMG_TAG = "\x3cimg"
assert SCRIPT_TAG in MARKUP and IMG_TAG in MARKUP


def assert_no_raw_markup(html):
    """`html` holds none of the payload's raw tags."""
    assert SCRIPT_TAG not in html
    assert IMG_TAG not in html


def title_tag(html):
    """The text inside the page's <title> element."""
    return html.split("<title>", 1)[1].split("</title>", 1)[0]


def no_store(response):
    """The response carries the private, no-store cache policy."""
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


def snapshot(*models, exclude=()):
    """Every row of `models`, by primary key, to show an action changed nothing.

    With no `models`, every model of the rounds app except those in `exclude`,
    so a new rounds model is checked without changing callers.
    """
    if not models:
        models = [
            model
            for model in apps.get_app_config("rounds").get_models()
            if model not in exclude
        ]
    return {model: list(model.objects.order_by("pk").values()) for model in models}


def locked(round_):
    """Lock the round row, as the views do before calling a service."""
    return Round.objects.select_for_update().get(pk=round_.pk)


def detail(round_id):
    """The round page URL."""
    return f"/coordinator/rounds/{round_id}/"


def edit(round_id):
    """The edit-round URL."""
    return f"/coordinator/rounds/{round_id}/edit/"


def draft_with_case(make_round):
    """A Draft round with one test case, so it shows a delete button."""
    round_ = make_round()
    Case.objects.create(
        round=round_, title="Synthetic case", steps="Steps", expected_result="Result"
    )
    return round_


def open_with_case(make_round):
    """An Open round with one test case, published on build Synthetic 1.0."""
    round_ = draft_with_case(make_round)
    with transaction.atomic():
        services.publish(locked(round_), "Synthetic 1.0")
    return round_


def close(client, round_):
    """POST the round's close action."""
    return client.post(f"{detail(round_.pk)}close/")


def stored_retest(client, round_, cases, label):
    """Retest `cases` of an Open round on `label` without its form.

    Calls the service and leaves `client` the success message the retest view
    would, for rendering stored text that the form refuses (rule 5).
    """
    with transaction.atomic():
        build = services.request_retest(
            locked(round_), label, [case.pk for case in cases]
        )
    text = retest_message(len(cases), build.label)
    session = client.session
    session[SessionStorage.session_key] = MessageEncoder().encode(
        [Message(constants.SUCCESS, text, extra_tags="retest")]
    )
    session.save()


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


def race(coordinator, first, second, slow):
    """Run `first` until it holds the round lock inside `slow`, then `second`.

    `slow` names services, or (object, attribute) pairs such as Round.save,
    whose call pauses after its work, still inside the view's locked
    transaction, so `second` arrives while `first` holds it.
    """
    inside = threading.Event()
    responses = {}
    targets = [(services, name) if isinstance(name, str) else name for name in slow]
    reals = {target: getattr(*target) for target in targets}

    def pausing(target):
        def run(*args, **kwargs):
            result = reals[target](*args, **kwargs)
            inside.set()
            time.sleep(0.3)
            return result

        return run

    def send(key, request):
        try:
            if key == "second":
                inside.wait(5)
            responses[key] = request(signed_in(coordinator))
        finally:
            connection.close()

    patches = [mock.patch.object(*target, pausing(target)) for target in targets]
    for patch in patches:
        patch.start()
    try:
        threads = [
            threading.Thread(target=send, args=(key, request))
            for key, request in (("first", first), ("second", second))
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for patch in patches:
            patch.stop()
    return responses["first"], responses["second"]


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
