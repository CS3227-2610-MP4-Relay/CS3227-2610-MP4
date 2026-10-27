import logging
import re
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.db import DatabaseError, IntegrityError, connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.test import Client
from django.urls import include, path
from django.views.debug import ExceptionReporter

from accounts import demo
from accounts.models import User, Workspace
from accounts.workspaces import workspace_records
from rounds import services as round_services
from rounds.models import Case, CaseCriterion, Criterion, Round

SAVE = "Save these passwords now. They will not be shown again."
UNAVAILABLE = "Relay is temporarily unavailable. Try again later."
DENIED = "You do not have access to this page."
NOT_FOUND = "Page not found."
ROW = re.compile(r"<tr><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td></tr>")
HOMES = {"coordinator": "/coordinator/", "tester": "/tester/"}


def record(request, pk):
    """A record route reading through the shared workspace helper (ACC-2.4)."""
    account = get_object_or_404(workspace_records(request.user, User), pk=pk)
    return HttpResponse(account.username)


urlpatterns = [path("record/<int:pk>/", record), path("", include("relay.urls"))]


def counts():
    """Rows of every model demo creation writes, its sample round included."""
    return tuple(
        model.objects.count()
        for model in (Workspace, User, Round, Criterion, Case, CaseCriterion)
    )


NOTHING = (0, 0, 0, 0, 0, 0)
# One workspace, 3 accounts and the RND-7 sample round: 3 criteria, 4 cases and
# 5 case-criterion links.
ONE_WORKSPACE = (1, 3, 1, 3, 4, 5)


def credentials(response):
    return ROW.findall(response.content.decode())


def created(client=None):
    response = (client or Client()).post("/demo/")
    assert response.status_code == 200
    return response


def csrf_client():
    client = Client(enforce_csrf_checks=True)
    client.get("/")
    return client, client.cookies[django_settings.CSRF_COOKIE_NAME].value


def capture_passwords():
    seen = []
    real = demo.generate_passwords

    def generate():
        passwords = real()
        seen.extend(password for password, _ in passwords)
        return passwords

    return seen, mock.patch.object(demo, "generate_passwords", generate)


@pytest.fixture
def account(db):
    workspace = Workspace.objects.create(name="Demo workspace view0001")

    def make(role):
        return User.objects.create_user(
            f"{role}-view0001", "Synthetic16Chars", workspace=workspace, role=role
        )

    return make


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.1")
def test_creation_shows_credentials_once_and_stays_signed_out():
    client = Client()
    response = created(client)
    html = response.content.decode()
    name = Workspace.objects.get().name
    for text in (
        "<title>Your demo workspace</title>",
        "<h1>Your demo workspace</h1>",
        f"<p>Workspace: {name}</p>",
        "<tr><th>Role</th><th>Username</th><th>Password</th></tr>",
        f"<p>{SAVE}</p>",
        '<a href="/sign-in/">Sign in</a>',
    ):
        assert text in html
    assert html.index("</table>") < html.index(SAVE)
    rows = credentials(response)
    assert [role for role, _, _ in rows] == [
        "Test Coordinator",
        "Beta Tester",
        "Beta Tester",
    ]
    assert django_settings.SESSION_COOKIE_NAME not in response.cookies
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.2")
def test_each_listed_account_signs_in_to_its_role_home():
    response = created()
    name = Workspace.objects.get().name
    rows = credentials(response)
    assert len(rows) == 3
    for (_, username, password), role in zip(
        rows, ["coordinator", "tester", "tester"], strict=True
    ):
        client = Client()
        signed_in = client.post(
            "/sign-in/", {"username": username, "password": password}
        )
        assert signed_in["Location"] == HOMES[role]
        home = client.get(HOMES[role]).content.decode()
        assert f"Workspace: {name}" in home
        assert f"Username: {username}" in home


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.2", "ACC-2.4")
def test_each_home_shows_only_its_own_workspace():
    first, second = created(), created()
    workspaces = {}
    for response in (first, second):
        rows = credentials(response)
        name = re.search(r"<p>Workspace: ([^<]*)</p>", response.content.decode())
        workspaces[name.group(1)] = rows
    assert len(workspaces) == 2
    for name, rows in workspaces.items():
        (other_name, other_rows) = next(
            item for item in workspaces.items() if item[0] != name
        )
        for (_, username, password), role in zip(
            rows, ["coordinator", "tester", "tester"], strict=True
        ):
            client = Client()
            client.post("/sign-in/", {"username": username, "password": password})
            home = client.get(HOMES[role]).content.decode()
            assert f"Workspace: {name}" in home
            assert other_name not in home
            for _, other_username, other_password in other_rows:
                assert other_username not in home
                assert other_password not in home


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.3")
def test_passwords_are_not_cached_or_shown_again(caplog):
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="django")
    caplog.set_level(logging.DEBUG, logger="django.template")
    client = Client()
    response = created(client)
    assert response["Cache-Control"] == "no-store"
    rows = credentials(response)
    passwords = [password for _, _, password in rows]
    later = [client.get("/"), client.get("/sign-in/")]
    for (_, username, password), home in zip(
        rows, ["/coordinator/", "/tester/", "/tester/"], strict=True
    ):
        user_client = Client()
        user_client.post("/sign-in/", {"username": username, "password": password})
        later += [user_client.get(home), user_client.get("/")]
    for page in later:
        for password in passwords:
            assert password not in page.content.decode()
    for password in passwords:
        assert password not in caplog.text


