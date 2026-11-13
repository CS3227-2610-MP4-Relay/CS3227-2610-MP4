"""PLT-4.17: standalone error pages link back to the start page."""

from unittest import mock

import pytest
from django.db import DatabaseError
from django.shortcuts import render
from django.test import Client, RequestFactory
from django.utils.functional import SimpleLazyObject

from accounts.models import User, Workspace
from rounds.models import Round
from rounds.tests.conftest import PASSWORD, csrf_token, signed_in

DENIED = "You do not have access to this page."
NOT_FOUND = "Page not found."
LIMITED = "Too many demo workspaces have been created recently. Try again later."
UNAVAILABLE = "Relay is temporarily unavailable. Try again later."
PAGES = [
    ("403.html", 403, DENIED),
    ("404.html", 404, NOT_FOUND),
    ("429.html", 429, LIMITED),
    ("503.html", 503, UNAVAILABLE),
]
HOME_LINK = '<a class="action secondary" href="/">Back to home</a>'
NAVIGATION = f'<nav class="page-navigation" aria-label="Page navigation">{HOME_LINK}'


def assert_home_link(response, status, message):
    """One Back to home link precedes the unchanged message, the only heading."""
    assert response.status_code == status
    body = response.content.decode()
    assert body.count(HOME_LINK) == 1 and body.count("Back to home") == 1
    assert body.count(NAVIGATION) == 1
    assert body.count("<a ") == 1
    heading = f'<div class="error"><h1>{message}</h1></div>'
    assert body.count(heading) == 1 and body.count("<h1") == 1
    assert body.index(HOME_LINK) < body.index(heading)
    assert "<form" not in body
    return body


def unavailable(*args, **kwargs):
    raise AssertionError("error pages must not read the user or session")


class Untouchable:
    """A session that fails on any access."""

    def __getattr__(self, name):
        unavailable()


@pytest.fixture
def accounts(db):
    """A coordinator and a tester, and another workspace's round."""
    workspace = Workspace.objects.create(name="Demo workspace err18301")
    other = Workspace.objects.create(name="Demo workspace err18302")
    return {
        "coordinator": User.objects.create_user(
            "coord-err18301", PASSWORD, workspace=workspace, role="coordinator"
        ),
        "tester": User.objects.create_user(
            "tester-err18301", PASSWORD, workspace=workspace, role="tester"
        ),
        "foreign": Round.objects.create(workspace=other, title="Synthetic foreign"),
    }


def client_for(accounts, visitor):
    return Client() if visitor == "signed-out" else signed_in(accounts[visitor])


@pytest.mark.ac("PLT-4.17")
@pytest.mark.parametrize("template,status,message", PAGES)
def test_rendering_reads_no_user_session_or_database(
    db, django_assert_num_queries, template, status, message
):
    request = RequestFactory().get("/synthetic/")
    request.user = SimpleLazyObject(unavailable)
    request.session = Untouchable()
    with django_assert_num_queries(0):
        response = render(request, template, status=status)
    assert_home_link(response, status, message)


@pytest.mark.ac("PLT-4.17", "PLT-1.3")
@pytest.mark.parametrize("visitor", ["signed-out", "coordinator", "tester"])
def test_unknown_and_foreign_pages_link_home_for_every_visitor(accounts, visitor):
    client = client_for(accounts, visitor)
    unknown = client.get("/synthetic-missing-page/")
    body = assert_home_link(unknown, 404, NOT_FOUND)
    assert "<h1>Page not found.</h1>" in body  # release smoke-check marker
    if visitor == "coordinator":
        foreign = client.get(f"/coordinator/rounds/{accounts['foreign'].pk}/")
        assert_home_link(foreign, 404, NOT_FOUND)
        assert foreign.content == unknown.content


@pytest.mark.ac("PLT-4.17", "ACC-1.4")
@pytest.mark.parametrize(
    "visitor,path", [("tester", "/coordinator/"), ("coordinator", "/tester/")]
)
def test_permission_denied_links_home_without_workspace_data(accounts, visitor, path):
    body = assert_home_link(client_for(accounts, visitor).get(path), 403, DENIED)
    for private in ("Demo workspace err18301", "coord-err18301", "tester-err18301"):
        assert private not in body


@pytest.mark.ac("PLT-4.17", "ACC-4.5")
@pytest.mark.parametrize("token", ["missing", "foreign-origin"])
def test_csrf_failure_links_home_without_workspace_data(accounts, token):
    client = signed_in(accounts["coordinator"], enforce_csrf_checks=True)
    extra = {}
    if token == "foreign-origin":
        extra = {
            "HTTP_X_CSRFTOKEN": csrf_token(client),
            "HTTP_ORIGIN": "https://attacker.example",
        }
    before = User.objects.count()
    body = assert_home_link(
        client.post("/coordinator/testers/add/", **extra), 403, DENIED
    )
    for private in ("Demo workspace err18301", "coord-err18301", "tester-err18301"):
        assert private not in body
    assert User.objects.count() == before


@pytest.mark.ac("PLT-4.17", "ACC-3.4")
def test_demo_limit_links_home(db):
    with mock.patch("accounts.views._any_reached", return_value=True):
        response = Client().post("/demo/")
    assert_home_link(response, 429, LIMITED)
    assert not Workspace.objects.exists()


@pytest.mark.ac("PLT-4.17", "ACC-2.5")
def test_demo_failure_links_home(db):
    with mock.patch(
        "accounts.demo.generate_passwords", side_effect=RuntimeError("synthetic")
    ):
        response = Client().post("/demo/")
    assert_home_link(response, 503, UNAVAILABLE)
    assert not Workspace.objects.exists()


@pytest.mark.ac("PLT-4.17")
def test_storage_failure_loading_the_user_still_links_home(accounts):
    client = signed_in(accounts["coordinator"])
    with mock.patch(
        "django.contrib.auth.get_user", side_effect=DatabaseError("synthetic")
    ) as get_user:
        response = client.get("/coordinator/rounds/new/")
    # The view's own check fails once; rendering the 503 never retries the user.
    assert get_user.call_count == 1
    assert_home_link(response, 503, UNAVAILABLE)
