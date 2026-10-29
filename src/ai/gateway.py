"""Bounded provider-independent access to Relay's shared SoC LLM."""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.db import connection, transaction
from django.utils import timezone

from .models import CallSlot, Usage

logger = logging.getLogger(__name__)

INPUT_LIMIT = 8000
REPLY_LIMIT = 20000
TOTAL_TIMEOUT = 30
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


class _NoRedirect(HTTPRedirectHandler):
    """Never follow a provider redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Refuse the redirect by raising its HTTP error."""
        raise HTTPError(newurl, code, msg, headers, fp)


def _user_key(user):
    return str(user.pk)


def _reserve(user, now):
    """Atomically reserve quota and both in-flight slots, or refuse."""
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
        live = [slot for slot in deployment if slot.expires_at > now]
        if len(live) >= DEPLOYMENT_IN_FLIGHT:
            return None
        user_usage, _ = Usage.objects.select_for_update().get_or_create(
            scope=USER_CALLS_SCOPE,
            key=_user_key(user),
            defaults={"window_start": now, "count": 0},
        )
        deployment_usage, _ = Usage.objects.select_for_update().get_or_create(
            scope=DEPLOYMENT_CALLS_SCOPE,
            key="all",
            defaults={"window_start": now, "count": 0},
        )
        if now >= user_usage.window_start + USER_WINDOW:
            user_usage.window_start, user_usage.count = now, 0
        if now >= deployment_usage.window_start + DEPLOYMENT_WINDOW:
            deployment_usage.window_start, deployment_usage.count = now, 0
        if user_usage.count >= USER_CALLS or deployment_usage.count >= DEPLOYMENT_CALLS:
            return None
        user_usage.count += 1
        deployment_usage.count += 1
        user_usage.save(update_fields=["window_start", "count"])
        deployment_usage.save(update_fields=["window_start", "count"])
        expires = now + timedelta(seconds=TOTAL_TIMEOUT)
        user_slot.expires_at = expires
        user_slot.save(update_fields=["expires_at"])
        reusable = next(slot for slot in deployment if slot.expires_at <= now)
        reusable.expires_at = expires
        reusable.save(update_fields=["expires_at"])
        return user_slot, reusable


def _release(user_slot, deployment_slot):
    """Release the two slots reserved by one call after every exit."""
    if user_slot is None:
        return
    now = timezone.now()
    for slot in (user_slot, deployment_slot):
        if slot.expires_at > now:
            slot.expires_at = now
            slot.save(update_fields=["expires_at"])


def _endpoint():
    """Return the verified HTTPS endpoint, or None when unconfigured."""
    url = os.environ.get("SOC_LLM_ENDPOINT", "").strip()
    if not url:
        return None
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
    ):
        return None
    return url


def _valid_text_object(value):
    """Accept exactly one JSON object with one string `text` field."""
    if type(value) is not dict or set(value) != {"text"}:
        return None
    text = value["text"]
    if type(text) is not str or len(text) > REPLY_LIMIT:
        return None
    return text


def _transport(instructions, data):
    """Send one request without redirects or retries, returning a result."""
    endpoint = _endpoint()
    api_key = os.environ.get("SOC_LLM_API_KEY", "").strip()
    model = os.environ.get("SOC_LLM_MODEL", "").strip()
    if endpoint is None or not api_key or not model:
        return Refused("not-configured")
    body = json.dumps(
        {"model": model, "instructions": instructions, "data": data},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    opener = build_opener(_NoRedirect)
    started = time.monotonic()
    try:
        with opener.open(request, timeout=TOTAL_TIMEOUT) as response:
            raw = response.read(REPLY_LIMIT * 4 + 1)
    except HTTPError as error:
        if error.code in {400, 401, 403, 429}:
            return Refused("quota" if error.code == 429 else "provider-refused")
        return Failed("transport")
    except TimeoutError:
        return Failed("timeout")
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            return Failed("timeout")
        return Failed("transport")
    except OSError:
        return Failed("transport")
    if time.monotonic() - started > TOTAL_TIMEOUT:
        return Failed("timeout")
    if len(raw) > REPLY_LIMIT * 4:
        return Failed("invalid-response")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, JSONDecodeError, ValueError, RecursionError):
        return Failed("invalid-response")
    if type(value) is dict and set(value) == {"refusal"}:
        if type(value["refusal"]) is str:
            return Refused("provider-refused")
        return Failed("invalid-response")
    text = _valid_text_object(value)
    if text is None:
        return Failed("invalid-response")
    return Success(text)


def complete(user, instructions, data, provider=None):
    """Run one bounded call for `user`, or return a refusal/failure.

    `provider` is a test/fake seam; it must expose `complete(instructions, data)`
    returning Success, Refused or Failed. The real provider is the HTTP transport.
    """
    if len(instructions) + len(data) > INPUT_LIMIT:
        return Refused("input-too-large")
    now = timezone.now()
    reserved = _reserve(user, now)
    if reserved is None:
        return Refused("busy-or-quota")
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
            except Exception:  # noqa: BLE001 - provider errors map to a fixed code
                result = Failed("provider-error")
        else:
            result = _transport(instructions, data)
        if not isinstance(result, (Success, Refused, Failed)):
            result = Failed("provider-error")
        code = "success" if isinstance(result, Success) else result.code
        logger.info("LLM gateway outcome: %s", code)
        return result
    finally:
        _release(*reserved)
        reserved[0].expires_at = timezone.now()
        reserved[0].save(update_fields=["expires_at"])