@pytest.mark.urls(__name__)
@pytest.mark.ac("ACC-2.4")
def test_other_workspace_record_in_url_is_page_not_found(account, client):
    own = account("coordinator")
    other_workspace = Workspace.objects.create(name="Demo workspace view0002")
    other = User.objects.create_user(
        "tester1-view0002", "Synthetic16Chars", workspace=other_workspace, role="tester"
    )
    client.force_login(own)
    assert client.get(f"/record/{own.pk}/").content == own.username.encode()
    foreign = client.get(f"/record/{other.pk}/")
    missing = client.get(f"/record/{other.pk + 1000}/")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.content == missing.content
    assert f"<h1>{NOT_FOUND}</h1>" in foreign.content.decode()
    assert other.username not in foreign.content.decode()


def fail_second_account(real_create):
    calls = []

    def create(**fields):
        calls.append(fields["username"])
        if len(calls) == 2:
            raise DatabaseError("synthetic storage failure")
        return real_create(**fields)

    return create


def fail_third_sample_case(real_add_case):
    calls = []

    def add_case(*args, **kwargs):
        calls.append(args)
        if len(calls) == 3:
            raise DatabaseError("synthetic storage failure")
        return real_add_case(*args, **kwargs)

    return add_case


def fail_rendering(*args, **kwargs):
    raise RuntimeError("synthetic rendering failure")


FAILURES = {
    "account write": lambda: mock.patch.object(
        User.objects, "create", fail_second_account(User.objects.create)
    ),
    "sample case write": lambda: mock.patch.object(
        round_services, "add_case", fail_third_sample_case(round_services.add_case)
    ),
    "rendering": lambda: mock.patch("accounts.views.render_to_string", fail_rendering),
    "taken suffix": lambda: mock.patch.object(
        demo, "draw_suffix", side_effect=["fail0001"] * 3
    ),
}


RAISED = {
    "account write": DatabaseError,
    "sample case write": DatabaseError,
    "rendering": RuntimeError,
    "taken suffix": IntegrityError,
}


def failure_record(caplog):
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "Demo workspace creation failed."
    ]
    assert len(records) == 1
    assert records[0].exc_info
    return records[0].exc_info


def error_report(exc_info):
    """Django's error report, with frame variables, as mailed or shown to admins."""
    return ExceptionReporter(None, *exc_info).get_traceback_html()


