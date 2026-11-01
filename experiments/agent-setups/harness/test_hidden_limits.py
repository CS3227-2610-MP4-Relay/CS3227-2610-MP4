"""Hidden acceptance suite for task 4 of the agent-setups experiment (#31).

Written from ACC-3 and the accounts notes of the technical spec (the limit
counter, the client address, and the `/sign-in/` and `/demo/` rows) as they
stood at ec1a951, before any run. It drives `/sign-in/` and `/demo/` over HTTP
from chosen client addresses and judges outcomes by status codes, the ACC-3
messages, whether a session started and the Workspace and User rows that
existed at the start, so it does not depend on how a candidate stores its
counts.

Not covered: ACC-3.2, because reaching a window's end needs control of the
clock, which each implementation reads differently, and for the same reason
ACC-3.3's rule that a refused sign-in does not extend its window; ACC-3.7 and
ACC-3.3's failed creations, because storage faults need injection specific to
an implementation. The concurrency tests of ACC-3.6 and ACC-3.8 send requests
from threads, each with its own client and database connection, so they
commit for real and restore the migrated rows before they start.
"""

import re
import threading

import pytest
from django.conf import settings
from django.db import connections
from django.test import Client

from accounts.models import User, Workspace

PASSWORD = "Synthetic16Chars"
FAILURE = "Username or password is incorrect."
SIGN_IN_LIMITED = "Too many sign-in attempts. Try again later."
DEMO_LIMITED = "Too many demo workspaces have been created recently. Try again later."
SIGN_IN_LIMIT = 30
DEMO_LIMIT = 10
TOTAL_LIMIT = 200
NUL = chr(0)
FOREIGN_ORIGIN = "https://attacker.example"
# Missing (None), empty and unparseable client addresses, all one "unknown".
UNKNOWN_ADDRESSES = [None, "", "not-an-address", "999.1.1.1"]


class NoAddressClient(Client):
    """A test client whose requests carry no `REMOTE_ADDR` at all."""

    def _base_environ(self, **request):
        environ = super()._base_environ(**request)
        environ.pop("REMOTE_ADDR", None)
        return environ


def client_at(address, **options):
    """A test client whose requests come from `address`; None sends none."""
    if address is None:
        return NoAddressClient(**options)
    return Client(REMOTE_ADDR=address, **options)


def text(response):
    """The page's text with tags removed and whitespace collapsed."""
    plain = re.sub(r"<[^>]+>", "", response.content.decode())
    return re.sub(r"\s+", " ", plain)


def coordinator(name):
    """A workspace and its Test Coordinator, who signs in with PASSWORD."""
    workspace = Workspace.objects.create(name=f"Demo workspace {name}")
    return User.objects.create_user(
        f"coord-{name}", PASSWORD, workspace=workspace, role="coordinator"
    )


def counts():
    """The number of workspaces and accounts."""
    return Workspace.objects.count(), User.objects.count()


def sign_in(address, username="nobody-hid4", password="Wrong16CharsPass", **extra):
    """POST a sign-in from `address` with a fresh client."""
    data = {"username": username, "password": password}
    return client_at(address).post("/sign-in/", data, **extra)


def create(address, **extra):
    """POST a demo creation from `address` with a fresh client."""
    return client_at(address).post("/demo/", **extra)


def assert_failure(response):
    """The normal ACC-1.2 failure, not a limit."""
    assert response.status_code == 200
    assert FAILURE in text(response)
    assert SIGN_IN_LIMITED not in text(response)


def assert_sign_in_limited(response):
    """The ACC-3.1 refusal."""
    assert response.status_code == 429
    assert SIGN_IN_LIMITED in text(response)


def assert_demo_limited(response):
    """The ACC-3.4 refusal."""
    assert response.status_code == 429
    assert DEMO_LIMITED in text(response)


