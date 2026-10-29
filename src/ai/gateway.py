"""Bounded provider-independent access to Relay's shared SoC LLM.

Every limit here is a proposal pending confirmation (workflow/specs/ai/llm-gateway.md),
and live calls stay off while `settings.SOC_LLM_LIVE` is False.
"""

import http.client
import io
import json
import logging
import os
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import CallRecord, CallSlot

logger = logging.getLogger(__name__)

INPUT_LIMIT = 8000
REPLY_LIMIT = 20000
RESPONSE_BYTES = REPLY_LIMIT * 12 + 4096
TOTAL_TIMEOUT = 30
RELEASE_MARGIN = 5
USER_CALLS = 20
DEPLOYMENT_CALLS = 200
USER_WINDOW = timedelta(hours=1)
DEPLOYMENT_WINDOW = timedelta(hours=1)
USER_IN_FLIGHT = 1
DEPLOYMENT_IN_FLIGHT = 2

USER_SCOPE = "user"
USER_CALLS_SCOPE = "user-calls"
DEPLOYMENT_SCOPE = "deployment"
DEPLOYMENT_CALLS_SCOPE = "deployment-calls"


@dataclass(frozen=True)
class Success:
    """A provider reply that passed the gateway envelope."""

    text: str


@dataclass(frozen=True)
class Refused:
    """A request the gateway declined or a provider refusal."""

    code: str


@dataclass(frozen=True)
class Failed:
    """A transport, timeout or malformed-response failure."""

    code: str


def _user_key(user):
    return str(user.pk)


def _quota(scope, key, limit, window, now):
    """Count a call in the rolling window, removing expired records."""
    CallRecord.objects.filter(
        scope=scope, key=key, created_at__lte=now - window
    ).delete()
    if CallRecord.objects.filter(scope=scope, key=key).count() >= limit:
        return False
    CallRecord.objects.create(scope=scope, key=key, created_at=now)
    return True


def _reserve(user, now):
    """Atomically reserve quota and both in-flight slots, or return None.

    Returns the user slot, the deployment slot and the expiry they now hold.
    """
    with transaction.atomic():
        user_slot, _ = CallSlot.objects.select_for_update().get_or_create(
            scope=USER_SCOPE, key=_user_key(user), defaults={"expires_at": now}
        )
        if user_slot.expires_at > now:
            return None
        deployment = list(
            CallSlot.objects.select_for_update()
            .filter(scope=DEPLOYMENT_SCOPE)
            .order_by("pk")
        )
        if len(deployment) != DEPLOYMENT_IN_FLIGHT:
            return None
        free = [slot for slot in deployment if slot.expires_at <= now]
        if not free:
            return None
        if not _quota(USER_CALLS_SCOPE, _user_key(user), USER_CALLS, USER_WINDOW, now):
            transaction.set_rollback(True)
            return None
        if not _quota(
            DEPLOYMENT_CALLS_SCOPE, "all", DEPLOYMENT_CALLS, DEPLOYMENT_WINDOW, now
        ):
            transaction.set_rollback(True)
            return None
        expires = now + timedelta(seconds=TOTAL_TIMEOUT + RELEASE_MARGIN)
        CallSlot.objects.filter(pk__in=[user_slot.pk, free[0].pk]).update(
            expires_at=expires
        )
        return user_slot, free[0], expires


def _release(user_slot, deployment_slot, expires):
    """Free this call's two slots, unless a later call already holds them."""
    CallSlot.objects.filter(
        pk__in=[user_slot.pk, deployment_slot.pk], expires_at=expires
    ).update(expires_at=timezone.now())


def _endpoint():
    """Return the parsed fixed HTTPS endpoint, or None when unconfigured."""
    url = os.environ.get("SOC_LLM_ENDPOINT", "").strip()
    if not url or any(char.isspace() or not char.isprintable() for char in url):
        return None
    parts = urlsplit(url)
    try:
        parts.port  # noqa: B018 - raises ValueError for an invalid port
    except ValueError:
        return None
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
    ):
        return None
    return parts


def _remaining(deadline):
    """Return the seconds left before `deadline`, or raise TimeoutError."""
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return left


def _resolve(host, port, deadline):
    """Resolve `host` in a helper thread, abandoned at the deadline."""
    found = {}
    done = threading.Event()

    def lookup():
        try:
            found["addresses"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as error:
            found["error"] = error
        finally:
            done.set()

    threading.Thread(target=lookup, daemon=True).start()
    if not done.wait(_remaining(deadline)):
        raise TimeoutError
    if "error" in found:
        raise found["error"]
    return found["addresses"]


def _connect(host, port, deadline):
    """Open a TCP connection to `host` within the deadline (the network step)."""
    error = OSError("no address")
    for family, kind, proto, _, address in _resolve(host, port, deadline):
        sock = socket.socket(family, kind, proto)
        try:
            sock.settimeout(_remaining(deadline))
            sock.connect(address)
        except TimeoutError:
            sock.close()
            raise
        except OSError as failure:
            sock.close()
            error = failure
            continue
        return sock
    raise error


def _tls_context():
    """Return a verifying TLS context: certificate and hostname checks on."""
    return ssl.create_default_context()


@sensitive_variables("payload", "chunks", "chunk")
def _exchange(parts, payload, deadline):
    """Send `payload` and return the raw response, all within the deadline."""
    sock = _connect(parts.hostname, parts.port or 443, deadline)
    try:
        sock.settimeout(_remaining(deadline))
        sock = _tls_context().wrap_socket(sock, server_hostname=parts.hostname)
        sent = 0
        while sent < len(payload):
            sock.settimeout(_remaining(deadline))
            sent += sock.send(payload[sent : sent + 16384])
        chunks, total = [], 0
        while True:
            sock.settimeout(_remaining(deadline))
            chunk = sock.recv(65536)
            _remaining(deadline)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            total += len(chunk)
            if total > RESPONSE_BYTES:
                raise ValueError
    finally:
        sock.close()


class _Received:
    """Present received bytes as a socket so http.client can parse them."""

    def __init__(self, raw):
        self.raw = raw

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.raw)


