"""ACC-5 tester-only password replacement, sessions and transient credentials."""

import logging
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import DatabaseError, connection, transaction
from django.template.loader import render_to_string
from django.test import Client
from django.views.debug import ExceptionReporter

from accounts import demo, limits, testers, views
from accounts.models import User
from accounts.tests.test_add_tester import SAVE, row, seed, signed_in, uncached
from relay.tests.test_access_matrix import every_row
from rounds.models import Build, Case, Result, Round

LIST = "/coordinator/testers/"
OLD = "SyntheticInitial16"


def reset_url(tester):
    return f"{LIST}{tester.pk}/reset-password/"


def members():
    """Seed usable own and foreign accounts, without real credentials."""
    workspace, coord = seed()
    _, foreign_coord = seed(label="foreign")
    tester, peer = list(workspace.accounts.filter(role="tester").order_by("pk"))
    for account in (tester, peer):
        account.set_password(OLD)
        account.save(update_fields=["password"])
    return workspace, coord, tester, peer, foreign_coord


def fail_after_credential_render(*args, **kwargs):
    """Fail with generated text in a frame, without fixture literals in source."""
    page = render_to_string(*args, **kwargs)
    assert SAVE in page
    raise RuntimeError("synthetic rendering failure")


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.1", "ACC-5.2", "ACC-5.3", "ACC-5.5", "ACC-5.7")
def test_reset_preserves_history_revokes_old_sessions_and_shows_password_once(caplog):
    workspace, coord, tester, peer, foreign = members()
    round_ = Round.objects.create(workspace=workspace, title="Synthetic round")
    case = Case.objects.create(round=round_, title="Synthetic case")
    build = Build.objects.create(round=round_, label="Synthetic build", key="synthetic")
    Result.objects.create(tester=tester, case=case, build=build, outcome="pass")
    client, peer_client = signed_in(coord), signed_in(peer)
    old_sessions = [signed_in(tester), signed_in(tester)]
    old_cookies = [session.cookies.copy() for session in old_sessions]
    coordinator_session = client.session.session_key
    before = every_row()
    home = client.get("/coordinator/")
    assert b">Beta Tester passwords</a>" in home.content
    listing = client.get(LIST)
    assert listing.status_code == 200
    uncached(listing)
    html = listing.content.decode()
    assert "<title>Beta Tester passwords</title>" in html
    assert workspace.name in html
    assert tester.username in html and peer.username in html
    assert foreign.username not in html and "tester-foreign" not in html
    assert f"{reset_url(coord)}" not in html
    assert (
        "Resetting a password stops the old password and existing tester sessions"
        in html
    )
    caplog.set_level(logging.DEBUG)
    response = client.post(
        reset_url(tester)
        + f"?workspace={foreign.workspace_id}&next=https://evil.invalid",
        {
            "username": peer.username,
            "password": "AttackerChosen16",
            "role": "coordinator",
            "workspace_id": foreign.workspace_id,
            "tester_id": peer.pk,
        },
    )
    assert response.status_code == 200
    uncached(response)
    role, username, password = row(response)
    assert role == "Beta Tester" and username == tester.username
    assert re.fullmatch(r"[a-zA-Z0-9]{16}", password) and password != OLD
    assert b"<h1>Beta Tester password reset</h1>" in response.content
    assert SAVE in response.content.decode()
    assert f'href="{LIST}"' in response.content.decode()
    after = every_row()
    changed = next(item for item in after["User"] if item["id"] == tester.pk)
    assert changed["password"] != tester.password and changed["password"] != password
    changed["password"] = tester.password
    assert after == before
    assert client.session.session_key == coordinator_session
    assert client.get("/coordinator/").status_code == 200
    assert peer_client.get("/tester/").status_code == 200
    assert authenticate(username=username, password=OLD) is None
    for session, cookie in zip(old_sessions, old_cookies, strict=True):
        assert session.get("/tester/")["Location"] == "/sign-in/"
        session.cookies = cookie
        assert session.get("/tester/")["Location"] == "/sign-in/"
    for route in (LIST, "/coordinator/"):
        assert password not in client.get(route).content.decode()
    assert password not in str(dict(client.session)) + str(client.cookies)
    assert password not in caplog.text + str(every_row()) + str(response.cookies)
    replacement = Client()
    assert replacement.login(username=username, password=password)
    assert workspace.name in replacement.get("/tester/").content.decode()
    repeated = client.post(reset_url(tester))
    assert repeated.status_code == 200
    second = row(repeated)[2]
    assert second != password
    assert authenticate(username=username, password=password) is None
    assert authenticate(username=username, password=second).pk == tester.pk
    assert replacement.get("/tester/")["Location"] == "/sign-in/"


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.3", "ACC-5.5")
@pytest.mark.parametrize(
    "target", ["foreign", "coordinator", "self", "missing", "huge"]
)
def test_invalid_targets_are_indistinguishable_and_never_generate(target):
    _, coord, tester, _, foreign = members()
    client = signed_in(coord)
    ids = {
        "foreign": foreign.workspace.accounts.get(username="tester-foreign-0").pk,
        "coordinator": foreign.pk,
        "self": coord.pk,
        "missing": 2_000_000_001,
        "huge": 99999999999999999999,
    }
    before = every_row()
    with mock.patch(
        "accounts.demo.generate_password", side_effect=AssertionError("generated")
    ):
        response = client.post(f"{LIST}{ids[target]}/reset-password/")
    assert response.status_code == 404
    assert response.content == client.get("/no-such-account/").content
    uncached(response)
    assert every_row() == before
    assert tester.username not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.1", "ACC-5.5")
