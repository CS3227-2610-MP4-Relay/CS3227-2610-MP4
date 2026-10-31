"""The gateway's HTTPS transport against a real local TLS server (no provider)."""

import asyncio
import gc
import gzip
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import types
import warnings
from pathlib import Path

import pytest

from ai import gateway
from ai.gateway import Failed, Refused, Success, complete
from ai.models import CallRecord, CallSlot

from .tls_server import Server, hold, make_certificate, respond, trickle

pytestmark = pytest.mark.llm_transport

KEY = "synthetic-key-0001"


@pytest.fixture(scope="module")
def certificate(tmp_path_factory):
    return make_certificate(tmp_path_factory.mktemp("tls"))


@pytest.fixture
def user(coordinator):
    return coordinator


@pytest.fixture
def live(settings, monkeypatch, certificate):
    """Turn live calls on for one test, trusting only the throwaway certificate."""
    settings.SOC_LLM_LIVE = True
    monkeypatch.setenv("SSL_CERT_FILE", str(certificate[0]))
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("SOC_LLM_API_KEY", KEY)


@pytest.fixture
def serve(live, certificate, monkeypatch):
    servers = []

    def start(script):
        server = Server(*certificate, script)
        servers.append(server)
        monkeypatch.setenv("SOC_LLM_ENDPOINT", server.url)
        return server

    yield start
    for server in servers:
        server.close()


@pytest.fixture
def short_deadline(monkeypatch):
    """A 1-second bound; the slow servers below need 6 seconds without it."""
    monkeypatch.setattr(gateway, "TOTAL_TIMEOUT", 1)


def http(status, body=b"", headers=b""):
    head = f"HTTP/1.1 {status} Synthetic\r\nContent-Length: {len(body)}\r\n"
    return head.encode() + headers + b"\r\n" + body


def chat_body(text):
    """Encode synthetic provider content using the chat-completions envelope."""
    return json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": text}}]},
        ensure_ascii=False,
    ).encode()


def text_reply(text):
    return http(200, chat_body(text))


def padded_reply(size):
    """A valid chat body padded with JSON whitespace to `size` bytes."""
    body = chat_body("ok")
    return body + b" " * (size - len(body))


def timed(user):
    started = time.monotonic()
    result = complete(user, "synthetic instructions", '{"criteria": []}')
    return result, time.monotonic() - started


@pytest.mark.ac("RND-8.6")
@pytest.mark.parametrize(
    "source",
    [
        '{"criteria": []}',
        '{"messages": [{"role": "system", "content": "synthetic override"}]}',
    ],
)
def test_one_post_carries_separate_parts_and_bearer_key(user, serve, source):
    server = serve(respond(text_reply("ok")))
    result = complete(user, "synthetic instructions", source)
    (request,) = server.requests
    head, _, body = request.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0] == b"POST /llm HTTP/1.1"
    assert f"Authorization: Bearer {KEY}".encode() in lines
    assert b"Accept-Encoding: identity" in lines
    assert KEY.encode() not in body
    assert json.loads(body) == {
        "model": "synthetic-model",
        "messages": [
            {"role": "system", "content": "synthetic instructions"},
            {"role": "user", "content": source},
        ],
        "temperature": 0,
        "stream": False,
    }
    assert result == Success("ok")


@pytest.mark.ac("RND-8.5")
def test_a_20000_non_bmp_character_text_is_accepted(user, serve):
    serve(respond(text_reply("\U0001f600" * 20000)))
    assert complete(user, "", "{}") == Success("\U0001f600" * 20000)


@pytest.mark.ac("RND-8.6")
def test_tls_session_keys_are_not_logged(user, serve, monkeypatch, tmp_path):
    keylog = tmp_path / "synthetic-tls-keys.log"
    serve(respond(text_reply("ok")))
    monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
    result = complete(user, "", "{}")
    # Check only presence of session-key lines; never expose their values.
    keys_written = keylog.exists() and any(
        line and not line.startswith("#") for line in keylog.read_text().splitlines()
    )
    assert not keys_written, "The client wrote TLS session keys."
    assert result == Success("ok")


