"""Offline operator command preflight and bounded orchestration."""

import io
import json

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from ai import drafting, evaluation, gateway
from ai.management.commands.evaluate_injection import Command
from rounds.tests.test_result_services import snapshot

pytestmark = [pytest.mark.django_db, pytest.mark.ac("SEC-INJ-1.1", "SEC-INJ-1.4")]
REVISION = "a" * 40


@pytest.fixture
def operator(monkeypatch, settings, coordinator):
    settings.SOC_LLM_LIVE = True
    for key, value in {
        "ENDPOINT": "https://provider.invalid/v1/chat/completions",
        "MODEL": "synthetic-model",
        "API_KEY": "synthetic-key",
    }.items():
        monkeypatch.setenv("SOC_LLM_" + key, value)
    return coordinator


@pytest.mark.parametrize(
    "invalid", ["flag", "user", "revision", "config", "endpoint", "off", "corpus"]
)
def test_invalid_preflight_makes_no_call(operator, invalid, monkeypatch, settings):
    calls = []
    monkeypatch.setattr(gateway, "complete", lambda *args: calls.append(args))
    options = {"live": True, "user_id": operator.pk, "revision": REVISION}
    if invalid == "flag":
        options["live"] = False
    elif invalid == "user":
        options["user_id"] = operator.pk + 1
    elif invalid == "revision":
        options["revision"] = "not-a-revision"
    elif invalid == "config":
        monkeypatch.delenv("SOC_LLM_API_KEY")
    elif invalid == "endpoint":
        monkeypatch.setenv("SOC_LLM_ENDPOINT", "http://provider.invalid")
    elif invalid == "off":
        settings.SOC_LLM_LIVE = False
    else:
        monkeypatch.setattr(evaluation, "corpus", lambda: ())
    with pytest.raises(CommandError, match="preflight refused"):
        call_command("evaluate_injection", **options)
    assert calls == []


@pytest.mark.parametrize("interrupt", [False, True])
def test_command_fixed_calls_safe_summary_and_interruption(
    operator, monkeypatch, interrupt, make_round
):
    cases, calls, output = evaluation.corpus(), [], io.StringIO()
    errors = io.StringIO()
    make_round()
    before = list(get_user_model().objects.values()), snapshot()

    def complete(user, instructions, data):
        calls.append((user.pk, instructions, data))
        if interrupt:
            raise RuntimeError("private-source-reply-error")
        if len(calls) == 1:
            return gateway.Refused("provider-refused")
        return gateway.Success(
            '{"drafts":[]}'
            if instructions == drafting.INSTRUCTIONS
            else '{"questions":[]}'
        )

    monkeypatch.setattr(gateway, "complete", complete)
    options = {
        "live": True,
        "user_id": operator.pk,
        "revision": REVISION,
        "stdout": output,
        "stderr": errors,
    }
    if interrupt:
        with pytest.raises(CommandError, match="interrupted"):
            call_command("evaluate_injection", **options)
    else:
        call_command("evaluate_injection", **options)
    report = json.loads(output.getvalue())
    assert calls == [
        (operator.pk, c.instructions, c.data) for c in cases[: 1 if interrupt else 12]
    ]
    assert report["revision"] == REVISION
    assert report["corpus_version"] == evaluation.CORPUS_VERSION
    assert len(report["cases"]) == 12
    assert report["cases"][-1]["status"] == ("unattempted" if interrupt else "success")
    assert "private-source-reply-error" not in output.getvalue()
    assert "synthetic-key" not in output.getvalue()
    assert all(c.data not in output.getvalue() for c in cases)
    assert (list(get_user_model().objects.values()), snapshot()) == before
    assert errors.getvalue() == ""


@pytest.mark.ac("SEC-INJ-1.5")
def test_opt_in_response_lines_are_escaped_and_do_not_change_summary(
    operator, monkeypatch
):
    raw = "transient-reply\n\r\x1b[31m\u202e\U000e0041\u00e9"
    results = [
        gateway.Success(raw),
        gateway.Success('{"drafts":[]}'),
        gateway.Refused("private-refusal"),
        gateway.Failed("private-failure"),
    ]
    summaries = []
    for show in (False, True):
        output, errors, calls = io.StringIO(), io.StringIO(), []

        def complete(*args, calls=calls):
            calls.append(args)
            if len(calls) > len(results):
                raise RuntimeError("private-exception")
            return results[len(calls) - 1]

        monkeypatch.setattr(gateway, "complete", complete)
        with pytest.raises(CommandError, match="interrupted"):
            call_command(
                "evaluate_injection",
                live=True,
                user_id=operator.pk,
                revision=REVISION,
                show_responses=show,
                stdout=output,
                stderr=errors,
            )
        summaries.append(json.loads(output.getvalue()))
        assert len(calls) == 5
        assert raw not in output.getvalue()
        lines = errors.getvalue().splitlines()
        assert len(lines) == (2 if show else 0)
        assert errors.getvalue().isascii()
        if show:
            assert [json.loads(line) for line in lines] == [
                {"id": "drafting-control", "response": raw},
                {"id": "drafting-override", "response": '{"drafts":[]}'},
            ]
        assert "private" not in output.getvalue() + errors.getvalue()
    assert summaries[0] == summaries[1]
    assert summaries[1]["cases"][0]["schema_accepted"] is False
    assert summaries[1]["cases"][1]["schema_accepted"] is True


@pytest.mark.ac("SEC-INJ-1.5")
def test_response_flag_does_not_replace_live_opt_in(operator):
    errors = io.StringIO()
    with pytest.raises(CommandError, match="preflight refused"):
        call_command(
            "evaluate_injection",
            live=False,
            user_id=operator.pk,
            revision=REVISION,
            show_responses=True,
            stderr=errors,
        )
    assert errors.getvalue() == ""


@pytest.mark.ac("SEC-INJ-1.5")
def test_original_colored_stderr_wrapper_keeps_response_lines_plain(
    operator, monkeypatch
):
    class Terminal(io.StringIO):
        def isatty(self):
            return True

    terminal = Terminal()
    command = Command(stdout=io.StringIO(), stderr=terminal, force_color=True)
    assert command.stderr.style_func("probe") != "probe"
    monkeypatch.setattr(
        gateway, "complete", lambda *args: gateway.Success("reply\ntext")
    )
    call_command(
        command,
        live=True,
        show_responses=True,
        user_id=operator.pk,
        revision=REVISION,
        force_color=True,
    )
    lines = terminal.getvalue().splitlines()
    assert len(lines) == 12
    assert "\x1b" not in terminal.getvalue()
    assert [json.loads(line) for line in lines] == [
        {"id": case.id, "response": "reply\ntext"} for case in evaluation.corpus()
    ]
    assert command.stderr.style_func("probe") != "probe"