@pytest.mark.parametrize("count", [0, 1, 10])
def test_list_boundaries_and_escaping(count):
    workspace, coord = seed(count)
    seed(label="foreign")
    if count:
        tester = workspace.accounts.filter(role="tester").first()
        tester.username = '<script>alert("synthetic")</script>'
        tester.save(update_fields=["username"])
    response = signed_in(coord).get(LIST)
    assert response.status_code == 200
    uncached(response)
    html = response.content.decode()
    assert html.count(">Reset password</button>") == count
    assert "tester-foreign" not in html
    assert ("This workspace has no Beta Testers." in html) == (count == 0)
    if count:
        assert tester.username not in html and "&lt;script&gt;" in html


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.3", "ACC-5.4", "ACC-5.5")
@pytest.mark.parametrize("caller", ["anonymous", "tester", "coordinator"])
def test_roles_methods_csrf_and_origin_precede_workspace_queries(caller):
    _, coord, tester, _, _ = members()
    client = Client(enforce_csrf_checks=True)
    if caller != "anonymous":
        client.force_login(coord if caller == "coordinator" else tester)
    client.get("/sign-in/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    before = every_row()
    with mock.patch.object(
        testers, "tester_records", side_effect=AssertionError("queried")
    ):
        for route, allowed, methods in (
            (LIST, "GET", ["head", "put", "delete", "options", "post"]),
            (reset_url(tester), "POST", ["head", "put", "delete", "options", "get"]),
        ):
            for method in methods:
                response = getattr(client, method)(route, HTTP_X_CSRFTOKEN=token)
                assert response.status_code == 405
                assert response["Allow"] == allowed
                uncached(response)
            for headers in (
                {},
                {"HTTP_X_CSRFTOKEN": "x" * 32},
                {"HTTP_X_CSRFTOKEN": token, "HTTP_ORIGIN": "https://evil.invalid"},
            ):
                assert client.post(route, **headers).status_code == 403
        if caller != "coordinator":
            for route, method in ((LIST, "get"), (reset_url(tester), "post")):
                response = getattr(client, method)(route, HTTP_X_CSRFTOKEN=token)
                assert response.status_code == (302 if caller == "anonymous" else 403)
                uncached(response)
                assert tester.username not in response.content.decode()
    assert every_row() == before
    if caller == "coordinator":
        response = client.post(
            reset_url(tester), HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://testserver"
        )
        assert response.status_code == 200


@pytest.fixture
def reset_errors():
    """Capture exceptions privately to inspect Django's report redaction."""
    errors = []
    real_error = views.logger.error

    def record(*args, **kwargs):
        errors.append(sys.exc_info())
        return real_error(*args, **kwargs)

    with mock.patch.object(views.logger, "error", record):
        yield errors


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.2", "ACC-5.5", "ACC-5.6")
@pytest.mark.parametrize(
    "failure", ["read", "generate", "hash", "write", "render", "password exception"]
)
def test_reset_failures_preserve_old_password_and_sessions(
    failure, caplog, reset_errors
):
    _, coord, tester, _, _ = members()
    client, session = signed_in(coord), signed_in(tester)
    before = every_row()
    synthetic = "SyntheticReset16"

    faults = {
        "read": ("accounts.testers.tester_records", DatabaseError("read failed")),
        "generate": ("accounts.demo._random", RuntimeError("generation failed")),
        "hash": ("accounts.demo.make_password", RuntimeError("hash failed")),
        "write": ("accounts.models.User.save", DatabaseError("write failed")),
        "render": ("accounts.views.render_to_string", fail_after_credential_render),
        "password exception": (
            "accounts.views.render_to_string",
            RuntimeError(synthetic),
        ),
    }
    target, action = faults[failure]
    with (
        mock.patch.object(demo, "_random", return_value=synthetic),
        mock.patch(target, side_effect=action),
    ):
        response = client.post(reset_url(tester))
    assert response.status_code == 503
    uncached(response)
    assert every_row() == before
    assert authenticate(username=tester.username, password=OLD).pk == tester.pk
    assert session.get("/tester/").status_code == 200
    assert synthetic not in response.content.decode() + caplog.text + str(
        dict(client.session)
    )
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "Beta Tester password reset failed."
    ]
    assert len(records) == 1 and records[0].exc_info is None
    if failure != "password exception":
        assert (
            synthetic
            not in ExceptionReporter(None, *reset_errors[0]).get_traceback_html()
        )


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.5", "ACC-5.6")
@pytest.mark.parametrize("route", [LIST, "reset"])
@pytest.mark.parametrize("failure", ["session", "read", "render"])
def test_route_loading_and_list_render_failures_are_uncached_503(route, failure):
    _, coord, tester, _, _ = members()
    client = signed_in(coord)
    before = every_row()
    target = {
        "session": "django.contrib.auth.get_user",
        "read": "accounts.testers.tester_records",
        "render": "accounts.views.render",
    }[failure]
    if failure == "render" and route == "reset":
        target = "accounts.views.render_to_string"
    real_render = views.render

    def render_failure(request, template, *args, **kwargs):
        if template != "503.html":
            raise RuntimeError("synthetic list rendering failure")
        return real_render(request, template, *args, **kwargs)

    action = (
        render_failure
        if target == "accounts.views.render"
        else DatabaseError("synthetic failure")
    )
    with mock.patch(target, side_effect=action):
        response = (
            client.get(route) if route == LIST else client.post(reset_url(tester))
        )
    assert response.status_code == 503
    uncached(response)
    assert tester.username not in response.content.decode()
    assert every_row() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-5.2", "ACC-5.5", "ACC-5.6")