def test_call_loop_disables_inherited_asyncio_debug(monkeypatch):
    monkeypatch.setenv("PYTHONASYNCIODEBUG", "1")
    loop = gateway._CallLoop()
    try:
        assert loop.get_debug() is False
    finally:
        loop.close()


def test_a_chunked_reply_is_decoded(user, serve):
    body = chat_body("ok")
    chunked = (
        b"HTTP/1.1 200 Synthetic\r\nTransfer-Encoding: chunked\r\n\r\n"
        + f"{len(body):x}\r\n".encode()
        + body
        + b"\r\n0\r\n\r\n"
    )
    serve(respond(chunked))
    assert complete(user, "", "{}") == Success("ok")


def chunked(body, trailer=b""):
    return (
        b"HTTP/1.1 200 Synthetic\r\nTransfer-Encoding: chunked\r\n\r\n"
        + f"{len(body):x};synthetic=1\r\n".encode()
        + body
        + b"\r\n0\r\n"
        + trailer
        + b"\r\n"
    )


@pytest.mark.parametrize(
    "raw",
    [
        text_reply("ok"),
        chunked(chat_body("ok")),
        chunked(chat_body("ok"), b"X-Synthetic: 1\r\n"),
    ],
    ids=["content-length", "chunked", "chunked-trailer"],
)
def test_a_complete_reply_on_a_held_connection_is_not_a_timeout(
    user, serve, short_deadline, raw
):
    serve(hold(raw, 6))
    result, elapsed = timed(user)
    assert result == Success("ok")
    assert elapsed < 1


@pytest.mark.parametrize(
    "raw",
    [
        http(200, chat_body("ok"))[:-1],
        chunked(chat_body("ok"))[:-2],
    ],
    ids=["content-length", "chunked"],
)
@pytest.mark.ac("RND-8.4")
def test_an_incomplete_reply_on_a_held_connection_times_out(
    user, serve, short_deadline, raw
):
    serve(hold(raw, 6))
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 3


@pytest.mark.ac("RND-8.4")
def test_a_server_that_never_answers_times_out(user, serve, short_deadline):
    server = serve(hold(b"", 6))
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 3
    assert len(server.requests) == 1
    assert CallRecord.objects.filter(scope=gateway.USER_CALLS_SCOPE).count() == 1
    assert CallRecord.objects.filter(scope=gateway.DEPLOYMENT_CALLS_SCOPE).count() == 1
    assert not CallSlot.objects.filter(expires_at__gt=gateway.timezone.now()).exists()


