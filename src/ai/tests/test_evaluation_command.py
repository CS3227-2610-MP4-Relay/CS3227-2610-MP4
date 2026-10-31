"""Offline operator command preflight and bounded orchestration."""

import io
import json

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from ai import drafting, evaluation, gateway
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