def test_hashing_precedes_transaction_and_commit_failure_rolls_back(
    caplog, reset_errors
):
    _, coord, tester, _, _ = members()
    client, session = signed_in(coord), signed_in(tester)
    before, seen = every_row(), []
    real_hash = demo.make_password

    def hash_password(password):
        assert not connection.in_atomic_block
        seen.append(password)
        return real_hash(password)

    with (
        mock.patch.object(demo, "make_password", hash_password),
        mock.patch.object(
            connection, "commit", side_effect=DatabaseError("synthetic commit failure")
        ),
    ):
        response = client.post(reset_url(tester))
    assert response.status_code == 503 and len(seen) == 1
    assert every_row() == before
    assert session.get("/tester/").status_code == 200
    assert authenticate(username=tester.username, password=OLD).pk == tester.pk
    report = ExceptionReporter(None, *reset_errors[0]).get_traceback_html()
    assert seen[0] not in response.content.decode() + caplog.text + report


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.3")
def test_target_authorization_is_rechecked_under_lock():
    _, coord, tester, _, foreign = members()
    client = signed_in(coord)
    old_hash = tester.password
    real_generate = demo.generate_password

    def change_workspace():
        User.objects.filter(pk=tester.pk).update(workspace=foreign.workspace)
        return real_generate()

    with mock.patch.object(demo, "generate_password", change_workspace):
        response = client.post(reset_url(tester))
    assert response.status_code == 404
    tester.refresh_from_db()
    assert tester.password == old_hash


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-5.2", "ACC-5.7")
def test_concurrent_resets_serialize_and_last_committed_password_wins():
    _, coord, tester, _, _ = members()
    clients = [signed_in(coord) for _ in range(3)]
    barrier, rendered = threading.Barrier(3), []

    def record_render(*args, **kwargs):
        page = render_to_string(*args, **kwargs)
        rendered.append(args[1]["credential"].password)
        return page

    def post(client):
        try:
            barrier.wait(10)
            return client.post(reset_url(tester))
        finally:
            connection.close()

    with (
        mock.patch.object(views, "render_to_string", record_render),
        ThreadPoolExecutor(max_workers=3) as pool,
    ):
        responses = list(pool.map(post, clients))
    assert [response.status_code for response in responses] == [200] * 3
    assert len(set(rendered)) == 3
    assert {row(response)[2] for response in responses} == set(rendered)
    tester.refresh_from_db()
    assert [tester.check_password(password) for password in rendered] == [
        False,
        False,
        True,
    ]


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-5.6")
def test_account_lock_wait_is_bounded_and_preserves_password():
    _, coord, tester, _, _ = members()
    client = signed_in(coord)
    locked, release = threading.Event(), threading.Event()

    def hold():
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(pk=tester.pk)
                locked.set()
                assert release.wait(10)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        holder = pool.submit(hold)
        try:
            assert locked.wait(10)
            with mock.patch.dict(limits.TIMEOUTS, {"lock_timeout": "100ms"}):
                response = client.post(reset_url(tester))
        finally:
            release.set()
            holder.result(timeout=10)
    assert response.status_code == 503
    tester.refresh_from_db()
    assert tester.check_password(OLD)


@pytest.mark.django_db
@pytest.mark.ac("ACC-5.6")
def test_statement_timeout_rolls_back_reset(reset_errors):
    _, coord, tester, _, _ = members()
    client = signed_in(coord)

    def slow_render(*args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(0.2)")
        raise AssertionError("statement timeout did not fire")

    with (
        mock.patch.dict(limits.TIMEOUTS, {"statement_timeout": "50ms"}),
        mock.patch.object(views, "render_to_string", slow_render),
    ):
        response = client.post(reset_url(tester))
    assert response.status_code == 503
    assert isinstance(reset_errors[0][1], DatabaseError)
    assert "statement timeout" in str(reset_errors[0][1])
    tester.refresh_from_db()
    assert tester.check_password(OLD)