def assert_signed_in_as_coordinator(response, client):
    """A redirect to the Coordinator home, which then opens."""
    assert response.status_code == 302
    assert response["Location"].endswith("/coordinator/")
    assert client.get("/coordinator/").status_code == 200


def fail(address, times):
    """Send `times` wrong-password sign-ins from `address`, each a normal failure."""
    for _ in range(times):
        assert_failure(sign_in(address))


def create_many(address, times):
    """Create `times` demo workspaces from `address`, each successfully."""
    for _ in range(times):
        assert create(address).status_code == 200


def refused_posts(address, path, data=None):
    """Two POSTs refused by CSRF protection: no token, and a foreign origin."""
    client = client_at(address, enforce_csrf_checks=True)
    client.get("/sign-in/")
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    with_token = {**(data or {}), "csrfmiddlewaretoken": token}
    return [
        client.post(path, data or {}),
        client.post(path, with_token, HTTP_ORIGIN=FOREIGN_ORIGIN),
    ]


def simultaneously(address, count, send):
    """Call `send(client)` from `count` threads at once, each with its own client."""
    barrier = threading.Barrier(count)
    responses, errors = [None] * count, []

    def run(index):
        try:
            client = client_at(address)
            barrier.wait(30)
            responses[index] = send(client)
        except Exception as error:  # noqa: BLE001 - reported by the assertion below
            errors.append(error)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors, errors
    return responses


# --- ACC-3.1: the sign-in limit ---


def test_the_30th_failed_sign_in_gets_the_normal_failure(db):
    fail("192.0.2.1", SIGN_IN_LIMIT)


def test_the_31st_sign_in_gets_429_with_the_message(db):
    fail("192.0.2.2", SIGN_IN_LIMIT)
    assert_sign_in_limited(sign_in("192.0.2.2"))


def test_a_correct_password_at_the_limit_gets_429_and_no_session(db):
    user = coordinator("hid4a")
    fail("192.0.2.3", SIGN_IN_LIMIT)
    client = client_at("192.0.2.3")
    data = {"username": user.username, "password": PASSWORD}
    assert_sign_in_limited(client.post("/sign-in/", data))
    home = client.get("/coordinator/")
    assert home.status_code == 302
    assert "/sign-in/" in home["Location"]


# --- ACC-3.3: what counts ---


def test_blank_fields_count_as_failures(db):
    blanks = [("", ""), ("", "Wrong16CharsPass"), ("nobody-hid4", "")]
    for attempt in range(SIGN_IN_LIMIT):
        username, password = blanks[attempt % len(blanks)]
        assert_failure(sign_in("192.0.2.4", username, password))
    assert_sign_in_limited(sign_in("192.0.2.4", "", ""))


def test_invalid_fields_count_as_failures(db):
    invalid = [
        ("nobody" + NUL, "Wrong16CharsPass"),
        ("nobody-hid4", "Wrong" + NUL + "Pass"),
        ("u" * 151, "Wrong16CharsPass"),
        ("   ", "Wrong16CharsPass"),
    ]
    for attempt in range(SIGN_IN_LIMIT):
        username, password = invalid[attempt % len(invalid)]
        assert_failure(sign_in("192.0.2.5", username, password))
    assert_sign_in_limited(sign_in("192.0.2.5"))


def test_a_successful_sign_in_neither_counts_nor_resets_the_count(db):
    user = coordinator("hid4b")
    fail("192.0.2.6", SIGN_IN_LIMIT - 1)
    client = client_at("192.0.2.6")
    data = {"username": user.username, "password": PASSWORD}
    assert_signed_in_as_coordinator(client.post("/sign-in/", data), client)
    assert_failure(sign_in("192.0.2.6"))
    assert_sign_in_limited(sign_in("192.0.2.6"))