@sensitive_variables("raw", "response")
def _parse_http(raw):
    """Return the status and body of a complete raw HTTP response."""
    response = http.client.HTTPResponse(_Received(raw), method="POST")
    response.begin()
    return response.status, response.read()


def _no_repeated_keys(pairs):
    """Build a dict, refusing a repeated key."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(value)


@sensitive_variables("body", "value", "text")
def _envelope(body):
    """Map a 2xx body to Success, a refusal or an invalid-response failure."""
    try:
        value = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_no_repeated_keys,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError):
        return Failed("invalid-response")
    if type(value) is dict and set(value) == {"refusal"}:
        if type(value["refusal"]) is str:
            return Refused("provider-refused")
        return Failed("invalid-response")
    if type(value) is not dict or set(value) != {"text"}:
        return Failed("invalid-response")
    text = value["text"]
    if (
        type(text) is not str
        or len(text) > REPLY_LIMIT
        or any(0xD800 <= ord(char) <= 0xDFFF for char in text)
    ):
        return Failed("invalid-response")
    return Success(text)


@sensitive_variables(
    "api_key", "head", "body", "payload", "instructions", "data", "raw"
)
def _transport(instructions, data, deadline):
    """Send one request without redirects or retries, returning a result."""
    if not settings.SOC_LLM_LIVE:
        return Refused("live-off")
    parts = _endpoint()
    api_key = os.environ.get("SOC_LLM_API_KEY", "").strip()
    model = os.environ.get("SOC_LLM_MODEL", "").strip()
    usable_key = api_key.isascii() and api_key.isprintable()
    if parts is None or not model or not api_key or not usable_key:
        return Refused("not-configured")
    try:
        body = json.dumps(
            {"model": model, "instructions": instructions, "data": data},
            ensure_ascii=False,
        ).encode("utf-8")
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        head = (
            f"POST {target} HTTP/1.1\r\nHost: {parts.netloc}\r\n"
            f"Authorization: Bearer {api_key}\r\n"
            "Content-Type: application/json\r\nAccept: application/json\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
        )
        payload = head.encode("ascii") + body
    except UnicodeError:
        return Failed("transport")
    try:
        raw = _exchange(parts, payload, deadline)
        status, body = _parse_http(raw)
    except TimeoutError:
        return Failed("timeout")
    except (OSError, http.client.HTTPException):
        return Failed("transport")
    except ValueError:
        return Failed("invalid-response")
    if status in {400, 401, 403}:
        return Refused("provider-refused")
    if status == 429:
        return Refused("quota")
    if not 200 <= status < 300:
        return Failed("transport")
    return _envelope(body)


@sensitive_variables("instructions", "data", "result")
def complete(user, instructions, data, provider=None):
    """Run one bounded call for `user`, or return a refusal/failure.

    `provider` is a test seam exposing `complete(instructions, data)` that
    returns Success, Refused or Failed; without it the call uses the HTTPS
    transport, which refuses while live calls are off. A storage error while
    reserving or releasing is raised for the feature's own error handling.
    """
    if provider is None and not settings.SOC_LLM_LIVE:
        logger.info("LLM gateway outcome: %s", "live-off")
        return Refused("live-off")
    if len(instructions) + len(data) > INPUT_LIMIT:
        return Refused("input-too-large")
    reserved = _reserve(user, timezone.now())
    if reserved is None:
        return Refused("busy-or-quota")
    deadline = time.monotonic() + TOTAL_TIMEOUT
    try:
        # No transaction or round lock is open here; do not hold a database
        # connection through a slow provider call.
        if not connection.in_atomic_block:
            connection.close()
        if provider is not None:
            try:
                result = provider.complete(instructions, data)
            except TimeoutError:
                result = Failed("timeout")
            except DatabaseError:
                raise
            except Exception:  # noqa: BLE001 - provider errors map to a fixed code
                result = Failed("provider-error")
        else:
            result = _transport(instructions, data, deadline)
        if not isinstance(result, (Success, Refused, Failed)):
            result = Failed("provider-error")
        code = "success" if isinstance(result, Success) else result.code
        logger.info("LLM gateway outcome: %s", code)
        return result
    finally:
        _release(*reserved)
