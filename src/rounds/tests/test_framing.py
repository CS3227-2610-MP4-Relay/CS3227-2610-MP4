"""Every response refuses framing, in every environment (#58).

Checks the framing control in the security spec's rounds section and the
technical spec's Configuration; like the "never cached" tests, it has no
criterion ID.
"""

from pathlib import Path
from unittest import mock

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.db import DatabaseError
from django.test import Client

from relay.settings import base
from rounds.models import Round

from .conftest import detail, page, signed_in
from .test_messages import close, draft_with_case, open_with_case

pytestmark = pytest.mark.django_db

SRC = Path(__file__).resolve().parents[2]
EXEMPTIONS = (
    "xframe_options_exempt",
    "xframe_options_sameorigin",
    "xframe_options_deny",
)


def refuses_framing(response, status):
    assert response.status_code == status
    assert response["X-Frame-Options"] == "DENY"


def test_public_pages_refuse_framing(client):
    refuses_framing(client.get("/"), 200)
    refuses_framing(client.post("/"), 405)
    refuses_framing(client.get("/sign-in/"), 200)
    refuses_framing(client.get("/no-such-page/"), 404)


def test_the_tester_home_refuses_framing(tester):
    refuses_framing(signed_in(tester).get("/tester/"), 200)


def test_round_pages_with_one_click_buttons_refuse_framing(coord_client, make_round):
    draft = draft_with_case(make_round)
    response = coord_client.get(detail(draft.pk))
    assert "Delete test case" in page(response)
    refuses_framing(response, 200)
    opened = open_with_case(make_round)
    response = coord_client.get(detail(opened.pk))
    assert "Close round" in page(response)
    refuses_framing(response, 200)


def test_round_error_responses_refuse_framing(
    coord_client, make_round, other_workspace
):
    other = make_round(owner=other_workspace)
    refuses_framing(coord_client.get(detail(other.pk)), 404)
    closed = make_round(state=Round.State.CLOSED)
    refuses_framing(close(coord_client, closed), 409)
    with mock.patch(
        "rounds.views.get_object_or_404", side_effect=DatabaseError("synthetic")
    ):
        refuses_framing(coord_client.get(detail(closed.pk)), 503)


def test_a_csrf_failure_refuses_framing(coordinator, make_round):
    opened = open_with_case(make_round)
    client = signed_in(coordinator, enforce_csrf_checks=True)
    refuses_framing(close(client, opened), 403)


def test_a_failed_session_save_after_a_view_still_refuses_framing(
    coordinator, make_round
):
    # The 500 is made by SessionMiddleware, so this fails if the framing
    # middleware sits below it.
    opened = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    with mock.patch.object(
        SessionStore, "save", side_effect=DatabaseError("synthetic")
    ):
        refuses_framing(close(client, opened), 500)


def test_no_view_is_exempt_from_framing_refusal():
    named = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if "tests" not in path.parts
        and any(name in path.read_text(encoding="utf-8") for name in EXEMPTIONS)
    ]
    assert named == []


def test_framing_is_refused_by_the_shared_settings(settings):
    for middleware in (base.MIDDLEWARE, settings.MIDDLEWARE):
        assert middleware[:2] == [
            "django.middleware.security.SecurityMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ]
    assert not hasattr(base, "X_FRAME_OPTIONS")
    assert settings.X_FRAME_OPTIONS == "DENY"


def test_an_anonymous_round_page_redirect_refuses_framing(make_round):
    response = Client().get(detail(make_round().pk))
    refuses_framing(response, 302)