def test_sign_ins_refused_by_csrf_protection_do_not_count(db):
    fail("192.0.2.7", SIGN_IN_LIMIT - 1)
    data = {"username": "nobody-hid4", "password": "Wrong16CharsPass"}
    for _ in range(2):
        for response in refused_posts("192.0.2.7", "/sign-in/", data):
            assert response.status_code == 403
    assert_failure(sign_in("192.0.2.7"))
    assert_sign_in_limited(sign_in("192.0.2.7"))


def test_viewing_the_sign_in_page_is_never_limited(db):
    client = client_at("192.0.2.8")
    for _ in range(SIGN_IN_LIMIT + 5):
        assert client.get("/sign-in/").status_code == 200
    fail("192.0.2.8", SIGN_IN_LIMIT)
    sign_in("192.0.2.8")
    page = client_at("192.0.2.8").get("/sign-in/")
    assert page.status_code == 200
    assert SIGN_IN_LIMITED not in text(page)


def test_demo_creations_refused_by_csrf_protection_do_not_count(db):
    create_many("198.51.100.1", DEMO_LIMIT - 1)
    for _ in range(2):
        for response in refused_posts("198.51.100.1", "/demo/"):
            assert response.status_code == 403
    assert create("198.51.100.1").status_code == 200
    assert_demo_limited(create("198.51.100.1"))


def test_a_signed_in_users_demo_request_does_not_count(db):
    user = coordinator("hid4c")
    create_many("198.51.100.2", DEMO_LIMIT - 1)
    client = client_at("198.51.100.2")
    client.force_login(user)
    for _ in range(3):
        assert client.post("/demo/").status_code == 302
    assert create("198.51.100.2").status_code == 200
    assert_demo_limited(create("198.51.100.2"))


def test_refused_demo_creations_do_not_count_toward_the_total(db):
    create_many("198.51.100.3", DEMO_LIMIT)
    for _ in range(5):
        assert_demo_limited(create("198.51.100.3"))
    for index in range(TOTAL_LIMIT - DEMO_LIMIT):
        assert create(f"10.43.{index // 100}.{index % 100 + 1}").status_code == 200
    assert_demo_limited(create("10.43.9.9"))


# --- ACC-3.4: the demo creation limits ---


def test_the_10th_demo_creation_from_one_address_succeeds(db):
    before = Workspace.objects.count()
    create_many("198.51.100.4", DEMO_LIMIT)
    assert Workspace.objects.count() == before + DEMO_LIMIT


def test_the_11th_demo_creation_from_one_address_gets_429_and_creates_nothing(db):
    create_many("198.51.100.5", DEMO_LIMIT)
    before = counts()
    assert_demo_limited(create("198.51.100.5"))
    assert counts() == before


def test_the_201st_demo_creation_from_all_addresses_gets_429_and_creates_nothing(db):
    for index in range(TOTAL_LIMIT):
        assert create(f"10.44.{index // 100}.{index % 100 + 1}").status_code == 200
    before = counts()
    assert_demo_limited(create("10.44.9.9"))
    assert counts() == before


# --- ACC-3.5: no escape, no spill-over ---


def test_varying_the_username_does_not_escape_the_sign_in_limit(db):
    user = coordinator("hid4d")
    for attempt in range(SIGN_IN_LIMIT):
        username = user.username if attempt % 3 == 0 else f"nobody-{attempt}"
        assert_failure(sign_in("192.0.2.9", username))
    assert_sign_in_limited(sign_in("192.0.2.9", "nobody-else"))


def test_a_forged_forwarded_for_does_not_escape_the_sign_in_limit(db):
    for attempt in range(SIGN_IN_LIMIT):
        forged = f"203.0.113.{attempt + 1}"
        assert_failure(sign_in("192.0.2.10", HTTP_X_FORWARDED_FOR=forged))
    forged = "203.0.113.200, 203.0.113.201"
    assert_sign_in_limited(sign_in("192.0.2.10", HTTP_X_FORWARDED_FOR=forged))


