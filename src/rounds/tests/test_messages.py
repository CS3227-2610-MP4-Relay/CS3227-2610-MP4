"""Success messages stay in the server-side session, never in a cookie (#57)."""

from unittest import mock

import pytest
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import CookieStorage
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import DatabaseError, transaction
from django.http import HttpRequest

from rounds import services
from rounds.models import Case, Round

from .conftest import detail, page, signed_in

pytestmark = pytest.mark.django_db

COOKIE = CookieStorage.cookie_name
SIGNED_OUT = "You have signed out."
FORGED_LABEL = "Synthetic forged label"


def forged_cookie(text, tags="retest"):
    """A messages cookie signed as Django's cookie storage would sign it."""
    storage = CookieStorage(HttpRequest())
    return storage._encode([Message(constants.SUCCESS, text, extra_tags=tags)])


def stored_messages(client):
    """The messages kept in the client's session row, as stored."""
    key = client.cookies["sessionid"].value
    return Session.objects.get(session_key=key).get_decoded().get("_messages", "")


def draft_with_case(make_round):
    round_ = make_round()
    Case.objects.create(
        round=round_, title="Synthetic case", steps="Steps", expected_result="Result"
    )
    return round_


def open_with_case(make_round):
    round_ = draft_with_case(make_round)
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=round_.pk)
        services.publish(locked, "Synthetic 1.0")
    return round_


def publish(client, round_):
    return client.post(f"{detail(round_.pk)}publish/", {"label": "Synthetic 1.0"})


def close(client, round_):
    return client.post(f"{detail(round_.pk)}close/")


def retest(client, round_):
    data = {"cases": [round_.cases.get().pk], "label": "Synthetic 1.1"}
    return client.post(f"{detail(round_.pk)}retest/", data)


ACTIONS = [
    pytest.param(
        draft_with_case,
        publish,
        "Round published.",
        "Round published.",
        id="publish",
        marks=pytest.mark.ac("RND-3.1"),
    ),
    pytest.param(
        open_with_case,
        close,
        "Round closed.",
        "Round closed.",
        id="close",
        marks=pytest.mark.ac("RND-6.1"),
    ),
    pytest.param(
        open_with_case,
        retest,
        "Retest requested for 1 test case on build Synthetic 1.1.",
        'Retest requested for 1 test case on build <span dir="auto">Synthetic 1.1'
        "</span>.",
        id="retest",
        marks=pytest.mark.ac("RND-5.1"),
    ),
]


@pytest.mark.parametrize(("setup", "act", "text", "html"), ACTIONS)
def test_a_success_message_is_kept_in_the_session_not_a_cookie(
    coord_client, make_round, setup, act, text, html
):
    round_ = setup(make_round)
    key = coord_client.cookies["sessionid"].value
    response = act(coord_client, round_)
    assert response.status_code == 302
    assert COOKIE not in response.cookies
    assert coord_client.cookies["sessionid"].value == key
    assert text in stored_messages(coord_client)
    shown = coord_client.get(detail(round_.pk))
    assert COOKIE not in shown.cookies
    assert page(shown).count(html) == 1
    assert html not in page(coord_client.get(detail(round_.pk)))
    assert text not in stored_messages(coord_client)


@pytest.mark.ac("RND-5.8")
def test_a_forged_messages_cookie_is_ignored_by_the_round_page(
    coord_client, make_round
):
    round_ = open_with_case(make_round)
    text = f"Retest requested for 1 test case on build {FORGED_LABEL}."
    coord_client.cookies[COOKIE] = forged_cookie(text)
    assert FORGED_LABEL not in page(coord_client.get(detail(round_.pk)))


@pytest.mark.ac("RND-5.8", "ACC-1.5")
@pytest.mark.parametrize(
    ("act", "text"),
    [
        (close, "Round closed."),
        (retest, "Retest requested for 1 test case on build Synthetic 1.1."),
    ],
    ids=["close", "retest"],
)
def test_sign_out_discards_an_unread_round_message(coord_client, make_round, act, text):
    round_ = open_with_case(make_round)
    assert act(coord_client, round_).status_code == 302
    coord_client.post("/sign-out/")
    html = page(coord_client.get("/sign-in/"))
    assert SIGNED_OUT in html
    assert text not in html


@pytest.mark.ac("RND-6.5")
def test_a_failed_session_save_after_a_close_gives_500_with_the_round_closed(
    coordinator, make_round
):
    # Accepted residual (#57): the session is saved after the view commits.
    round_ = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    failing = mock.patch.object(
        SessionStore, "save", side_effect=DatabaseError("synthetic")
    )
    with failing:
        response = close(client, round_)
    round_.refresh_from_db()
    assert response.status_code == 500
    assert round_.state == Round.State.CLOSED
