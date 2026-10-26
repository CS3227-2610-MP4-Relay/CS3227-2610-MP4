import threading
import time
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.sessions.models import Session
from django.db import DatabaseError, OperationalError, connection, transaction
from django.test import Client, RequestFactory

from accounts import demo, limits
from accounts.models import LimitCounter, Workspace

PASSWORD = "Synthetic16Chars"
WRONG = "Wrong16Characters"
FAILURE = "Username or password is incorrect."
SIGN_IN_LIMITED = "Too many sign-in attempts. Try again later."
DEMO_LIMITED = "Too many demo workspaces have been created recently. Try again later."
UNAVAILABLE = "Relay is temporarily unavailable. Try again later."
ADDRESS = "203.0.113.5"
OTHER = "198.51.100.7"
T0 = datetime(2030, 1, 7, 9, 0, tzinfo=UTC)


@pytest.fixture
def user(db):
    workspace = Workspace.objects.create(name="Demo workspace limit001")
    return get_user_model().objects.create_user(
        "coord-limit001", PASSWORD, workspace=workspace, role="coordinator"
    )


def key(address):
    return limits.client_key(RequestFactory().get("/", REMOTE_ADDR=address))


def stored(limit, address=ADDRESS):
    row_key = limits.TOTAL_KEY if limit is limits.DEMO_TOTAL else key(address)
    return LimitCounter.objects.filter(scope=limit.scope, key=row_key).first()


def count_of(limit, address=ADDRESS):
    row = stored(limit, address)
    return row.count if row else 0


def set_count(limit, count, start=None, address=ADDRESS):
    row_key = limits.TOTAL_KEY if limit is limits.DEMO_TOTAL else key(address)
    LimitCounter.objects.update_or_create(
        scope=limit.scope,
        key=row_key,
        defaults={"count": count, "window_start": start or datetime.now(UTC)},
    )


def at(moment):
    return mock.patch.object(limits.timezone, "now", return_value=moment)


def sign_in(client=None, username="coord-limit001", password=WRONG, **extra):
    extra.setdefault("REMOTE_ADDR", ADDRESS)
    return (client or Client()).post(
        "/sign-in/", {"username": username, "password": password}, **extra
    )


def create(client=None, **extra):
    extra.setdefault("REMOTE_ADDR", ADDRESS)
    return (client or Client()).post("/demo/", **extra)


def snapshot():
    rows = LimitCounter.objects.order_by("scope", "key")
    return list(rows.values_list("scope", "key", "window_start", "count"))


def in_transaction_then(action):
    """Run `action` whenever a limit is checked inside a limited transaction."""
    real = limits.reached

    def reached(counter, limit):
        if connection.in_atomic_block:
            action()
        return real(counter, limit)

    return mock.patch.object(limits, "reached", side_effect=reached)


def signed_in(client):
    return "_auth_user_id" in client.session


def assert_failure(response):
    assert response.status_code == 200
    assert FAILURE in response.content.decode()


def assert_sign_in_limited(response):
    assert response.status_code == 429
    html = response.content.decode()
    assert SIGN_IN_LIMITED in html
    assert FAILURE not in html
    assert "<title>Sign in</title>" in html and "<h1>Sign in</h1>" in html
    assert 'name="password"' in html


def assert_demo_limited(response):
    assert response.status_code == 429
    assert f"<h1>{DEMO_LIMITED}</h1>" in response.content.decode()


def assert_unavailable(response):
    assert response.status_code == 503
    assert UNAVAILABLE in response.content.decode()


# ACC-3.1


@pytest.mark.ac("ACC-3.1", "ACC-3.5")
def test_30th_failure_is_normal_and_then_even_a_correct_password_is_refused(user):
    for attempt in range(30):
        assert_failure(sign_in(username=f"varied-{attempt}"))
    client = Client()
    assert_sign_in_limited(sign_in(client, password=PASSWORD))
    assert not signed_in(client)
    assert_sign_in_limited(sign_in())
    assert stored(limits.SIGN_IN).count == 30


@pytest.mark.ac("ACC-3.1")
def test_29_failures_leave_one_normal_failure(user):
    set_count(limits.SIGN_IN, 29)
    assert_failure(sign_in())
    assert_sign_in_limited(sign_in())


# ACC-3.2


@pytest.mark.ac("ACC-3.2")
def test_sign_in_refusal_lasts_until_its_15_minute_window_ends(user):
    set_count(limits.SIGN_IN, 30, T0)
    with at(T0 + timedelta(minutes=15, microseconds=-1)):
        assert_sign_in_limited(sign_in(password=PASSWORD))
    with at(T0 + timedelta(minutes=15)):
        response = sign_in(password=PASSWORD)
    assert response.status_code == 302


