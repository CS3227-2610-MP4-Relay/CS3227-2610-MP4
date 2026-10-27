import re
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import Client
from django.urls import include, path

from accounts.models import Workspace

PASSWORD = "Synthetic16Chars"
FAILURE = "Username or password is incorrect."
DENIED = "You do not have access to this page."
SIGNED_OUT = "You have signed out."
COOKIE = django_settings.SESSION_COOKIE_NAME
SIGNED_IN_AT = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def touch(request):
    """Write to the session, as any later session-changing request would."""
    request.session["touched"] = request.session.get("touched", 0) + 1
    return HttpResponse("touched")


urlpatterns = [path("touch/", touch), path("", include("relay.urls"))]


@pytest.fixture
def workspace(db):
    return Workspace.objects.create(name="Demo workspace sign0001")


@pytest.fixture
def coordinator(workspace):
    return get_user_model().objects.create_user(
        "coord-sign0001", PASSWORD, workspace=workspace, role="coordinator"
    )


@pytest.fixture
def tester(workspace):
    return get_user_model().objects.create_user(
        "tester1-sign0001", PASSWORD, workspace=workspace, role="tester"
    )


def sign_in(client, username, password=PASSWORD, **extra):
    return client.post(
        "/sign-in/", {"username": username, "password": password}, **extra
    )


def session_key(client):
    return client.cookies[COOKIE].value if COOKIE in client.cookies else None


def signed_in_user_id(client):
    session = Session.objects.filter(session_key=session_key(client)).first()
    return session.get_decoded().get("_auth_user_id") if session else None


def without_csrf_token(response):
    html = response.content.decode()
    return re.sub(r'name="csrfmiddlewaretoken" value="[^"]*"', "", html)


@pytest.mark.ac("ACC-1.1")
@pytest.mark.parametrize(
    ("role", "home", "title"),
    [
        ("coordinator", "/coordinator/", "Coordinator home"),
        ("tester", "/tester/", "Tester home"),
    ],
)
def test_sign_in_opens_own_role_home(client, coordinator, tester, role, home, title):
    user = coordinator if role == "coordinator" else tester
    response = sign_in(client, user.username)
    assert response.status_code == 302
    assert response["Location"] == home
    page = client.get(home)
    assert page.status_code == 200
    html = page.content.decode()
    assert f"<title>{title}</title>" in html
    assert user.username in html
    assert "Demo workspace sign0001" in html


@pytest.mark.ac("ACC-1.1")
@pytest.mark.parametrize(
    "target", ["/tester/", "https://attacker.invalid/", "//attacker.invalid/"]
)
def test_sign_in_ignores_redirect_targets(client, coordinator, target):
    response = client.post(
        f"/sign-in/?next={target}",
        {"username": coordinator.username, "password": PASSWORD, "next": target},
        HTTP_REFERER=target,
    )
    assert response.status_code == 302
    assert response["Location"] == "/coordinator/"


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "coord-sign0001", "password": "Wrong16Characters"},
        {"username": "unknown-sign0001", "password": PASSWORD},
        {"username": "", "password": PASSWORD},
        {"username": "coord-sign0001", "password": ""},
        {"username": "", "password": ""},
        {},
        {"username": "coord-sign0001\x00", "password": PASSWORD},
        {"username": "coord-sign0001", "password": PASSWORD + "\x00"},
        {"username": "c" * 151, "password": PASSWORD},
    ],
)
def test_failed_sign_in_keeps_visitor_signed_out(client, coordinator, credentials):
    response = client.post("/sign-in/", credentials)
    assert response.status_code == 200
    assert FAILURE in response.content.decode()
    assert signed_in_user_id(client) is None
    assert client.get("/coordinator/")["Location"] == "/sign-in/"


@pytest.mark.ac("ACC-1.2")
def test_failure_does_not_reveal_which_field_was_wrong(client, coordinator):
    wrong_password = sign_in(client, coordinator.username, "Wrong16Characters")
    unknown_user = sign_in(client, "unknown-sign0001")
    assert FAILURE in wrong_password.content.decode()
    assert without_csrf_token(wrong_password) == without_csrf_token(unknown_user)
    assert coordinator.username not in wrong_password.content.decode()


@pytest.mark.ac("ACC-1.2")
def test_blank_fields_reach_the_server(client, db):
    html = client.get("/sign-in/").content.decode()
    inputs = [tag for tag in re.findall(r"<input [^>]*>", html) if "hidden" not in tag]
    assert len(inputs) == 2
    assert not [tag for tag in inputs if "required" in tag]