@pytest.mark.ac("RND-8.4")
def test_a_hung_name_lookup_does_not_extend_the_deadline(
    user, serve, short_deadline, monkeypatch
):
    """The call's own loop is closed without waiting for the lookup's thread."""
    server = serve(respond(text_reply("ok")))
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://localhost:{server.port}/llm")
    original = socket.getaddrinfo

    def slow(*args, **kwargs):
        time.sleep(6)
        return original(*args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 3


@pytest.mark.ac("RND-8.4")
def test_a_trickling_body_is_cut_off_at_the_total_deadline(user, serve, short_deadline):
    """Each byte arrives in time, so only a whole-request bound stops it."""
    prefix = b"HTTP/1.1 200 Synthetic\r\nContent-Length: 100000\r\n\r\n"
    serve(trickle(prefix, b" ", 0.2, 6))
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 3


def client_sockets(port):
    """Count this process's open TCP sockets connected to 127.0.0.1:`port`.

    Returns None where open descriptors cannot be listed (no /dev/fd).
    """
    if not os.path.isdir("/dev/fd"):
        return None
    count = 0
    for name in os.listdir("/dev/fd"):
        try:
            with socket.fromfd(int(name), socket.AF_INET, socket.SOCK_STREAM) as sock:
                count += sock.getpeername() == ("127.0.0.1", port)
        except OSError:
            continue
    return count


@pytest.fixture
def no_gc():
    """Pause automatic garbage collection, so only the call itself closes sockets."""
    gc.collect()
    gc.disable()
    yield
    gc.enable()


def collected_resource_warnings():
    """Collect garbage and return the ResourceWarnings it reports."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gc.collect()
    return [w for w in caught if issubclass(w.category, ResourceWarning)]


@pytest.mark.parametrize(
    ("script", "expected"),
    [
        (hold(b"", 6), Failed("timeout")),
        (
            trickle(
                b"HTTP/1.1 200 Synthetic\r\nContent-Length: 100000\r\n\r\n",
                b" ",
                0.2,
                6,
            ),
            Failed("timeout"),
        ),
        (hold(text_reply("ok"), 6), Success("ok")),
        (
            hold(http(200, padded_reply(gateway.RESPONSE_BYTES + 1)), 6),
            Failed("invalid-response"),
        ),
        (hold(b"HELLO\r\n\r\n", 6), Failed("transport")),
    ],
    ids=["silent", "trickle", "success", "oversized", "unparsable"],
)
def test_no_connection_is_left_open_after_the_call(
    user, serve, short_deadline, no_gc, script, expected
):
    """The server holds every connection open, so only the client can close it."""
    server = serve(script)
    result, elapsed = timed(user)
    assert result == expected
    assert elapsed < 3
    assert client_sockets(server.port) in {0, None}  # None: not countable here
    assert collected_resource_warnings() == []


def test_a_hung_name_lookup_leaves_no_thread_that_delays_exit(
    user, serve, short_deadline, monkeypatch
):
    server = serve(respond(text_reply("ok")))
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://localhost:{server.port}/llm")
    original = socket.getaddrinfo

    def slow(*args, **kwargs):
        time.sleep(6)
        return original(*args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    before = set(threading.enumerate())
    assert timed(user)[0] == Failed("timeout")
    started = [t for t in threading.enumerate() if t not in before and t.is_alive()]
    assert started, "the hung lookup's thread should still be running"
    assert all(thread.daemon for thread in started)


def test_a_process_with_a_hung_name_lookup_exits_promptly():
    """The helper's lookup hangs for 20 seconds; exit must not wait for it."""
    src = Path(__file__).resolve().parents[2]
    started = time.monotonic()
    finished = subprocess.run(
        [sys.executable, "-m", "ai.tests.hung_lookup"],
        cwd=src,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    elapsed = time.monotonic() - started
    assert finished.returncode == 0, finished.stderr[-2000:]
    assert finished.stdout.strip() == "timeout"
    assert elapsed < 10


def test_the_call_cancels_its_leftover_tasks():
    leftovers = []

    async def work():
        leftovers.append(asyncio.get_running_loop().create_task(asyncio.sleep(10)))
        return "done"

    assert gateway._run(work()) == "done"
    assert leftovers[0].cancelled()


def test_a_task_ignoring_cancellation_delays_the_call_by_at_most_the_bound():
    async def stubborn():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(10)

    async def work():
        asyncio.get_running_loop().create_task(stubborn())
        await asyncio.sleep(0)
        return "done"

    started = time.monotonic()
    assert gateway._run(work()) == "done"
    assert time.monotonic() - started < gateway.CLEANUP_TIMEOUT + 0.5
    gc.collect()  # the abandoned task is reported now, not in a later test


def test_the_call_closes_its_suspended_async_generators():
    closed = []
    suspended = []

    async def numbers():
        try:
            yield 1
            yield 2
        finally:
            closed.append(True)

    async def work():
        generator = numbers()
        suspended.append(generator)
        await anext(generator)
        return "done"

    assert gateway._run(work()) == "done"
    assert closed == [True]


def test_a_leftover_task_failing_on_cancellation_is_not_reported(caplog):
    """Its exception is retrieved after the wait, so asyncio reports nothing."""

    async def failing_on_cancel():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise RuntimeError("synthetic failure while cancelled") from None

    async def work():
        asyncio.get_running_loop().create_task(failing_on_cancel())
        await asyncio.sleep(0)
        return "done"

    gc.collect()  # earlier tests' leftovers are reported now, not below
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    assert gateway._run(work()) == "done"
    gc.collect()
    reports = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert reports == []


def test_leftover_tasks_log_no_exception_or_task_text(caplog):
    """asyncio's own reports would name the task and repeat the exception."""

    async def failing_secret_task():
        await asyncio.sleep(0.01)
        raise RuntimeError(f"synthetic {KEY} secret-data")

    async def stubborn_secret_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(10)

    async def failed_early_secret_task():
        raise RuntimeError(f"synthetic {KEY} early-secret-data")

    async def work():
        loop = asyncio.get_running_loop()
        loop.create_task(failed_early_secret_task())
        loop.create_task(stubborn_secret_task())
        loop.create_task(failing_secret_task())
        await asyncio.sleep(0.05)  # failing_secret_task fails first
        return "done"

    caplog.set_level(logging.DEBUG)
    assert gateway._run(work()) == "done"
    gc.collect()
    logged = repr(
        [(r.getMessage(), r.exc_info, r.exc_text, r.args) for r in caplog.records]
    )
    for secret in (KEY, "secret-data", "secret_task", "RuntimeError"):
        assert secret not in logged
    report = "LLM gateway loop report: leftover-task"
    assert report in [r.getMessage() for r in caplog.records]


@pytest.mark.parametrize("stubborn_task", [False, True])
def test_a_generator_ignoring_cancellation_does_not_hold_the_call(stubborn_task):
    async def stubborn():
        try:
            yield 1
        finally:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                await asyncio.sleep(3)

    async def work(generator):
        await anext(generator)
        if stubborn_task:  # the generator then gets only what is left of the bound
            await anext(other := stubborn())
            asyncio.ensure_future(other.aclose())
        return "done"

    generator = stubborn()  # kept, so the loop must close it
    started = time.monotonic()
    assert gateway._run(work(generator)) == "done"
    assert time.monotonic() - started < gateway.CLEANUP_TIMEOUT + 0.5
    del generator
    gc.collect()  # the abandoned tasks are reported now, not in a later test


def test_loop_reports_log_a_code_chosen_only_by_the_kind_of_object(caplog):
    caplog.set_level(logging.DEBUG)
    error = RuntimeError(f"synthetic {KEY} os-error-text")
    for key in ("task", "future", "asyncgen", "transport", "protocol", "handle"):
        gateway._report_loop_event(
            None, {"message": str(error), "exception": error, key: 1}
        )
    codes = ["leftover-task"] * 2 + ["asyncgen-close"] + ["connection-error"] * 2
    expected = [(f"LLM gateway loop report: {c}", None) for c in [*codes, "loop-error"]]
    assert [(r.getMessage(), r.exc_info) for r in caplog.records] == expected


def test_one_failing_abort_skips_no_other_transport(monkeypatch, caplog):
    aborted = []
    below = types.SimpleNamespace(abort=lambda: aborted.append("not a transport"))
    tls = types.SimpleNamespace(_transport=below)
    first = types.SimpleNamespace(abort=lambda: 1 / 0, _ssl_protocol=tls)
    second = types.SimpleNamespace(abort=lambda: aborted.append("second"))
    connections = iter([first, second])

    async def connect(self, *args, **kwargs):
        return next(connections), None

    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", connect)
    loop = gateway._CallLoop()
    for _ in range(2):
        loop.run_until_complete(loop.create_connection())
    gateway._settle(loop)
    loop.close()
    assert aborted == ["second"]
    assert caplog.messages == ["LLM gateway loop report: abort-failed"]


def test_the_deadline_passed_in_bounds_the_request(serve):
    """The time left from reservation, not a fresh TOTAL_TIMEOUT, is the bound."""
    serve(hold(b"", 6))
    started = time.monotonic()
    result = gateway._transport("", "{}", started + 0.5)
    assert result == Failed("timeout")
    assert time.monotonic() - started < 2


def test_a_passed_deadline_sends_nothing(serve):
    server = serve(respond(text_reply("ok")))
    assert gateway._transport("", "{}", time.monotonic() - 1) == Failed("timeout")
    time.sleep(0.2)
    assert server.requests == []


def test_a_refused_connection_is_a_transport_failure(user, live, monkeypatch):
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://127.0.0.1:{port}/llm")
    assert complete(user, "", "{}") == Failed("transport")


def test_a_name_the_resolver_cannot_encode_is_a_transport_failure(
    user, live, monkeypatch
):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://{'a' * 64}.invalid/llm")
    assert complete(user, "", "{}") == Failed("transport")


def test_any_name_lookup_error_is_a_transport_failure(user, serve, monkeypatch):
    server = serve(respond(text_reply("ok")))
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://localhost:{server.port}/llm")

    def broken(*args, **kwargs):
        raise RuntimeError("synthetic resolver failure")

    monkeypatch.setattr(socket, "getaddrinfo", broken)
    assert complete(user, "", "{}") == Failed("transport")


def test_an_unexpected_client_error_is_a_transport_failure_and_not_logged(
    user, serve, monkeypatch, caplog
):
    serve(respond(text_reply("ok")))

    async def broken(*args, **kwargs):
        raise RuntimeError(f"synthetic {KEY} secret-instructions secret-data")

    monkeypatch.setattr(gateway.aiohttp.ClientResponse, "start", broken)
    caplog.set_level(logging.DEBUG)
    result = complete(user, "secret-instructions", '{"criteria": "secret-data"}')
    assert result == Failed("transport")
    logged = repr([(r.getMessage(), r.exc_text, r.args) for r in caplog.records])
    for secret in (KEY, "secret-instructions", "secret-data"):
        assert secret not in logged


def test_an_untrusted_certificate_is_a_transport_failure(user, serve, monkeypatch):
    serve(respond(text_reply("ok")))
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/synthetic.pem")
    assert complete(user, "", "{}") == Failed("transport")


@pytest.mark.parametrize(
    "raw",
    [
        b"HELLO\r\n\r\n",
        b"HTTP/1.1 200 Synthetic\r\nX-Long: " + b"a" * 70000 + b"\r\n\r\n",
        b"HTTP/1.1 200 Synthetic\r\nContent-Length: 100\r\n\r\n" + b"{}",
    ],
    ids=["bad-status-line", "long-header-line", "short-body"],
)
def test_a_malformed_http_response_is_a_transport_failure(user, serve, raw):
    serve(respond(raw))
    assert complete(user, "", "{}") == Failed("transport")


def test_a_trusted_certificate_for_another_name_is_a_transport_failure(
    user, live, tmp_path, monkeypatch
):
    cert, key = make_certificate(tmp_path, "DNS:synthetic.invalid")
    server = Server(cert, key, respond(text_reply("ok")))
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    monkeypatch.setenv("SOC_LLM_ENDPOINT", server.url)
    try:
        assert complete(user, "", "{}") == Failed("transport")
    finally:
        server.close()
    assert server.requests == []


def test_a_redirect_is_not_followed(user, serve):
    server = serve(
        respond(http(302, headers=b"Location: /llm-moved\r\nConnection: close\r\n"))
    )
    assert complete(user, "", "{}") == Failed("transport")
    assert len(server.requests) == 1


def test_proxy_variables_are_ignored(user, serve, monkeypatch):
    serve(respond(text_reply("ok")))
    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    assert complete(user, "", "{}") == Success("ok")


def test_a_compressed_body_is_not_decompressed(user, serve):
    body = gzip.compress(chat_body("ok"))
    serve(respond(http(200, body, b"Content-Encoding: gzip\r\n")))
    assert complete(user, "", "{}") == Failed("invalid-response")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, Refused("provider-refused")),
        (401, Refused("provider-refused")),
        (403, Refused("provider-refused")),
        (429, Refused("quota")),
        (201, Failed("invalid-response")),
        (404, Failed("transport")),
        (500, Failed("transport")),
        (503, Failed("transport")),
    ],
)
@pytest.mark.ac("RND-8.4")
def test_status_codes_map_to_fixed_outcomes(user, serve, status, expected):
    server = serve(respond(http(status, b"synthetic provider body")))
    assert complete(user, "", "{}") == expected
    assert len(server.requests) == 1
    assert CallRecord.objects.filter(scope=gateway.USER_CALLS_SCOPE).count() == 1
    assert CallRecord.objects.filter(scope=gateway.DEPLOYMENT_CALLS_SCOPE).count() == 1
    assert not CallSlot.objects.filter(expires_at__gt=gateway.timezone.now()).exists()


