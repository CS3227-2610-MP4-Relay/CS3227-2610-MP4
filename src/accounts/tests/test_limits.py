import re
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.db import connection, transaction
from django.db.transaction import TransactionManagementError
from django.test import RequestFactory

from accounts import limits
from accounts.models import LimitCounter

T0 = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
KEY = "k" * 64


def key_for(remote_addr=None, **headers):
    request = RequestFactory().post("/sign-in/", **headers)
    if remote_addr is None:
        del request.META["REMOTE_ADDR"]  # RequestFactory sets 127.0.0.1
    else:
        request.META["REMOTE_ADDR"] = remote_addr
    return limits.client_key(request)


def at(moment):
    return mock.patch.object(limits.timezone, "now", return_value=moment)


@pytest.mark.ac("ACC-3.5")
def test_ipv4_addresses_count_individually():
    assert key_for("203.0.113.5") == key_for("203.0.113.5")
    assert key_for("203.0.113.5") != key_for("203.0.113.6")


@pytest.mark.ac("ACC-3.5")
def test_forged_forwarding_header_is_ignored():
    forged = key_for("203.0.113.5", HTTP_X_FORWARDED_FOR="198.51.100.7")
    assert forged == key_for("203.0.113.5")
    assert forged != key_for("198.51.100.7")


@pytest.mark.ac("ACC-3.5")
def test_ipv6_addresses_count_by_64_prefix():
    first = key_for("2001:db8:0:1::1")
    assert key_for("2001:db8:0:1:ffff:ffff:ffff:ffff") == first
    assert key_for("2001:db8:0:2::1") != first
    assert key_for("2001:db8:0:0:ffff:ffff:ffff:ffff") != first


@pytest.mark.ac("ACC-3.5")
def test_ipv4_mapped_ipv6_address_counts_as_its_ipv4_address():
    assert key_for("::ffff:203.0.113.5") == key_for("203.0.113.5")
    assert key_for("::ffff:203.0.113.6") != key_for("203.0.113.5")


@pytest.mark.ac("ACC-3.5")
@pytest.mark.parametrize("remote_addr", ["", "not-an-address", "203.0.113.5:443"])
def test_missing_or_unparseable_address_shares_the_unknown_key(remote_addr):
    assert key_for(remote_addr) == key_for(None)
    assert key_for(None) != key_for("203.0.113.5")


@pytest.mark.ac("ACC-3.5")
def test_stored_key_is_a_keyed_hash_not_the_address():
    key = key_for("203.0.113.5")
    assert re.fullmatch("[0-9a-f]{64}", key)
    assert "203" not in key
    assert key_for(None) != "unknown"


@pytest.mark.django_db
def test_migration_creates_the_overall_creation_row():
    assert LimitCounter.objects.filter(scope="demo-total", key="all").count() == 1


@pytest.mark.django_db
@pytest.mark.ac("ACC-3.3")
def test_peek_reads_a_missing_row_as_zero_without_writing():
    assert limits.peek(limits.DEMO, KEY).count == 0
    assert not LimitCounter.objects.filter(key=KEY).exists()


@pytest.mark.django_db
def test_peek_reads_the_stored_count():
    LimitCounter.objects.create(scope="demo", key=KEY, window_start=T0, count=4)
    with at(T0):
        assert limits.peek(limits.DEMO, KEY).count == 4
        assert limits.peek(limits.SIGN_IN, KEY).count == 0


@pytest.mark.django_db
def test_lock_inserts_a_missing_row_with_count_zero():
    with transaction.atomic():
        counter = limits.lock(limits.SIGN_IN, KEY)
    assert counter.pk and counter.count == 0
    assert LimitCounter.objects.get(scope="sign-in", key=KEY).count == 0


@pytest.mark.django_db
@pytest.mark.ac("ACC-3.3")
def test_lock_leaves_an_existing_window_and_count_unchanged():
    LimitCounter.objects.create(scope="sign-in", key=KEY, window_start=T0, count=30)
    with at(T0 + timedelta(minutes=10)), transaction.atomic():
        counter = limits.lock(limits.SIGN_IN, KEY)
    assert (counter.window_start, counter.count) == (T0, 30)
    stored = LimitCounter.objects.get(scope="sign-in", key=KEY)
    assert (stored.window_start, stored.count) == (T0, 30)


