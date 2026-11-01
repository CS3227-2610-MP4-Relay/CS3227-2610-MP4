"""Bounded provider-independent access to Relay's shared SoC LLM.

The contract is workflow/specs/ai/llm-gateway.md. Live calls require configured
provider settings and refuse while `settings.SOC_LLM_LIVE` is False. Relay
applies its own rules here; aiohttp does the networking.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import ssl
import threading
import time
from dataclasses import dataclass, replace
from datetime import timedelta
from urllib.parse import urlsplit

import aiohttp
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
CLEANUP_TIMEOUT = 1
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

TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")
MAX_COUNT = 2**63 - 1


@dataclass(frozen=True)
class Usage:
    """Optional provider counts; the gateway validates each before use."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def _count(value):
    return value if type(value) is int and 0 <= value <= MAX_COUNT else None


@sensitive_variables("usage")
def _checked_usage(usage):
    """Keep only bounded numeric fields from a typed usage value."""
    if type(usage) is not Usage:
        return None
    counts = [_count(getattr(usage, name)) for name in TOKEN_FIELDS]
    return Usage(*counts) if any(value is not None for value in counts) else None


@dataclass(frozen=True)
class Success:
    """A provider reply that passed the gateway envelope."""

    text: str
    usage: Usage | None = None


@dataclass(frozen=True)
class Refused:
    """A request the gateway declined or a provider refusal."""

    code: str
    usage: Usage | None = None


@dataclass(frozen=True)
class Failed:
    """A transport, timeout or malformed-response failure."""

    code: str
    usage: Usage | None = None


def _valid_reply_text(text):
    """Check the shared reply type, character limit and Unicode validity."""
    return (
        type(text) is str
        and len(text) <= REPLY_LIMIT
        and not any(0xD800 <= ord(char) <= 0xDFFF for char in text)
    )


@sensitive_variables("result")
def _checked_result(result):
    """Reject malformed provider results before returning or logging them."""
    if type(result) is Success:
        usage = _checked_usage(result.usage)
        return (
            Success(result.text, usage)
            if _valid_reply_text(result.text)
            else Failed("invalid-response", usage)
        )
    if type(result) is Refused:
        codes = {
            "live-off",
            "input-too-large",
            "busy-or-quota",
            "not-configured",
            "provider-refused",
            "quota",
        }
    elif type(result) is Failed:
        codes = {"timeout", "transport", "invalid-response", "provider-error"}
    else:
        return Failed("provider-error")
    if type(result.code) is not str or result.code not in codes:
        return Failed("provider-error")
    return replace(result, usage=_checked_usage(result.usage))


def _user_key(user):
    return str(user.pk)


def _quota(scope, key, limit, window, now):
    """Count a call in the rolling window, removing expired records."""
    CallRecord.objects.filter(
        scope=scope, key=key, created_at__lte=now - window
    ).delete()
    if CallRecord.objects.filter(scope=scope, key=key).count() >= limit:
        return False
    return CallRecord.objects.create(scope=scope, key=key, created_at=now)


def _reserve(user):
    """Atomically reserve quota and both in-flight slots, or return None.

    The reservation moment is taken once the slot locks are held. Returns the
    user slot, the deployment slot and the expiry they now hold, and the
    monotonic time of that moment, where the call's deadline starts, and both
    quota record IDs for completing metrics after the provider returns.
    """
    with transaction.atomic():
        user_slot, _ = CallSlot.objects.select_for_update().get_or_create(
            scope=USER_SCOPE,
            key=_user_key(user),
            defaults={"expires_at": timezone.now()},
        )
        deployment = list(
            CallSlot.objects.select_for_update()
            .filter(scope=DEPLOYMENT_SCOPE)
            .order_by("pk")
        )
        now, started = timezone.now(), time.monotonic()
        if user_slot.expires_at > now:
            return None
        if len(deployment) != DEPLOYMENT_IN_FLIGHT:
            return None
        free = [slot for slot in deployment if slot.expires_at <= now]
        if not free:
            return None
        user_record = _quota(
            USER_CALLS_SCOPE, _user_key(user), USER_CALLS, USER_WINDOW, now
        )
        if not user_record:
            transaction.set_rollback(True)
            return None
        deployment_record = _quota(
            DEPLOYMENT_CALLS_SCOPE, "all", DEPLOYMENT_CALLS, DEPLOYMENT_WINDOW, now
        )
        if not deployment_record:
            transaction.set_rollback(True)
            return None
        expires = now + timedelta(seconds=TOTAL_TIMEOUT + RELEASE_MARGIN)
        CallSlot.objects.filter(pk__in=[user_slot.pk, free[0].pk]).update(
            expires_at=expires
        )
        return (
            (user_slot, free[0], expires),
            started,
            (user_record.pk, deployment_record.pk),
        )


