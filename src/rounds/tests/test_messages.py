"""Success messages stay in the server-side session, never in a cookie (#57)."""

from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import CookieStorage
from django.contrib.messages.storage.session import SessionStorage
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import OperationalError, connection, connections
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import escape

from rounds.models import Round

from .conftest import (
    MARKUP,
    ROUND_RECORDS,
    SCRIPT_TAG,
    close,
    detail,
    domain_rows,
    draft_with_case,
    open_with_case,
    page,
    signed_in,
    stored_retest,
)

pytestmark = pytest.mark.django_db

COOKIE = CookieStorage.cookie_name
SIGNED_OUT = "You have signed out."
FORGED_LABEL = "Synthetic forged label"
FALLBACK = "django.contrib.messages.storage.fallback.FallbackStorage"
HEADING = '<h1><span dir="auto">Synthetic round</span></h1>'
RLO, ZWSP, LRI = chr(0x202E), chr(0x200B), chr(0x2066)


def forged_cookie(text, tags="retest"):
    """A messages cookie signed as Django's cookie storage would sign it."""
    storage = CookieStorage(HttpRequest())
    return storage._encode([Message(constants.SUCCESS, text, extra_tags=tags)])


def stored_messages(client):
    """The messages kept in the client's session row, as stored."""
    key = client.cookies["sessionid"].value
    return Session.objects.get(session_key=key).get_decoded().get("_messages", "")


def publish(client, round_):
    return client.post(f"{detail(round_.pk)}publish/", {"label": "Synthetic 1.0"})


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


@pytest.mark.parametrize(
    "cookie_storage",
    [
        pytest.param(False, id="session-storage", marks=pytest.mark.ac("RND-5.8")),
        pytest.param(True, id="control"),
    ],
)
def test_a_forged_messages_cookie_is_ignored_by_the_round_page(
    coord_client, make_round, settings, cookie_storage
):
    # The control proves the forged cookie is one Django's cookie storage reads.
    if cookie_storage:
        settings.MESSAGE_STORAGE = FALLBACK
    round_ = open_with_case(make_round)
    text = f"Retest requested for 1 test case on build {FORGED_LABEL}."
    coord_client.cookies[COOKIE] = forged_cookie(text)
    response = coord_client.get(detail(round_.pk))
    assert response.status_code == 200
    assert HEADING in page(response)
    assert (FORGED_LABEL in page(response)) is cookie_storage


@pytest.mark.ac("ACC-1.5")
@pytest.mark.parametrize(
    ("act", "text"),
    [
        pytest.param(
            close, "Round closed.", id="close", marks=pytest.mark.ac("RND-6.1")
        ),
        pytest.param(
            retest,
            "Retest requested for 1 test case on build Synthetic 1.1.",
            id="retest",
            marks=pytest.mark.ac("RND-5.8"),
        ),
    ],
)
def test_sign_out_discards_an_unread_round_message(coord_client, make_round, act, text):
    round_ = open_with_case(make_round)
    assert act(coord_client, round_).status_code == 302
    coord_client.post("/sign-out/")
    html = page(coord_client.get("/sign-in/"))
    assert SIGNED_OUT in html
    assert text not in html


@pytest.mark.ac("RND-6.5")
def test_a_failed_session_save_rolls_back_close_with_503(coordinator, make_round):
    round_ = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    before = domain_rows(*ROUND_RECORDS)
    failing = mock.patch.object(
        Session, "save", side_effect=OperationalError("synthetic")
    )
    with failing as save:
        response = close(client, round_)
    round_.refresh_from_db()
    assert response.status_code == 503
    assert "Relay is temporarily unavailable. Try again later." in page(response)
    assert "no-store" in response["Cache-Control"]
    assert (round_.state, round_.closed_at) == (Round.State.OPEN, None)
    assert "Round closed." not in stored_messages(client)
    assert save.call_count == 1
    assert domain_rows(*ROUND_RECORDS) == before