@pytest.mark.ac("ACC-3.2")
@pytest.mark.parametrize(
    ("limit", "count", "window"),
    [
        (limits.DEMO, 10, timedelta(hours=1)),
        (limits.DEMO_TOTAL, 200, timedelta(hours=24)),
    ],
)
def test_creation_refusal_lasts_until_its_window_ends(db, limit, count, window):
    set_count(limit, count, T0)
    with at(T0 + window - timedelta(microseconds=1)):
        assert_demo_limited(create())
    with at(T0 + window):
        assert create().status_code == 200


# ACC-3.3


@pytest.mark.ac("ACC-3.3")
def test_blank_fields_count_as_failures(user):
    for _ in range(30):
        assert_failure(sign_in(username="", password=""))
    assert_sign_in_limited(sign_in(password=PASSWORD))


@pytest.mark.ac("ACC-3.3")
def test_success_neither_counts_nor_resets(user):
    set_count(limits.SIGN_IN, 29)
    assert sign_in(password=PASSWORD).status_code == 302
    assert stored(limits.SIGN_IN).count == 29
    assert_failure(sign_in())
    assert_sign_in_limited(sign_in())


@pytest.mark.ac("ACC-3.3")
def test_refused_sign_in_does_not_extend_its_window(user):
    set_count(limits.SIGN_IN, 30, T0)
    with at(T0 + timedelta(minutes=14)):
        assert_sign_in_limited(sign_in())
    row = stored(limits.SIGN_IN)
    assert (row.window_start, row.count) == (T0, 30)
    with at(T0 + timedelta(minutes=15)):
        assert_failure(sign_in())
    row = stored(limits.SIGN_IN)
    assert (row.window_start, row.count) == (T0 + timedelta(minutes=15), 1)


@pytest.mark.ac("ACC-3.3")
def test_refused_creation_counts_nothing(db):
    set_count(limits.DEMO, 10, T0)
    set_count(limits.DEMO_TOTAL, 5, T0)
    with at(T0 + timedelta(minutes=1)):
        assert_demo_limited(create())
    assert stored(limits.DEMO).count == 10
    assert stored(limits.DEMO_TOTAL).count == 5


@pytest.mark.ac("ACC-3.3")
def test_csrf_refusals_count_nothing(user):
    client = Client(enforce_csrf_checks=True)
    assert sign_in(client).status_code == 403
    assert create(client).status_code == 403
    assert stored(limits.SIGN_IN) is None
    assert stored(limits.DEMO) is None


@pytest.mark.ac("ACC-3.3", "ACC-3.7")
def test_unavailable_sign_in_counts_nothing(user):
    with mock.patch(
        "accounts.views.authenticate", side_effect=OperationalError("synthetic")
    ):
        assert_unavailable(sign_in())
    assert stored(limits.SIGN_IN) is None


@pytest.mark.ac("ACC-3.3")
def test_failed_creation_counts_nothing(db):
    with mock.patch.object(
        demo, "create_demo_workspace", side_effect=OperationalError("synthetic")
    ):
        assert_unavailable(create())
    assert stored(limits.DEMO) is None
    assert count_of(limits.DEMO_TOTAL) == 0


@pytest.mark.ac("ACC-3.3")
def test_viewing_the_sign_in_page_is_never_limited(user):
    set_count(limits.SIGN_IN, 30)
    response = Client().get("/sign-in/", REMOTE_ADDR=ADDRESS)
    assert response.status_code == 200
    assert SIGN_IN_LIMITED not in response.content.decode()


@pytest.mark.ac("ACC-3.3")
def test_signed_in_redirect_from_creation_counts_nothing(user):
    client = Client()
    client.force_login(user)
    assert create(client).status_code == 302
    assert stored(limits.DEMO) is None


# ACC-3.4


@pytest.mark.ac("ACC-3.4")
def test_11th_creation_from_one_address_is_refused(db):
    for _ in range(10):
        assert create().status_code == 200
    workspaces = Workspace.objects.count()
    assert_demo_limited(create())
    assert Workspace.objects.count() == workspaces == 10
    assert stored(limits.DEMO).count == 10
    assert stored(limits.DEMO_TOTAL).count == 10


@pytest.mark.ac("ACC-3.4")
def test_201st_creation_from_all_addresses_is_refused(db):
    set_count(limits.DEMO_TOTAL, 199)
    assert create(REMOTE_ADDR="192.0.2.1").status_code == 200
    assert stored(limits.DEMO_TOTAL).count == 200
    assert_demo_limited(create(REMOTE_ADDR="192.0.2.2"))
    assert Workspace.objects.count() == 1


