"""The gateway's HTTPS transport against a real local TLS server (no provider)."""

import json
import socket
import threading
import time

import pytest

from ai import gateway
from ai.gateway import Failed, Refused, Success, complete

from .tls_server import Server, make_certificate, respond, trickle

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
    monkeypatch.setattr(gateway, "TOTAL_TIMEOUT", 1)


def http(status, body=b"", headers=b""):
    head = f"HTTP/1.1 {status} Synthetic\r\nContent-Length: {len(body)}\r\n"
    return head.encode() + headers + b"\r\n" + body


def text_reply(text):
    return http(200, json.dumps({"text": text}, ensure_ascii=False).encode())


def timed(user):
    started = time.monotonic()
    result = complete(user, "synthetic instructions", '{"criteria": []}')
    return result, time.monotonic() - started


def test_one_post_carries_separate_parts_and_bearer_key(user, serve):
    server = serve(respond(text_reply("ok")))
    assert complete(user, "synthetic instructions", '{"criteria": []}') == Success("ok")
    (request,) = server.requests
    head, _, body = request.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0] == b"POST /llm HTTP/1.1"
    assert f"Authorization: Bearer {KEY}".encode() in lines
    assert KEY.encode() not in body
    assert json.loads(body) == {
        "model": "synthetic-model",
        "instructions": "synthetic instructions",
        "data": '{"criteria": []}',
    }


@pytest.mark.ac("RND-8.5")
def test_a_20000_non_bmp_character_text_is_accepted(user, serve):
    serve(respond(text_reply("\U0001f600" * 20000)))
    assert complete(user, "", "{}") == Success("\U0001f600" * 20000)


def test_a_chunked_reply_is_decoded(user, serve):
    body = json.dumps({"text": "ok"}).encode()
    chunked = (
        b"HTTP/1.1 200 Synthetic\r\nTransfer-Encoding: chunked\r\n\r\n"
        + f"{len(body):x}\r\n".encode()
        + body
        + b"\r\n0\r\n\r\n"
    )
    serve(respond(chunked))
    assert complete(user, "", "{}") == Success("ok")


@pytest.mark.parametrize(
    ("prefix", "piece"),
    [
        (b"", b"H"),
        (b"HTTP/1.1 200 Synthetic\r\n", b"X-Synthetic: 1\r\n"),
        (b"HTTP/1.1 200 Synthetic\r\nContent-Length: 100000\r\n\r\n", b"x"),
    ],
    ids=["status-line", "headers", "body"],
)
@pytest.mark.ac("RND-8.4")
def test_a_trickling_server_is_cut_off_at_the_deadline(
    user, serve, short_deadline, prefix, piece
):
    serve(trickle(prefix, piece, 0.2, 4))
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 1.8


@pytest.mark.ac("RND-8.4")
def test_slow_name_resolution_is_cut_off_at_the_deadline(
    user, serve, short_deadline, monkeypatch
):
    serve(respond(text_reply("ok")))
    original = socket.getaddrinfo

    def slow(*args, **kwargs):
        time.sleep(3)
        return original(*args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    result, elapsed = timed(user)
    assert result == Failed("timeout")
    assert elapsed < 1.8


@pytest.mark.ac("RND-8.4")
def test_a_stalled_tls_handshake_is_cut_off_at_the_deadline(
    user, live, short_deadline, monkeypatch
):
    listener = socket.create_server(("127.0.0.1", 0))
    accepted = []
    threading.Thread(
        target=lambda: accepted.append(listener.accept()), daemon=True
    ).start()
    monkeypatch.setenv(
        "SOC_LLM_ENDPOINT", f"https://127.0.0.1:{listener.getsockname()[1]}/llm"
    )
    try:
        result, elapsed = timed(user)
    finally:
        listener.close()
    assert result == Failed("timeout")
    assert elapsed < 1.8


def test_a_refused_connection_is_a_transport_failure(user, live, monkeypatch):
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    monkeypatch.setenv("SOC_LLM_ENDPOINT", f"https://127.0.0.1:{port}/llm")
    assert complete(user, "", "{}") == Failed("transport")


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


def test_a_redirect_is_not_followed(user, serve):
    server = serve(respond(http(302, headers=b"Location: https://127.0.0.1:9/\r\n")))
    assert complete(user, "", "{}") == Failed("transport")
    assert len(server.requests) == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, Refused("provider-refused")),
        (401, Refused("provider-refused")),
        (403, Refused("provider-refused")),
        (429, Refused("quota")),
        (500, Failed("transport")),
        (503, Failed("transport")),
    ],
)
def test_status_codes_map_to_fixed_outcomes(user, serve, status, expected):
    serve(respond(http(status, b"synthetic provider body")))
    assert complete(user, "", "{}") == expected


def test_a_refusal_object_is_a_refusal(user, serve):
    serve(respond(http(200, b'{"refusal": "synthetic"}')))
    assert complete(user, "", "{}") == Refused("provider-refused")


@pytest.mark.parametrize(
    "body",
    [
        b'{"text": "a", "text": "b"}',
        b'{"text": "\\ud800"}',
        b'{"text": "ok", "extra": 1}',
        b'{"text": NaN}',
        b'{"text": "' + b"a" * 20001 + b'"}',
        b"[]",
        b"\xff",
    ],
    ids=[
        "repeated-text",
        "surrogate",
        "extra-key",
        "nan",
        "over-limit",
        "array",
        "not-utf8",
    ],
)
def test_an_invalid_envelope_is_an_invalid_response(user, serve, body):
    serve(respond(http(200, body)))
    assert complete(user, "", "{}") == Failed("invalid-response")


def test_a_response_over_the_byte_cap_is_an_invalid_response(user, serve):
    serve(respond(http(200, b"x" * (gateway.RESPONSE_BYTES + 1))))
    assert complete(user, "", "{}") == Failed("invalid-response")