@pytest.mark.ac("RND-8.4")
def test_a_chat_refusal_is_a_refusal(user, serve, caplog):
    caplog.set_level(logging.INFO, logger="ai.gateway")
    body = json.dumps(
        {"choices": [{"message": {"refusal": "synthetic refusal text"}}]}
    ).encode()
    serve(respond(http(200, body)))
    assert complete(user, "", "{}") == Refused("provider-refused")
    assert [record.getMessage() for record in caplog.records] == [
        "LLM gateway outcome: provider-refused"
    ]


@pytest.mark.parametrize(
    "body",
    [
        b'{"choices": [{"message": {"content": "a", "content": "b"}}]}',
        b'{"choices": [{"message": {"content": "\\ud800"}}]}',
        b'{"text": "legacy"}',
        b'{"choices": [{"message": {"content": NaN}}]}',
        chat_body("a" * 20001),
        b"[]",
        b"\xff",
    ],
    ids=[
        "repeated-text",
        "surrogate",
        "legacy-envelope",
        "nan",
        "over-limit",
        "array",
        "not-utf8",
    ],
)
def test_an_invalid_envelope_is_an_invalid_response(user, serve, body):
    serve(respond(http(200, body)))
    assert complete(user, "", "{}") == Failed("invalid-response")


@pytest.mark.ac("RND-8.5")
@pytest.mark.parametrize("offset", [-1, 0])
def test_a_body_at_or_below_the_byte_cap_is_accepted(user, serve, offset):
    serve(respond(http(200, padded_reply(gateway.RESPONSE_BYTES + offset))))
    assert complete(user, "", "{}") == Success("ok")


def test_a_body_over_the_byte_cap_is_an_invalid_response(user, serve):
    serve(respond(http(200, padded_reply(gateway.RESPONSE_BYTES + 1))))
    assert complete(user, "", "{}") == Failed("invalid-response")


def test_a_chunked_body_over_the_byte_cap_is_an_invalid_response(user, serve):
    """Many small chunks, with no Content-Length to check in advance."""
    body = padded_reply(gateway.RESPONSE_BYTES + 1)
    pieces = [body[i : i + 1000] for i in range(0, len(body), 1000)]
    head = b"HTTP/1.1 200 Synthetic\r\nTransfer-Encoding: chunked\r\n\r\n"
    chunks = b"".join(f"{len(p):x}\r\n".encode() + p + b"\r\n" for p in pieces)
    serve(respond(head + chunks + b"0\r\n\r\n"))
    assert complete(user, "", "{}") == Failed("invalid-response")