@pytest.mark.ac("ACC-3.4")
def test_precheck_refuses_before_hashing_any_password(db):
    set_count(limits.DEMO, 10)
    with mock.patch.object(demo, "generate_passwords") as generate:
        assert_demo_limited(create())
    assert not generate.called


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize("limit", [limits.DEMO, limits.DEMO_TOTAL])
def test_locked_recheck_refuses_with_429_not_503(db, limit):
    set_count(limit, limit.limit)
    passed = LimitCounter(window_start=datetime.now(UTC), count=0)
    with (
        mock.patch.object(limits, "peek", return_value=passed),
        mock.patch.object(
            demo, "generate_passwords", wraps=demo.generate_passwords
        ) as generate,
    ):
        assert_demo_limited(create())
    assert generate.called
    assert Workspace.objects.count() == 0
    assert stored(limit).count == limit.limit
    assert count_of(limits.DEMO) == (10 if limit is limits.DEMO else 0)


@pytest.mark.ac("ACC-2.5", "ACC-3.3")
def test_password_generation_failure_gives_503_and_counts_nothing(db):
    before = count_of(limits.DEMO_TOTAL)
    with mock.patch.object(
        demo, "generate_passwords", side_effect=RuntimeError("synthetic")
    ):
        assert_unavailable(create())
    assert Workspace.objects.count() == 0
    assert (count_of(limits.DEMO), count_of(limits.DEMO_TOTAL)) == (0, before)


@pytest.mark.ac("ACC-2.5", "ACC-3.3")
def test_render_failure_gives_503_and_counts_nothing(db):
    before = count_of(limits.DEMO_TOTAL)
    with mock.patch(
        "accounts.views.render_to_string", side_effect=RuntimeError("synthetic")
    ):
        assert_unavailable(create())
    assert Workspace.objects.count() == 0
    assert (count_of(limits.DEMO), count_of(limits.DEMO_TOTAL)) == (0, before)


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-2.5", "ACC-3.3")
def test_commit_failure_gives_503_and_counts_nothing():
    before = count_of(limits.DEMO_TOTAL)
    with mock.patch.object(
        connection, "commit", side_effect=DatabaseError("synthetic commit failure")
    ) as commit:
        response = create()
    assert commit.called
    assert_unavailable(response)
    assert Workspace.objects.count() == 0
    assert (count_of(limits.DEMO), count_of(limits.DEMO_TOTAL)) == (0, before)


@pytest.mark.ac("ACC-3.1", "ACC-3.3")
def test_limited_sign_in_never_checks_the_password(user):
    set_count(limits.SIGN_IN, 30)
    with mock.patch("accounts.views.authenticate") as checked:
        assert_sign_in_limited(sign_in(password=PASSWORD))
    assert not checked.called


@pytest.mark.ac("ACC-3.1")
def test_correct_password_racing_to_the_limit_is_refused_by_the_locked_recheck(user):
    set_count(limits.SIGN_IN, 30)
    passed = LimitCounter(window_start=datetime.now(UTC), count=0)
    client = Client()
    with (
        mock.patch.object(limits, "peek", return_value=passed),
        mock.patch("accounts.views.authenticate", wraps=authenticate) as checked,
    ):
        response = sign_in(client, password=PASSWORD)
    assert_sign_in_limited(response)
    assert checked.called
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert count_of(limits.SIGN_IN) == 30


@pytest.mark.django_db(transaction=True)
def test_password_is_checked_outside_any_transaction(user):
    in_transaction = []

    def check(*args, **kwargs):
        in_transaction.append(connection.in_atomic_block)
        return authenticate(*args, **kwargs)

    with mock.patch("accounts.views.authenticate", side_effect=check):
        assert_failure(sign_in())
        assert sign_in(password=PASSWORD).status_code == 302
    assert in_transaction == [False, False]


# ACC-3.5


@pytest.mark.ac("ACC-3.5")
def test_forged_forwarding_header_does_not_escape_the_limit(user):
    for attempt in range(30):
        sign_in(HTTP_X_FORWARDED_FOR=f"192.0.2.{attempt}")
    assert_sign_in_limited(sign_in(HTTP_X_FORWARDED_FOR=OTHER))
    set_count(limits.DEMO, 10)
    assert_demo_limited(create(HTTP_X_FORWARDED_FOR=OTHER))


@pytest.mark.ac("ACC-3.5")
def test_one_limited_address_does_not_limit_another(user):
    set_count(limits.SIGN_IN, 30)
    set_count(limits.DEMO, 10)
    assert_failure(sign_in(REMOTE_ADDR=OTHER))
    assert sign_in(password=PASSWORD, REMOTE_ADDR=OTHER).status_code == 302
    assert create(REMOTE_ADDR=OTHER).status_code == 200


@pytest.mark.ac("ACC-3.5")
def test_missing_or_unparseable_addresses_share_one_count(user):
    for attempt in range(30):
        assert_failure(sign_in(REMOTE_ADDR="" if attempt % 2 else "not-an-address"))
    assert_sign_in_limited(sign_in(REMOTE_ADDR="203.0.113.5:443"))
    assert_failure(sign_in())