@sensitive_variables("result")
def _record_metrics(record_ids, result, elapsed_ms):
    """Update this call's two quota rows together; null means unavailable."""
    usage = result.usage or Usage()
    metrics = {name: getattr(usage, name) for name in TOKEN_FIELDS}
    with transaction.atomic():
        CallRecord.objects.filter(pk__in=record_ids).update(
            **metrics, elapsed_ms=elapsed_ms
        )


def _release(user_slot, deployment_slot, expires):
    """Free this call's two slots, unless a later call already holds them."""
    CallSlot.objects.filter(
        pk__in=[user_slot.pk, deployment_slot.pk], expires_at=expires
    ).update(expires_at=timezone.now())


def _endpoint():
    """Return the fixed HTTPS endpoint URL, or None when unconfigured."""
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
    return url


def _remaining(deadline):
    """Return the seconds left before `deadline`, or raise TimeoutError."""
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return left


class _ResponseTooLarge(Exception):
    """The response body passed RESPONSE_BYTES."""


@sensitive_variables("headers", "body", "received", "chunk", "response")
async def _exchange(url, headers, body, deadline):
    """POST `body` with aiohttp; return the status and capped body (the network step).

    The time left before `deadline` is the total timeout; certificates are
    verified, redirects are not followed and proxy variables are ignored.
    """
    timeout = aiohttp.ClientTimeout(total=_remaining(deadline))
    tls = ssl.create_default_context()
    tls.keylog_filename = None
    async with (
        aiohttp.ClientSession(
            timeout=timeout, trust_env=False, auto_decompress=False
        ) as session,
        session.post(
            url,
            data=body,
            headers=headers,
            allow_redirects=False,
            ssl=tls,
        ) as response,
    ):
        received = bytearray()
        async for chunk in response.content.iter_any():
            received += chunk
            if len(received) > RESPONSE_BYTES:
                raise _ResponseTooLarge
        return response.status, bytes(received)


class _DaemonExecutor(concurrent.futures.ThreadPoolExecutor):
    """Run each job, such as a name lookup, in its own daemon thread.

    A daemon thread is not joined at interpreter exit, so a hung lookup cannot
    delay a worker's shutdown; shutting the executor down never waits.
    """

    def submit(self, fn, /, *args, **kwargs):
        """Start `fn(*args, **kwargs)` in a new daemon thread; return its future."""
        future = concurrent.futures.Future()

        def work():
            if not future.set_running_or_notify_cancel():
                return
            try:
                result = fn(*args, **kwargs)
            except BaseException as error:  # noqa: BLE001 - handed to the awaiting call
                future.set_exception(error)
            else:
                future.set_result(result)

        threading.Thread(target=work, daemon=True).start()
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        """Do nothing: the daemon threads are never waited for."""


_LOOP_REPORTS = (
    (("task", "future"), "leftover-task"),
    (("asyncgen",), "asyncgen-close"),
    (("transport", "protocol"), "connection-error"),
)


def _report_loop_event(loop, context):
    """Log asyncio's report about the call's loop as a fixed code only.

    The code depends only on which keys `context` has: asyncio's message and
    exception can carry task, exception or operating-system text.
    """
    keys = [
        code for names, code in _LOOP_REPORTS if not context.keys().isdisjoint(names)
    ]
    logger.warning("LLM gateway loop report: %s", (keys or ["loop-error"])[0])


class _CallLoop(asyncio.EventLoop):
    """One call's event loop, which records every connection it opens."""

    def __init__(self):
        super().__init__()
        self.set_debug(False)
        self.transports = []
        self.set_default_executor(_DaemonExecutor())
        self.set_exception_handler(_report_loop_event)

    async def create_connection(self, *args, **kwargs):
        """Open a connection as asyncio does, recording its transports.

        For TLS, the socket transport below is recorded too: once aiohttp has
        closed a TLS transport twice, aborting it no longer reaches that socket.
        asyncio offers no public way to reach it, hence the private attributes;
        the unparsable-reply transport test fails if they change.
        """
        transport, protocol = await super().create_connection(*args, **kwargs)
        self.transports.append(transport)
        tls = getattr(transport, "_ssl_protocol", None)
        below = getattr(tls, "_transport", None)
        if isinstance(below, asyncio.BaseTransport):
            self.transports.append(below)
        return transport, protocol


def _run(awaitable):
    """Run `awaitable` on a new loop, leaving no connection or task behind.

    Unlike asyncio.run, closing the loop does not wait for a lookup's thread.
    """
    loop = _CallLoop()
    try:
        return loop.run_until_complete(awaitable)
    finally:
        try:
            _settle(loop)
        finally:
            loop.close()


