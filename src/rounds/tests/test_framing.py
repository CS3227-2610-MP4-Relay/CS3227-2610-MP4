"""Every response refuses framing, in every environment (#58).

Checks the framing control in the security spec's rounds section and the
technical spec's Configuration; like the "never cached" tests, it has no
criterion ID.
"""

import json
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.sessions.models import Session
from django.db import DatabaseError, OperationalError
from django.test import Client

from relay.settings import base
from relay.tests.probes import probe
from rounds.models import Round

from .conftest import close, detail, draft_with_case, open_with_case, page, signed_in

pytestmark = pytest.mark.django_db

SRC = Path(__file__).resolve().parents[2]
TEST_DIRECTORIES = {"tests"}
# Lower-case text that exempts a view or sets the header or setting directly:
# the xframe_options_* decorators and attribute, the header, X_FRAME_OPTIONS.
OVERRIDES = ("xframe_options_", "x-frame-options", "x_frame_options")
FIRST_TWO = [
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
]


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


def failing_session_save():
    return mock.patch.object(Session, "save", side_effect=OperationalError("synthetic"))


def test_a_failed_session_save_after_a_view_still_refuses_framing(
    coordinator, make_round
):
    # SessionMiddleware makes this 400 (SessionInterrupted) after the view, so
    # only middleware above it sees the response.
    opened = open_with_case(make_round)
    client = signed_in(coordinator, raise_request_exception=False)
    with failing_session_save():
        refuses_framing(close(client, opened), 400)


def test_a_failed_new_session_at_sign_out_still_refuses_framing(coordinator):
    # The sign-out message needs a new session row; SessionMiddleware makes
    # the 500 when creating it fails.
    client = signed_in(coordinator, raise_request_exception=False)
    with failing_session_save():
        refuses_framing(client.post("/sign-out/"), 500)


def test_no_code_exempts_a_view_or_sets_framing_itself():
    named = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if not TEST_DIRECTORIES & set(path.relative_to(SRC).parts)
        # This operational helper only reads the header in deployment smoke checks.
        and path != SRC / "release.py"
        and any(text in path.read_text(encoding="utf-8").lower() for text in OVERRIDES)
    ]
    assert named == []


def test_framing_is_refused_by_the_shared_settings(settings):
    for middleware in (base.MIDDLEWARE, settings.MIDDLEWARE):
        assert middleware[:2] == FIRST_TWO
    assert settings.X_FRAME_OPTIONS == "DENY"


def test_framing_is_refused_by_the_local_settings():
    result = probe("relay.settings.local", DJANGO_SECRET_KEY="synthetic-local-key")
    assert result.returncode == 0, result.stderr
    framing = json.loads(result.stdout)["framing"]
    assert framing["middleware"][:2] == FIRST_TWO
    assert framing["x_frame_options"] == "DENY"


def test_an_anonymous_round_page_redirect_refuses_framing(make_round):
    response = Client().get(detail(make_round().pk))
    refuses_framing(response, 302)


@pytest.mark.parametrize(
    ("host", "status"), [("testserver", 301), ("disallowed.example", 400)]
)
def test_responses_made_by_the_security_middleware_refuse_framing(
    settings, host, status
):
    # The HTTPS redirect and the disallowed-host 400 are made inside
    # SecurityMiddleware, so only middleware above it sees them.
    settings.SECURE_SSL_REDIRECT = True
    refuses_framing(Client().get("/", HTTP_HOST=host), status)