# ACC-3.7


def assert_signed_out_and_nothing_created(client):
    assert not signed_in(client)
    assert Workspace.objects.exclude(name="Demo workspace limit001").count() == 0


@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("function", ["lock", "record", "start"])
def test_sign_in_limit_failure_gives_503(user, caplog, function):
    password = PASSWORD if function != "record" else WRONG
    client = Client()
    with mock.patch.object(limits, function, side_effect=OperationalError("synthetic")):
        response = sign_in(client, password=password)
    assert_unavailable(response)
    assert Session.objects.count() == 0
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert_signed_out_and_nothing_created(client)
    assert password not in caplog.text


@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("function", ["peek", "start", "lock", "record"])
def test_creation_limit_failure_gives_503(db, function):
    with mock.patch.object(limits, function, side_effect=OperationalError("synthetic")):
        assert_unavailable(create())
    assert Workspace.objects.count() == 0
    assert stored(limits.DEMO) is None


def hold_lock(limit, row_key, locked, release):
    try:
        with transaction.atomic():
            limits.lock(limit, row_key)
            locked.set()
            release.wait(10)
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("route", ["sign-in", "demo"])
def test_lock_timeout_gives_503(route):
    workspace = Workspace.objects.create(name="Demo workspace limit001")
    get_user_model().objects.create_user(
        "coord-limit001", PASSWORD, workspace=workspace, role="coordinator"
    )
    limit = limits.SIGN_IN if route == "sign-in" else limits.DEMO
    locked, release = threading.Event(), threading.Event()
    holder = threading.Thread(
        target=hold_lock, args=(limit, key(ADDRESS), locked, release)
    )
    holder.start()
    client = Client()
    try:
        assert locked.wait(10)
        with mock.patch.dict(limits.TIMEOUTS, {"lock_timeout": "100ms"}):
            response = (
                sign_in(client, password=PASSWORD) if route == "sign-in" else create()
            )
    finally:
        release.set()
        holder.join(10)
    assert_unavailable(response)
    assert not signed_in(client)
    assert Workspace.objects.count() == 1


# ACC-3.6 and ACC-3.8


def simultaneously(request, count=5):
    barrier = threading.Barrier(count)
    responses = [None] * count

    def run(index):
        try:
            barrier.wait(10)
            responses[index] = request()
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    return [response.status_code for response in responses]


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-3.6")
def test_simultaneous_creations_cannot_exceed_the_limit():
    set_count(limits.DEMO, 8)
    # A pause under the lock widens any race between reading and recording.
    with in_transaction_then(lambda: time.sleep(0.1)):
        statuses = simultaneously(create)
    assert sorted(statuses) == [200, 200, 429, 429, 429]
    assert Workspace.objects.count() == 2
    assert stored(limits.DEMO).count == 10


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-3.8")
def test_simultaneous_failed_sign_ins_cannot_exceed_the_limit():
    workspace = Workspace.objects.create(name="Demo workspace limit001")
    get_user_model().objects.create_user(
        "coord-limit001", PASSWORD, workspace=workspace, role="coordinator"
    )
    set_count(limits.SIGN_IN, 29)
    with in_transaction_then(lambda: time.sleep(0.1)):
        statuses = simultaneously(sign_in)
    assert sorted(statuses) == [200, 429, 429, 429, 429]
    assert stored(limits.SIGN_IN).count == 30


def pg_sleep():
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_sleep(0.5)")


TIMEOUT_CASES = {
    "idle": (
        "idle_in_transaction_session_timeout",
        lambda: time.sleep(0.5),
        "idle-in-transaction timeout",
    ),
    "statement": ("statement_timeout", pg_sleep, "statement timeout"),
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("timeout", TIMEOUT_CASES)
@pytest.mark.parametrize("route", ["wrong password", "correct password", "demo"])
def test_timeout_inside_a_limited_transaction_gives_503(caplog, user, timeout, route):
    set_count(limits.SIGN_IN, 3)
    set_count(limits.DEMO, 3)
    before = snapshot()
    setting, action, reason = TIMEOUT_CASES[timeout]
    client = Client()
    with (
        mock.patch.dict(limits.TIMEOUTS, {setting: "100ms"}),
        in_transaction_then(action),
    ):
        if route == "demo":
            response = create(client)
        else:
            password = PASSWORD if route == "correct password" else WRONG
            response = sign_in(client, password=password)
    assert_unavailable(response)
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert Session.objects.count() == 0
    assert snapshot() == before
    assert Workspace.objects.count() == 1
    assert reason in caplog.text
    assert PASSWORD not in caplog.text