@pytest.mark.ac("ACC-1.2")
def test_sign_in_password_is_sensitive_and_never_cached(client, coordinator):
    page = client.get("/sign-in/")
    failed = sign_in(client, coordinator.username, "Wrong16Characters")
    for response in (page, failed):
        assert "no-store" in response["Cache-Control"]
        assert "private" in response["Cache-Control"]
    assert failed.wsgi_request.sensitive_post_parameters == ("password",)


@pytest.mark.ac("ACC-1.2")
def test_failed_sign_in_leaves_existing_session_unchanged(client, coordinator, tester):
    sign_in(client, tester.username)
    key = session_key(client)
    response = sign_in(client, coordinator.username, "Wrong16Characters")
    assert FAILURE in response.content.decode()
    assert session_key(client) == key
    assert signed_in_user_id(client) == str(tester.pk)
    assert client.get("/tester/").status_code == 200


@pytest.mark.ac("ACC-1.3")
@pytest.mark.parametrize("home", ["/coordinator/", "/tester/"])
def test_signed_out_visitor_is_sent_to_sign_in(client, db, home):
    response = client.get(home)
    assert response.status_code == 302
    assert response["Location"] == "/sign-in/"


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize(
    ("role", "own", "other"),
    [
        ("coordinator", "/coordinator/", "/tester/"),
        ("tester", "/tester/", "/coordinator/"),
    ],
)
def test_other_role_home_is_forbidden(client, coordinator, tester, role, own, other):
    user = coordinator if role == "coordinator" else tester
    sign_in(client, user.username)
    response = client.get(other)
    assert response.status_code == 403
    html = response.content.decode()
    assert DENIED in html
    for private in ("Demo workspace sign0001", coordinator.username, tester.username):
        assert private not in html
    assert client.get(own).status_code == 200


@pytest.mark.ac("ACC-1.5")
def test_sign_out_ends_server_session(client, coordinator):
    sign_in(client, coordinator.username)
    old_key = session_key(client)
    response = client.post("/sign-out/")
    assert response.status_code == 302
    assert response["Location"] == "/sign-in/"
    assert not Session.objects.filter(session_key=old_key).exists()
    assert SIGNED_OUT in client.get("/sign-in/").content.decode()
    assert SIGNED_OUT not in client.get("/sign-in/").content.decode()
    assert client.get("/coordinator/")["Location"] == "/sign-in/"
    client.cookies[COOKIE] = old_key
    assert client.get("/coordinator/")["Location"] == "/sign-in/"


@pytest.mark.ac("ACC-1.5")
@pytest.mark.parametrize("method", ["get", "head", "put", "delete"])
def test_sign_out_needs_post(client, coordinator, method):
    sign_in(client, coordinator.username)
    response = getattr(client, method)("/sign-out/")
    assert response.status_code == 405
    assert client.get("/coordinator/").status_code == 200


@pytest.mark.ac("ACC-1.6")
@pytest.mark.parametrize(
    ("elapsed", "status"),
    [
        (timedelta(hours=8) - timedelta(seconds=1), 200),
        (timedelta(hours=8), 302),
        (timedelta(hours=8, seconds=1), 302),
    ],
)
def test_session_ends_eight_hours_after_sign_in(
    client, coordinator, settings, elapsed, status
):
    settings.ROOT_URLCONF = __name__
    with mock.patch("django.utils.timezone.now", return_value=SIGNED_IN_AT):
        sign_in(client, coordinator.username)
    later = SIGNED_IN_AT + timedelta(hours=4)
    with mock.patch("django.utils.timezone.now", return_value=later):
        assert client.get("/touch/").status_code == 200
        assert client.get("/coordinator/").status_code == 200
    moment = SIGNED_IN_AT + elapsed
    with mock.patch("django.utils.timezone.now", return_value=moment):
        response = client.get("/coordinator/")
    assert response.status_code == status
    if status == 302:
        assert response["Location"] == "/sign-in/"


@pytest.mark.ac("ACC-1.7")
def test_sign_in_replaces_signed_out_session_identifier(client, coordinator):
    old_key = client.session.session_key
    assert Session.objects.filter(session_key=old_key).exists()
    sign_in(client, coordinator.username)
    assert session_key(client) not in (None, old_key)
    assert not Session.objects.filter(session_key=old_key).exists()