def _settle(loop):
    """Cancel `loop`'s remaining work, then abort and close its connections.

    Leftover tasks and generators get CLEANUP_TIMEOUT in all, then are abandoned.
    """
    end = time.monotonic() + CLEANUP_TIMEOUT
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.wait(pending, timeout=CLEANUP_TIMEOUT))
    closing = {loop.create_task(loop.shutdown_asyncgens())}
    loop.run_until_complete(
        asyncio.wait(closing, timeout=max(0, end - time.monotonic()))
    )
    for task in pending:
        if task.done() and not task.cancelled():
            task.exception()  # retrieved, so asyncio does not report it
    for transport in loop.transports:
        try:
            transport.abort()
        except Exception:  # noqa: BLE001 - the others must still be aborted
            logger.warning("LLM gateway loop report: %s", "abort-failed")
    loop.run_until_complete(asyncio.sleep(0))  # one pass closes the aborted sockets


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


@sensitive_variables("body", "value", "raw_usage", "usage")
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
    if type(value) is not dict:
        return Failed("invalid-response")
    raw_usage = value.get("usage")
    usage = (
        _checked_usage(Usage(*(raw_usage.get(name) for name in TOKEN_FIELDS)))
        if type(raw_usage) is dict
        else None
    )
    return replace(_reply(value), usage=usage)


@sensitive_variables("value", "choices", "choice", "message", "refusal", "text")
def _reply(value):
    """Validate the first choice independently of optional usage metadata."""
    choices = value.get("choices")
    if type(choices) is not list or not choices or type(choices[0]) is not dict:
        return Failed("invalid-response")
    choice = choices[0]
    message = choice.get("message")
    if (
        type(message) is not dict
        or message.get("role", "assistant") != "assistant"
        or message.get("tool_calls") not in (None, [])
        or message.get("function_call") is not None
    ):
        return Failed("invalid-response")
    refusal = message.get("refusal")
    if refusal is not None:
        if type(refusal) is not str or not refusal:
            return Failed("invalid-response")
        return Refused("provider-refused")
    if choice.get("finish_reason") == "content_filter":
        return Refused("provider-refused")
    if choice.get("finish_reason") == "length":
        return Failed("invalid-response")
    text = message.get("content")
    if not _valid_reply_text(text):
        return Failed("invalid-response")
    return Success(text)


@sensitive_variables("api_key")
def configured():
    """Return the endpoint URL, model and API key, or None if any is unusable."""
    url = _endpoint()
    api_key = os.environ.get("SOC_LLM_API_KEY", "").strip()
    model = os.environ.get("SOC_LLM_MODEL", "").strip()
    usable_key = api_key.isascii() and api_key.isprintable()
    if url is None or not model or not api_key or not usable_key:
        return None
    return url, model, api_key


@sensitive_variables("config", "api_key", "headers", "body", "instructions", "data")
def _transport(instructions, data, deadline):
    """Send one request without redirects or retries, returning a result."""
    if not settings.SOC_LLM_LIVE:
        return Refused("live-off")
    config = configured()
    if config is None:
        return Refused("not-configured")
    url, model, api_key = config
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    try:
        body = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": data},
                ],
                "temperature": 0,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        status, body = _run(_exchange(url, headers, body, deadline))
    except TimeoutError:  # asyncio's and aiohttp's timeouts included
        return Failed("timeout")
    except _ResponseTooLarge:
        return Failed("invalid-response")
    except Exception:  # noqa: BLE001 - a fixed code, never exception text
        # aiohttp client errors (connection, TLS, malformed HTTP, incomplete
        # body), OSError, ValueError (such as an unencodable host name) and
        # every other Exception.
        return Failed("transport")
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
    reserving, recording metrics or releasing is raised for the feature's own
    error handling.
    """
    if provider is None and not settings.SOC_LLM_LIVE:
        logger.info("LLM gateway outcome: %s", "live-off")
        return Refused("live-off")
    if len(instructions) + len(data) > INPUT_LIMIT:
        return Refused("input-too-large")
    reserved = _reserve(user)
    if reserved is None:
        return Refused("busy-or-quota")
    slots, started, record_ids = reserved
    deadline = started + TOTAL_TIMEOUT
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
        result = _checked_result(result)
        elapsed_ms = int(max(0, time.monotonic() - started) * 1000)
        _record_metrics(record_ids, result, elapsed_ms)
        code = "success" if isinstance(result, Success) else result.code
        logger.info("LLM gateway outcome: %s", code)
        return result
    finally:
        _release(*slots)
