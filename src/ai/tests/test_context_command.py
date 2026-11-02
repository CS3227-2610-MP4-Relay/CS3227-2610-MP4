"""Offline bounded operator execution and safe optional response inspection."""

import io
import json
from dataclasses import replace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ai import context_comparison as comparison
from ai import gateway
from ai.management.commands import compare_context as command
from rounds.tests.test_result_services import snapshot

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.ac("CTX-1.1", "CTX-1.3", "CTX-1.4", "CTX-1.5", "CTX-1.7"),
]
REVISION = "a" * 40


@pytest.fixture
def operator(coordinator, settings, monkeypatch):
    settings.SOC_LLM_LIVE = True
    for name, value in {
        "ENDPOINT": "https://provider.invalid/v1/chat/completions",
        "MODEL": "synthetic",
        "API_KEY": "synthetic-key",
    }.items():
        monkeypatch.setenv("SOC_LLM_" + name, value)
    return coordinator


@pytest.mark.parametrize(
    "invalid",
    [
        "flag",
        "off",
        "user",
        "revision",
        "key",
        "model",
        "endpoint",
        "corpus",
        "duplicate",
        "oversize",
    ],
)
def test_preflight_denials_make_zero_calls(operator, invalid, settings, monkeypatch):
    calls = []
    monkeypatch.setattr(gateway, "complete", lambda *args: calls.append(args))
    options = {
        "live": True,
        "user_id": operator.pk,
        "revision": REVISION,
        "show_responses": True,
    }
    if invalid == "flag":
        options["live"] = False
    elif invalid == "off":
        settings.SOC_LLM_LIVE = False
    elif invalid == "user":
        options["user_id"] += 1
    elif invalid == "revision":
        options["revision"] = "bad"
    elif invalid in {"key", "model", "endpoint"}:
        monkeypatch.delenv(
            "SOC_LLM_" + ("API_KEY" if invalid == "key" else invalid.upper())
        )
    else:
        cases = comparison.corpus()
        if invalid == "corpus":
            cases = ()
        elif invalid == "duplicate":
            cases = (cases[0],) * 8
        else:
            cases = (replace(cases[0], data="x" * 8001), *cases[1:])
        monkeypatch.setattr(comparison, "corpus", lambda: cases)
    with pytest.raises(CommandError, match="preflight refused"):
        call_command("compare_context", **options)
    assert calls == []


@pytest.mark.parametrize(
    "show,interrupt", [(False, False), (True, False), (True, True)]
)
def test_fixed_calls_metrics_output_and_interruption(
    operator, monkeypatch, make_round, show, interrupt
):
    class Terminal(io.StringIO):
        def isatty(self):
            return True

    output, errors, calls = io.StringIO(), Terminal(), []
    cases = comparison.corpus()
    monkeypatch.setattr(
        gateway, "INPUT_LIMIT", max(len(c.instructions) + len(c.data) for c in cases)
    )
    make_round()
    before = snapshot()
    ticks = iter(range(16))
    monkeypatch.setattr(command.time, "monotonic", lambda: next(ticks))
    replies = [
        gateway.Success("untrusted\n\x1b[31m\u202eé"),
        gateway.Refused("provider-refused"),
        gateway.Failed("timeout"),
        gateway.Success('{"drafts":[]}', gateway.Usage(0, 2, 2)),
    ]

    def complete(user, instructions, data):
        calls.append((user.pk, instructions, data))
        if interrupt and len(calls) == 2:
            raise RuntimeError("private-exception")
        return (
            replies[len(calls) - 1]
            if len(calls) <= 4
            else gateway.Success('{"questions":[]}')
        )

    monkeypatch.setattr(gateway, "complete", complete)
    options = {
        "live": True,
        "user_id": operator.pk,
        "revision": REVISION,
        "show_responses": show,
        "stdout": output,
        "stderr": errors,
        "force_color": True,
    }
    if interrupt:
        with pytest.raises(CommandError, match="interrupted"):
            call_command("compare_context", **options)
    else:
        call_command("compare_context", **options)
    report = json.loads(output.getvalue())
    assert calls == [
        (operator.pk, c.instructions, c.data) for c in cases[: 2 if interrupt else 8]
    ]
    assert (
        report["revision"] == REVISION
        and report["corpus_version"] == comparison.CORPUS_VERSION
    )
    rows = report["cases"]
    assert len(rows) == 8 and report["invocations"] == len(calls)
    assert rows[0]["schema_accepted"] is False and rows[0]["command_elapsed_ms"] == 1000
    if interrupt:
        assert rows[1]["status"] == "failed" and rows[1]["command_elapsed_ms"] is None
        assert all(
            r["status"] == "unattempted" and r["command_elapsed_ms"] is None
            for r in rows[2:]
        )
    else:
        assert [r["status"] for r in rows[1:3]] == ["refused", "failed"]
        assert rows[3]["accepted_items"] == 0 and rows[3]["prompt_tokens"] == 0
        assert all(r["command_elapsed_ms"] == 1000 for r in rows)
    expected = [
        (cases[i].id, replies[i].text if i < 4 else '{"questions":[]}')
        for i in ([0] if interrupt else [0, 3, 4, 5, 6, 7])
    ]
    assert [
        (r["id"], r["response"])
        for r in map(json.loads, errors.getvalue().splitlines())
    ] == (expected if show else [])
    assert errors.getvalue().isascii() and "\x1b" not in errors.getvalue()
    assert all(
        set(r) == {"id", "response"}
        for r in map(json.loads, errors.getvalue().splitlines())
    )
    assert "untrusted" not in output.getvalue()
    assert (
        "private" not in output.getvalue() and "synthetic-key" not in output.getvalue()
    )
    assert all(c.data not in output.getvalue() for c in cases)
    assert snapshot() == before