@pytest.mark.ac("ACC-1.7")
@pytest.mark.parametrize("first", ["tester", "coordinator"])
def test_sign_in_replaces_signed_in_session_identifier(
    client, coordinator, tester, first
):
    first_user = tester if first == "tester" else coordinator
    sign_in(client, first_user.username)
    old_key = session_key(client)
    sign_in(client, coordinator.username)
    assert session_key(client) != old_key
    assert signed_in_user_id(client) == str(coordinator.pk)
    stale = Client()
    stale.cookies[COOKIE] = old_key
    assert stale.get(f"/{first}/")["Location"] == "/sign-in/"


def csrf_client():
    client = Client(enforce_csrf_checks=True)
    client.get("/sign-in/")
    return client, client.cookies[django_settings.CSRF_COOKIE_NAME].value


def csrf_data(valid, token):
    if token is None:
        return {}
    return {"csrfmiddlewaretoken": valid if token == "valid" else token}


def origin_header(origin):
    return {"HTTP_ORIGIN": origin} if origin else {}


REFUSED_CSRF = [
    (None, None),
    ("x" * 32, None),
    ("valid", "https://attacker.invalid"),
    ("valid", "null"),
]


@pytest.mark.ac("ACC-1.8")
def test_sign_in_with_valid_token_and_origin_succeeds(coordinator):
    client, valid = csrf_client()
    response = client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, "valid"),
        HTTP_ORIGIN="http://testserver",
    )
    assert response["Location"] == "/coordinator/"


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("token", "origin"), REFUSED_CSRF)
def test_sign_in_without_valid_csrf_or_origin_is_refused(coordinator, token, origin):
    client, valid = csrf_client()
    response = client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, token),
        **origin_header(origin),
    )
    assert response.status_code == 403
    assert DENIED in response.content.decode()
    assert signed_in_user_id(client) is None
    coordinator.refresh_from_db()
    assert coordinator.last_login is None


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("token", "origin"), REFUSED_CSRF)
def test_sign_out_without_valid_csrf_or_origin_is_refused(coordinator, token, origin):
    client, valid = csrf_client()
    client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, "valid"),
    )
    key = session_key(client)
    valid = client.cookies[django_settings.CSRF_COOKIE_NAME].value
    response = client.post(
        "/sign-out/", csrf_data(valid, token), **origin_header(origin)
    )
    assert response.status_code == 403
    assert DENIED in response.content.decode()
    assert session_key(client) == key
    assert client.get("/coordinator/").status_code == 200


REFUSED_HTTPS = [
    {},
    {"HTTP_REFERER": "https://attacker.invalid/sign-in/"},
    {"HTTP_ORIGIN": "http://testserver"},
]


@pytest.mark.ac("ACC-1.8")
def test_https_sign_in_with_same_origin_succeeds(coordinator):
    client, valid = csrf_client()
    response = client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, "valid"),
        secure=True,
        HTTP_ORIGIN="https://testserver",
    )
    assert response["Location"] == "/coordinator/"


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("headers", REFUSED_HTTPS)
def test_https_sign_in_without_matching_origin_is_refused(coordinator, headers):
    client, valid = csrf_client()
    response = client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, "valid"),
        secure=True,
        **headers,
    )
    assert response.status_code == 403
    assert DENIED in response.content.decode()
    assert signed_in_user_id(client) is None
    coordinator.refresh_from_db()
    assert coordinator.last_login is None


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("headers", REFUSED_HTTPS)
def test_https_sign_out_without_matching_origin_is_refused(coordinator, headers):
    client, valid = csrf_client()
    client.post(
        "/sign-in/",
        {"username": coordinator.username, "password": PASSWORD}
        | csrf_data(valid, "valid"),
    )
    key = session_key(client)
    valid = client.cookies[django_settings.CSRF_COOKIE_NAME].value
    response = client.post(
        "/sign-out/", csrf_data(valid, "valid"), secure=True, **headers
    )
    assert response.status_code == 403
    assert DENIED in response.content.decode()
    assert session_key(client) == key
    assert client.get("/coordinator/").status_code == 200


def test_sign_in_session_cookie_flags(client, coordinator):
    """Check the cookie rules in the technical spec's accounts routes."""
    response = sign_in(client, coordinator.username)
    cookie = response.cookies[COOKIE]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["secure"] is True
    assert 0 < int(cookie["max-age"]) <= 8 * 60 * 60


@pytest.mark.parametrize("role", ["coordinator", "tester"])
def test_role_homes_are_never_cached(client, coordinator, tester, role):
    """Check the caching rule in the technical spec's accounts routes."""
    user = coordinator if role == "coordinator" else tester
    sign_in(client, user.username)
    cache_control = client.get(f"/{role}/")["Cache-Control"]
    assert "no-store" in cache_control
    assert "private" in cache_control
