"""Fixed-window abuse limits on failed sign-ins and demo creations (ACC-3).

Views call only the functions below: `start` and `lock` inside one transaction,
then `reached` and, for a counted request, `record`. Refused requests record
nothing, so they never move a window.
"""

import ipaddress
from datetime import timedelta
from typing import NamedTuple

from django.db import connection
from django.db.transaction import TransactionManagementError
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import LimitCounter

ADDRESS_SALT = "accounts.limits.client-address"
UNKNOWN = "unknown"
TOTAL_KEY = "all"
TIMEOUTS = {
    "lock_timeout": "5s",
    "statement_timeout": "10s",
    "idle_in_transaction_session_timeout": "10s",
}


class Limit(NamedTuple):
    """A scope's maximum count within its window."""

    scope: str
    limit: int
    window: timedelta


SIGN_IN = Limit(LimitCounter.Scope.SIGN_IN, 30, timedelta(minutes=15))
DEMO = Limit(LimitCounter.Scope.DEMO, 10, timedelta(hours=1))
DEMO_TOTAL = Limit(LimitCounter.Scope.DEMO_TOTAL, 200, timedelta(hours=24))

_TABLE = LimitCounter._meta.db_table
_LOCK_SQL = f"""
    INSERT INTO {_TABLE} (scope, key, window_start, count) VALUES (%s, %s, %s, 0)
    ON CONFLICT (scope, key) DO UPDATE SET count = {_TABLE}.count
    RETURNING id, window_start, count
"""


def _client_value(remote_addr):
    try:
        address = ipaddress.ip_address(remote_addr)
    except ValueError:
        return UNKNOWN
    if address.version == 4:
        return str(address)
    if address.ipv4_mapped:
        return str(address.ipv4_mapped)
    return str(ipaddress.IPv6Network((int(address) >> 64 << 64, 64)))


def client_key(request):
    """Return the keyed hash of the request's `REMOTE_ADDR`, IPv6 by /64 prefix."""
    value = _client_value(request.META.get("REMOTE_ADDR", ""))
    return salted_hmac(ADDRESS_SALT, value, algorithm="sha256").hexdigest()


def _require_transaction():
    if not connection.in_atomic_block:
        raise TransactionManagementError("Limit locks need a transaction.")


def start():
    """Set this transaction's lock, statement and idle-in-transaction timeouts."""
    _require_transaction()
    calls = ", ".join("set_config(%s, %s, true)" for _ in TIMEOUTS)
    params = [part for item in TIMEOUTS.items() for part in item]
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {calls}", params)


def peek(limit, key):
    """Read a counter without locking it; a missing row counts as 0."""
    counter = LimitCounter.objects.filter(scope=limit.scope, key=key).first()
    return counter or LimitCounter(
        scope=limit.scope, key=key, window_start=timezone.now(), count=0
    )


def lock(limit, key):
    """Insert the counter with count 0, or lock it unchanged, and return it."""
    _require_transaction()
    with connection.cursor() as cursor:
        cursor.execute(_LOCK_SQL, [limit.scope, key, timezone.now()])
        pk, window_start, count = cursor.fetchone()
    return LimitCounter(
        pk=pk, scope=limit.scope, key=key, window_start=window_start, count=count
    )


def _window_ended(counter, limit):
    return timezone.now() >= counter.window_start + limit.window


def reached(counter, limit):
    """Return whether the counter is at its limit within its window."""
    return counter.count >= limit.limit and not _window_ended(counter, limit)


def record(counter, limit):
    """Count one request, restarting the window if it has ended."""
    if counter.count == 0 or _window_ended(counter, limit):
        counter.window_start, counter.count = timezone.now(), 1
    else:
        counter.count += 1
    counter.save(update_fields=["window_start", "count"])