def test_a_forged_forwarded_for_does_not_escape_the_demo_limit(db):
    for attempt in range(DEMO_LIMIT):
        forged = f"203.0.113.{attempt + 1}"
        response = create("198.51.100.6", HTTP_X_FORWARDED_FOR=forged)
        assert response.status_code == 200
    before = counts()
    response = create("198.51.100.6", HTTP_X_FORWARDED_FOR="203.0.113.200")
    assert_demo_limited(response)
    assert counts() == before


def test_a_forwarded_for_naming_a_limited_address_does_not_limit_another(db):
    fail("192.0.2.11", SIGN_IN_LIMIT)
    assert_sign_in_limited(sign_in("192.0.2.11"))
    assert_failure(sign_in("192.0.2.12", HTTP_X_FORWARDED_FOR="192.0.2.11"))


def test_one_address_at_its_sign_in_limit_does_not_limit_another(db):
    user = coordinator("hid4e")
    fail("192.0.2.13", SIGN_IN_LIMIT)
    assert_sign_in_limited(sign_in("192.0.2.13"))
    assert_failure(sign_in("192.0.2.14"))
    client = client_at("192.0.2.14")
    data = {"username": user.username, "password": PASSWORD}
    assert_signed_in_as_coordinator(client.post("/sign-in/", data), client)


def test_one_address_at_its_demo_limit_does_not_limit_another(db):
    create_many("198.51.100.7", DEMO_LIMIT)
    assert_demo_limited(create("198.51.100.7"))
    assert create("198.51.100.8").status_code == 200


def test_missing_and_unparseable_addresses_share_one_sign_in_count(db):
    for attempt in range(SIGN_IN_LIMIT):
        address = UNKNOWN_ADDRESSES[attempt % len(UNKNOWN_ADDRESSES)]
        assert_failure(sign_in(address))
    for address in UNKNOWN_ADDRESSES:
        assert_sign_in_limited(sign_in(address))


def test_missing_and_unparseable_addresses_share_one_demo_count(db):
    for attempt in range(DEMO_LIMIT):
        address = UNKNOWN_ADDRESSES[attempt % len(UNKNOWN_ADDRESSES)]
        assert create(address).status_code == 200
    for address in UNKNOWN_ADDRESSES:
        assert_demo_limited(create(address))


def test_ipv6_addresses_in_one_64_share_the_sign_in_count(db):
    for attempt in range(SIGN_IN_LIMIT):
        assert_failure(sign_in(f"2001:db8:4:6::{attempt + 1:x}"))
    assert_sign_in_limited(sign_in("2001:db8:4:6:ffff:ffff:ffff:ffff"))


def test_ipv6_addresses_in_different_64s_do_not_share_a_count(db):
    fail("2001:db8:4:8::1", SIGN_IN_LIMIT)
    assert_sign_in_limited(sign_in("2001:db8:4:8::1"))
    assert_failure(sign_in("2001:db8:4:9::1"))


# --- ACC-3.6 and ACC-3.8: concurrent requests ---


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_five_simultaneous_creations_with_two_left_create_at_most_two():
    create_many("198.51.100.9", DEMO_LIMIT - 2)
    before = Workspace.objects.count()
    responses = simultaneously("198.51.100.9", 5, lambda client: client.post("/demo/"))
    made = Workspace.objects.count() - before
    assert made <= 2
    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == made
    for response in responses:
        if response.status_code != 200:
            assert_demo_limited(response)


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_five_simultaneous_failed_sign_ins_with_one_left_give_one_failure_at_most():
    fail("192.0.2.15", SIGN_IN_LIMIT - 1)
    data = {"username": "nobody-hid4", "password": "Wrong16CharsPass"}
    responses = simultaneously(
        "192.0.2.15", 5, lambda client: client.post("/sign-in/", data)
    )
    normal = [response for response in responses if response.status_code == 200]
    assert len(normal) <= 1
    for response in normal:
        assert_failure(response)
    for response in responses:
        if response.status_code != 200:
            assert_sign_in_limited(response)