@pytest.mark.django_db
def test_lock_finds_the_migrated_overall_row():
    with transaction.atomic():
        counter = limits.lock(limits.DEMO_TOTAL, limits.TOTAL_KEY)
    assert LimitCounter.objects.filter(scope="demo-total").count() == 1
    assert counter.count == 0


@pytest.mark.django_db(transaction=True)
def test_lock_requires_a_transaction():
    with pytest.raises(TransactionManagementError):
        limits.lock(limits.SIGN_IN, KEY)


@pytest.mark.django_db
def test_record_starts_a_window_then_adds_to_it():
    with transaction.atomic():
        counter = limits.lock(limits.SIGN_IN, KEY)
        with at(T0):
            limits.record(counter, limits.SIGN_IN)
        with at(T0 + timedelta(minutes=5)):
            limits.record(counter, limits.SIGN_IN)
    stored = LimitCounter.objects.get(scope="sign-in", key=KEY)
    assert (stored.window_start, stored.count) == (T0, 2)


def counter_at_limit(limit):
    return LimitCounter(scope=limit.scope, key=KEY, window_start=T0, count=limit.limit)


@pytest.mark.ac("ACC-3.1", "ACC-3.4")
@pytest.mark.parametrize(
    ("limit", "number"),
    [(limits.SIGN_IN, 30), (limits.DEMO, 10), (limits.DEMO_TOTAL, 200)],
)
def test_limits_match_the_criteria(limit, number):
    assert limit.limit == number
    below = LimitCounter(scope=limit.scope, key=KEY, window_start=T0, count=number - 1)
    with at(T0):
        assert not limits.reached(below, limit)
        assert limits.reached(counter_at_limit(limit), limit)


@pytest.mark.ac("ACC-3.2")
@pytest.mark.parametrize(
    ("limit", "window"),
    [
        (limits.SIGN_IN, timedelta(minutes=15)),
        (limits.DEMO, timedelta(hours=1)),
        (limits.DEMO_TOTAL, timedelta(hours=24)),
    ],
)
def test_a_reached_limit_lasts_until_its_window_ends(limit, window):
    counter = counter_at_limit(limit)
    with at(T0 + window - timedelta(microseconds=1)):
        assert limits.reached(counter, limit)
    with at(T0 + window):
        assert not limits.reached(counter, limit)
    with at(T0 + window + timedelta(seconds=1)):
        assert not limits.reached(counter, limit)


@pytest.mark.django_db
@pytest.mark.ac("ACC-3.2")
def test_recording_after_the_window_ends_restarts_it():
    LimitCounter.objects.create(scope="sign-in", key=KEY, window_start=T0, count=30)
    end = T0 + timedelta(minutes=15)
    with transaction.atomic():
        counter = limits.lock(limits.SIGN_IN, KEY)
        with at(end):
            limits.record(counter, limits.SIGN_IN)
    stored = LimitCounter.objects.get(scope="sign-in", key=KEY)
    assert (stored.window_start, stored.count) == (end, 1)


@pytest.mark.django_db
@pytest.mark.ac("ACC-3.2")
def test_recording_just_before_the_window_ends_adds_to_it():
    LimitCounter.objects.create(scope="demo", key=KEY, window_start=T0, count=3)
    with transaction.atomic():
        counter = limits.lock(limits.DEMO, KEY)
        with at(T0 + timedelta(hours=1) - timedelta(microseconds=1)):
            limits.record(counter, limits.DEMO)
    stored = LimitCounter.objects.get(scope="demo", key=KEY)
    assert (stored.window_start, stored.count) == (T0, 4)


def setting(name):
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW {name}")
        return cursor.fetchone()[0]


@pytest.mark.django_db
@pytest.mark.ac("ACC-3.7")
def test_start_sets_the_transaction_timeouts():
    with transaction.atomic():
        limits.start()
        assert setting("lock_timeout") == "5s"
        assert setting("statement_timeout") == "10s"
        assert setting("idle_in_transaction_session_timeout") == "10s"


@pytest.mark.django_db(transaction=True)
def test_start_timeouts_end_with_their_transaction():
    before = setting("lock_timeout")
    with transaction.atomic():
        limits.start()
    assert setting("lock_timeout") == before


@pytest.mark.django_db(transaction=True)
def test_start_requires_a_transaction():
    with pytest.raises(TransactionManagementError):
        limits.start()
