"""Coordinator-created tester boundaries, isolation and transient credentials."""

import logging
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.template.loader import render_to_string
from django.test import Client
from django.views.debug import ExceptionReporter

from accounts import demo, limits, views
from accounts.models import User, Workspace
from relay.tests.test_access_matrix import every_row

URL = "/coordinator/testers/add/"
LIMIT = "This workspace already has 10 Beta Testers."
SAVE = "Save this password now. It will not be shown again."
ROW = re.compile(r"<tr><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td></tr>")


def seed(count=2, label="own"):
    """Create a workspace with a coordinator and synthetic testers."""
    workspace = Workspace.objects.create(name=f"Workspace {label}")
    coord = User.objects.create_user(
        f"coord-{label}", "SyntheticInitial16", workspace=workspace, role="coordinator"
    )
    User.objects.bulk_create(
        [
            User(username=f"tester-{label}-{i}", workspace=workspace, role="tester")
            for i in range(count)
        ]
    )
    return workspace, coord


def signed_in(user, *, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def row(response):
    rows = ROW.findall(response.content.decode())
    assert len(rows) == 1
    return rows[0]


def uncached(response):
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


@pytest.fixture
def caught_errors():
    """Inspect redaction without enabling production traceback logging."""
    errors = []
    real_error = views.logger.error

    def record(*args, **kwargs):
        errors.append(sys.exc_info())
        return real_error(*args, **kwargs)

    with mock.patch.object(views.logger, "error", record):
        yield errors


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.1", "ACC-4.4", "ACC-4.6", "ACC-4.8")
def test_create_ignores_identity_fields_and_shows_working_credentials_once(caplog):
    workspace, coord = seed()
    other, foreign = seed(label="foreign")
    client = signed_in(coord)
    session_key = client.session.session_key
    before = every_row()
    caplog.set_level(logging.DEBUG)
    home = client.get("/coordinator/")
    assert b">Add Beta Tester</button>" in home.content
    response = client.post(
        URL + f"?workspace={other.pk}&next=https://attacker.invalid",
        {
            "workspace": other.pk,
            "workspace_id": other.pk,
            "role": "coordinator",
            "username": foreign.username,
            "password": "AttackerChosen16",
            "user_id": foreign.pk,
            "next": "https://attacker.invalid",
        },
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "<title>Beta Tester added</title>" in html
    assert "<h1>Beta Tester added</h1>" in html
    assert SAVE in html and 'href="/coordinator/"' in html
    role, username, password = row(response)
    assert role == "Beta Tester"
    assert re.fullmatch(r"tester-[a-z0-9]{8}", username)
    assert re.fullmatch(r"[a-zA-Z0-9]{16}", password)
    made = User.objects.get(username=username)
    assert made.role == "tester" and made.workspace_id == workspace.pk
    assert made.check_password(password)
    after = every_row()
    after["User"] = [account for account in after["User"] if account["id"] != made.pk]
    assert before == after
    assert client.session.session_key == session_key
    assert client.session["_auth_user_id"] == str(coord.pk)
    assert other.name not in html
    uncached(response)
    later = client.get("/coordinator/")
    assert password not in later.content.decode()
    assert password not in str(dict(client.session))
    assert password not in str(client.cookies) + str(response.cookies)
    assert password not in caplog.text + str(every_row())
    tester = Client()
    result = tester.post("/sign-in/", {"username": username, "password": password})
    assert result.status_code == 302 and result["Location"] == "/tester/"
    assert workspace.name in tester.get("/tester/").content.decode()
    repeated = client.post(URL)
    assert repeated.status_code == 200
    assert row(repeated)[1:] != (username, password)
    assert workspace.accounts.filter(role="tester").count() == 4


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.2")
@pytest.mark.parametrize("count", [8, 9, 10, 11])
def test_capacity_counts_only_own_testers_and_refuses_before_generation(count):
    workspace, coord = seed(count)
    seed(10, "foreign")
    client = signed_in(coord)
    if count < 10:
        response = client.post(URL)
        assert response.status_code == 200
        assert workspace.accounts.filter(role="tester").count() == count + 1
    else:
        with mock.patch.object(
            demo, "_random", side_effect=AssertionError("generated")
        ):
            response = client.post(URL)
        assert response.status_code == 409
        assert LIMIT in response.content.decode()
        assert b"<title>Tester limit reached</title>" in response.content
        assert workspace.accounts.filter(role="tester").count() == count
    uncached(response)


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.4", "ACC-4.5", "ACC-4.6")
@pytest.mark.parametrize("caller", ["anonymous", "tester", "coordinator"])
def test_roles_methods_and_csrf_deny_without_writes(caller):
    workspace, coord = seed()
    client = Client(enforce_csrf_checks=True)
    if caller != "anonymous":
        user = (
            coord
            if caller == "coordinator"
            else workspace.accounts.get(username="tester-own-0")
        )
        client.force_login(user)
    client.get("/")
    # Signed-in / redirects before rendering a CSRF token; home renders one.
    if caller == "coordinator":
        client.get("/coordinator/")
    elif caller == "tester":
        client.get("/tester/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    before = every_row()
    for method in ("get", "head", "put", "delete", "options"):
        response = getattr(client, method)(URL, HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 405
        assert response["Allow"] == "POST"
        uncached(response)
    for headers in (
        {},
        {"HTTP_X_CSRFTOKEN": "x" * 32},
        {"HTTP_X_CSRFTOKEN": token, "HTTP_ORIGIN": "https://attacker.invalid"},
    ):
        response = client.post(URL, **headers)
        assert response.status_code == 403
    assert every_row() == before
    if caller != "coordinator":
        response = client.post(URL, HTTP_X_CSRFTOKEN=token)
        assert response.status_code == (302 if caller == "anonymous" else 403)
        if caller == "anonymous":
            assert response["Location"] == "/sign-in/"
            uncached(response)
        assert workspace.name not in response.content.decode()
        assert every_row() == before
    else:
        assert (
            client.post(
                URL, HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://testserver"
            ).status_code
            == 200
        )


def fail_after_render(*args, **kwargs):
    """Fail after credential text exists inside a nested rendering frame."""
    page = render_to_string(*args, **kwargs)
    assert SAVE in page
    raise RuntimeError("synthetic rendering failure")


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.6", "ACC-4.7")
@pytest.mark.parametrize(
    "failure", ["read", "write", "render", "hash", "password in exception"]
)
def test_failures_roll_back_and_redact_error_reports(failure, caplog, caught_errors):
    _, coord = seed()
    client = signed_in(coord)
    before = every_row()
    synthetic_password = "P" * 16
    faults = {
        "read": ("accounts.testers.tester_count", DatabaseError("synthetic read")),
        "write": (
            "accounts.models.User.objects.create",
            DatabaseError("synthetic write"),
        ),
        "render": ("accounts.views.render_to_string", fail_after_render),
        "hash": (
            "accounts.demo.make_password",
            RuntimeError("synthetic hashing failure"),
        ),
        "password in exception": (
            "accounts.views.render_to_string",
            RuntimeError(synthetic_password),
        ),
    }
    target, failure_action = faults[failure]
    with (
        mock.patch.object(demo, "_random", return_value=synthetic_password),
        mock.patch(target, side_effect=failure_action),
    ):
        response = client.post(URL)
    assert response.status_code == 503
    uncached(response)
    assert every_row() == before
    records = [
        r for r in caplog.records if r.getMessage() == "Beta Tester creation failed."
    ]
    assert len(records) == 1 and records[0].exc_info is None
    assert synthetic_password not in response.content.decode() + caplog.text
    if failure != "password in exception":
        report = ExceptionReporter(None, *caught_errors[0]).get_traceback_html()
        assert synthetic_password not in report


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.7")
@pytest.mark.parametrize("taken_draws", [2, 3])
def test_username_collisions_are_bounded_and_do_not_change_existing_accounts(
    taken_draws,
):
    workspace, coord = seed()
    User.objects.create(username="tester-taken001", role="tester", workspace=workspace)
    client = signed_in(coord)
    before = every_row()
    with mock.patch.object(
        demo, "draw_suffix", side_effect=["taken001"] * taken_draws + ["fresh001"]
    ) as draw:
        response = client.post(URL)
    assert draw.call_count == 3
    assert response.status_code == (200 if taken_draws == 2 else 503)
    if taken_draws == 3:
        assert every_row() == before
    else:
        assert row(response)[1] == "tester-fresh001"


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-4.6", "ACC-4.7")
def test_hashing_precedes_transaction_and_commit_failure_rolls_back(
    caplog, caught_errors
):
    _, coord = seed()
    client = signed_in(coord)
    before = every_row()
    real_hash = demo.make_password
    seen = []

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
        response = client.post(URL)
    assert response.status_code == 503 and len(seen) == 1
    assert every_row() == before
    record = next(
        r for r in caplog.records if r.getMessage() == "Beta Tester creation failed."
    )
    assert record.exc_info is None
    report = ExceptionReporter(None, *caught_errors[0]).get_traceback_html()
    assert seen[0] not in response.content.decode() + caplog.text + report


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-4.3")
def test_concurrent_posts_fill_only_the_last_place():
    workspace, coord = seed(9)
    clients = [signed_in(coord) for _ in range(5)]
    barrier = threading.Barrier(5)
    real_create = User.objects.create

    def slow_create(**kwargs):
        time.sleep(0.05)
        return real_create(**kwargs)

    def post(client):
        try:
            barrier.wait(10)
            return client.post(URL)
        finally:
            connection.close()

    with (
        mock.patch.object(User.objects, "create", slow_create),
        ThreadPoolExecutor(max_workers=5) as pool,
    ):
        responses = list(pool.map(post, clients))
    assert sorted(response.status_code for response in responses) == [
        200,
        409,
        409,
        409,
        409,
    ]
    assert workspace.accounts.filter(role="tester").count() == 10


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-4.7")
def test_workspace_lock_wait_is_bounded():
    workspace, coord = seed()
    client = signed_in(coord)
    locked, release = threading.Event(), threading.Event()

    def hold():
        try:
            with transaction.atomic():
                Workspace.objects.select_for_update().get(pk=workspace.pk)
                locked.set()
                assert release.wait(10)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        holder = pool.submit(hold)
        try:
            assert locked.wait(10)
            with mock.patch.dict(limits.TIMEOUTS, {"lock_timeout": "100ms"}):
                response = client.post(URL)
        finally:
            release.set()
            holder.result(timeout=10)
    assert response.status_code == 503
    assert workspace.accounts.filter(role="tester").count() == 2


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.7")
def test_session_loading_storage_failure_returns_503():
    _, coord = seed()
    client = signed_in(coord)
    with mock.patch(
        "django.contrib.auth.get_user",
        side_effect=DatabaseError("synthetic session read"),
    ):
        response = client.post(URL)
    assert response.status_code == 503
    uncached(response)


@pytest.mark.django_db
@pytest.mark.ac("ACC-4.7")
def test_statement_timeout_rolls_back_the_new_account(caught_errors):
    workspace, coord = seed()
    client = signed_in(coord)

    def slow_render(*args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_setting('idle_in_transaction_session_timeout')"
            )
            assert cursor.fetchone() == ("10s",)
            cursor.execute("SELECT pg_sleep(0.2)")
        raise AssertionError("statement timeout did not fire")

    with (
        mock.patch.dict(limits.TIMEOUTS, {"statement_timeout": "50ms"}),
        mock.patch.object(views, "render_to_string", slow_render),
    ):
        response = client.post(URL)
    assert response.status_code == 503
    assert isinstance(caught_errors[0][1], DatabaseError)
    assert "statement timeout" in str(caught_errors[0][1])
    assert workspace.accounts.filter(role="tester").count() == 2