@pytest.mark.ac("RND-6.1", "RND-6.5")
@pytest.mark.django_db(transaction=True)
def test_close_keeps_unread_messages_and_saves_session_before_commit(
    coord_client, make_round
):
    round_ = open_with_case(make_round)
    session = coord_client.session
    request = HttpRequest()
    request.session = session
    session["_messages"] = SessionStorage(request).serialize_messages(
        [Message(constants.SUCCESS, "Synthetic earlier notification.")]
    )
    session.save()
    key = session.session_key
    original_save = SessionStore.save
    calls = []

    def save_in_transaction(store, *args, **kwargs):
        calls.append(connection.in_atomic_block)
        assert Round.objects.get(pk=round_.pk).state == Round.State.CLOSED
        return original_save(store, *args, **kwargs)

    with mock.patch.object(SessionStore, "save", save_in_transaction):
        response = close(coord_client, round_)
    assert response.status_code == 302
    assert calls == [True]
    assert coord_client.cookies["sessionid"].value == key
    assert COOKIE not in response.cookies
    html = page(coord_client.get(detail(round_.pk)))
    assert html.count("Synthetic earlier notification.") == 1
    assert html.count("Round closed.") == 1
    html = page(coord_client.get(detail(round_.pk)))
    assert "Synthetic earlier notification." not in html
    assert "Round closed." not in html


@pytest.mark.ac("RND-6.5")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("failure", ["close-write", "commit"])
def test_close_transaction_failure_keeps_session_and_round_unchanged(
    coordinator, make_round, failure
):
    round_ = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    before = domain_rows(*ROUND_RECORDS)
    key = client.cookies["sessionid"].value
    session_before = Session.objects.get(session_key=key).session_data
    target = connection if failure == "commit" else QuerySet
    method = "commit" if failure == "commit" else "update"
    with mock.patch.object(target, method, side_effect=OperationalError("synthetic")):
        response = close(client, round_)
    assert response.status_code == 503
    assert "no-store" in response["Cache-Control"]
    round_.refresh_from_db()
    assert (round_.state, round_.closed_at) == (Round.State.OPEN, None)
    assert domain_rows(*ROUND_RECORDS) == before
    assert Session.objects.get(session_key=key).session_data == session_before
    assert "Round closed." not in page(client.get(detail(round_.pk)))


def delete_session_elsewhere(key):
    """Commit a concurrent sign-out's session deletion on another connection."""
    try:
        Session.objects.filter(session_key=key).delete()
    finally:
        connections.close_all()


@pytest.mark.ac("RND-6.5")
@pytest.mark.django_db(transaction=True)
def test_close_does_not_resurrect_a_concurrently_deleted_session(
    coordinator, make_round
):
    round_ = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    key = client.cookies["sessionid"].value
    original_save = SessionStore.save
    calls = []

    def save_after_sign_out(store, *args, **kwargs):
        calls.append(store.session_key)
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(delete_session_elsewhere, key).result(timeout=10)
        return original_save(store, *args, **kwargs)

    with mock.patch.object(SessionStore, "save", save_after_sign_out):
        response = close(client, round_)
    assert response.status_code == 503
    assert calls == [key]
    round_.refresh_from_db()
    assert (round_.state, round_.closed_at) == (Round.State.OPEN, None)
    assert not Session.objects.exists()


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize(
    "through_form, second_line, invisible",
    [
        pytest.param(True, "abc" + ZWSP + "ghi", (ZWSP,), id="retest-form"),
        # Stored without the form, which refuses text-direction controls (rule 5).
        pytest.param(
            False,
            "abc" + RLO + "def" + ZWSP + "ghi" + LRI,
            (RLO, ZWSP, LRI),
            id="stored",
        ),
    ],
)
def test_an_unread_retest_label_is_isolated_and_escaped_on_the_sign_in_page(
    coord_client, make_round, through_form, second_line, invisible
):
    round_ = open_with_case(make_round)
    label = MARKUP + "\n" + second_line
    if through_form:
        data = {"cases": [round_.cases.get().pk], "label": label}
        assert coord_client.post(f"{detail(round_.pk)}retest/", data).status_code == 302
    else:
        stored_retest(coord_client, round_, [round_.cases.get()], label)
    response = coord_client.get("/sign-in/")
    html = page(response)
    lines = (
        f'<span dir="auto">{escape(MARKUP)}</span><br>'
        f'<span dir="auto">{second_line}</span>'
    )
    status = f'<p role="status">Retest requested for 1 test case on build {lines}.</p>'
    assert response.status_code == 200
    assert html.count(status) == 1
    assert SCRIPT_TAG not in html
    for char in invisible:
        assert char not in html.replace(lines, ""), hex(ord(char))