def assert_503_with_nothing_left(response, before, passwords, caplog):
    assert response.status_code == 503
    html = response.content.decode()
    assert f"<h1>{UNAVAILABLE}</h1>" in html
    assert "<table" not in html
    assert counts() == before
    assert len(passwords) == 3
    for password in passwords:
        assert password not in html
        assert password not in caplog.text


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.5")
@pytest.mark.parametrize("failure", FAILURES)
def test_failed_creation_leaves_nothing_and_shows_503(failure, caplog):
    if failure == "taken suffix":
        Workspace.objects.create(name="Demo workspace fail0001")
    before = counts()
    seen, spy = capture_passwords()
    client = Client()
    client.raise_request_exception = False
    with spy, FAILURES[failure]() as patched:
        response = client.post("/demo/")
    assert_503_with_nothing_left(response, before, seen, caplog)
    exc_info = failure_record(caplog)
    assert type(exc_info[1]) is RAISED[failure]
    report = error_report(exc_info)
    assert "create_demo" in report
    for password in seen:
        assert password not in report
    if failure == "taken suffix":
        assert patched.call_count == 3


class FailingCredential:
    """A third table row whose password raises while the page renders."""

    role = "Beta Tester"
    username = "tester2-render01"

    @property
    def password(self):
        raise RuntimeError("synthetic failure inside the credentials table")


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.3", "ACC-2.5")
def test_failure_mid_table_keeps_rendered_passwords_out_of_error_reports(caplog):
    seen, spy = capture_passwords()
    real_create = demo.create_demo_workspace

    def create(passwords):
        workspace, credentials = real_create(passwords)
        return workspace, [*credentials[:2], FailingCredential()]

    client = Client()
    client.raise_request_exception = False
    with spy, mock.patch.object(demo, "create_demo_workspace", create):
        response = client.post("/demo/")
    assert_503_with_nothing_left(response, NOTHING, seen, caplog)
    exc_info = failure_record(caplog)
    assert "inside the credentials table" in str(exc_info[1])
    report = error_report(exc_info)
    assert "create_demo" in report
    for password in seen:
        assert password not in report


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-2.5")
def test_failed_commit_leaves_nothing_and_shows_503(caplog):
    seen, spy = capture_passwords()
    client = Client()
    client.raise_request_exception = False
    with (
        spy,
        mock.patch.object(
            connection, "commit", side_effect=DatabaseError("synthetic commit failure")
        ) as commit,
    ):
        response = client.post("/demo/")
    assert commit.called
    assert_503_with_nothing_left(response, NOTHING, seen, caplog)
    exc_info = failure_record(caplog)
    assert type(exc_info[1]) is DatabaseError
    for password in seen:
        assert password not in error_report(exc_info)


@pytest.mark.ac("ACC-2.6", "PLT-1.1")
@pytest.mark.parametrize("role", ["coordinator", "tester"])
def test_signed_in_user_is_sent_home_and_creates_nothing(account, role):
    client, _ = csrf_client()
    client.force_login(account(role))
    valid = client.cookies[django_settings.CSRF_COOKIE_NAME].value
    before = counts()
    for response in (
        client.get("/"),
        client.head("/"),
        client.post("/demo/", {"csrfmiddlewaretoken": valid}),
    ):
        assert response.status_code == 302
        assert response["Location"] == HOMES[role]
    assert counts() == before


REFUSED_CSRF = [
    (None, None),
    ("x" * 32, None),
    ("valid", "https://attacker.invalid"),
    ("valid", "null"),
]


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.7")
def test_creation_with_token_from_start_page_and_own_origin_succeeds():
    client, valid = csrf_client()
    response = client.post(
        "/demo/", {"csrfmiddlewaretoken": valid}, HTTP_ORIGIN="http://testserver"
    )
    assert response.status_code == 200
    assert counts() == ONE_WORKSPACE


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.7")
@pytest.mark.parametrize(("token", "origin"), REFUSED_CSRF)
def test_creation_without_valid_csrf_or_origin_is_refused(token, origin):
    client, valid = csrf_client()
    data = {} if token is None else {"csrfmiddlewaretoken": valid}
    if token not in (None, "valid"):
        data["csrfmiddlewaretoken"] = token
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    response = client.post("/demo/", data, **extra)
    assert response.status_code == 403
    assert DENIED in response.content.decode()
    assert counts() == NOTHING


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.7")
def test_creation_by_get_is_refused():
    response = Client().get("/demo/")
    assert response.status_code == 405
    assert counts() == NOTHING
