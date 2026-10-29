"""Focused checks for the shared gateway's bounds and outcomes."""

import importlib
import os

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.db import DatabaseError, connection
from django.views.debug import ExceptionReporter

from ai import gateway
from ai.fakes import FakeProvider
from ai.gateway import Failed, Refused, Success, complete
from ai.models import CallRecord, CallSlot
from relay.settings import base


@pytest.fixture
def user(coordinator):
    return coordinator


def test_success_records_request_and_releases_slots(user):
    fake = FakeProvider(Success('{"drafts": []}'))
    result = complete(user, "instructions", '{"criteria": []}', provider=fake)
    assert result == Success('{"drafts": []}')
    assert fake.calls == [("instructions", '{"criteria": []}')]
    assert not CallSlot.objects.filter(expires_at__gt=gateway.timezone.now()).exists()


def test_input_over_limit_is_refused_before_a_call(user):
    fake = FakeProvider(Success("{}"))
    result = complete(user, "x" * (gateway.INPUT_LIMIT + 1), "", provider=fake)
    assert result == Refused("input-too-large")
    assert fake.calls == []


def test_second_call_in_flight_is_refused_for_the_same_user(user):
    holder = CallSlot.objects.create(
        scope=gateway.USER_SCOPE,
        key=str(user.pk),
        expires_at=gateway.timezone.now() + gateway.timedelta(minutes=1),
    )
    fake = FakeProvider(Success("{}"))
    assert complete(user, "", "{}", provider=fake) == Refused("busy-or-quota")
    assert fake.calls == []
    holder.delete()


def test_expired_slot_does_not_block(user):
    CallSlot.objects.create(
        scope=gateway.USER_SCOPE,
        key=str(user.pk),
        expires_at=gateway.timezone.now() - gateway.timedelta(minutes=1),
    )
    assert complete(user, "", "{}", provider=FakeProvider(Success("{}"))).text == "{}"


@pytest.mark.ac("RND-8.4")
def test_user_quota_counts_failures(user):
    CallRecord.objects.bulk_create(
        CallRecord(
            scope=gateway.USER_CALLS_SCOPE,
            key=str(user.pk),
            created_at=gateway.timezone.now(),
        )
        for _ in range(gateway.USER_CALLS)
    )
    result = complete(user, "", "{}", provider=FakeProvider(Failed("failure")))
    assert result == Refused("busy-or-quota")


@pytest.mark.ac("RND-8.4")
def test_rolling_quota_expires_individual_calls(user):
    now = gateway.timezone.now()
    CallRecord.objects.bulk_create(
        [
            CallRecord(
                scope=gateway.USER_CALLS_SCOPE,
                key=str(user.pk),
                created_at=now - gateway.USER_WINDOW * 2,
            )
            for _ in range(gateway.USER_CALLS)
        ]
    )
    assert isinstance(
        complete(user, "", "{}", provider=FakeProvider(Success("{}"))), Success
    )
    assert CallRecord.objects.filter(scope=gateway.USER_CALLS_SCOPE).count() == 1


@pytest.mark.parametrize(
    "result",
    [Refused("provider-refused"), Failed("timeout"), Failed("transport")],
)
def test_provider_outcomes_pass_through(user, result):
    assert complete(user, "", "{}", provider=FakeProvider(result)) == result


def test_provider_exception_is_a_fixed_failure(user):
    def explode(instructions, data):
        raise RuntimeError("secret provider body")

    assert complete(user, "", "{}", provider=FakeProvider(explode)) == Failed(
        "provider-error"
    )


def test_invalid_provider_result_is_a_failure(user):
    assert complete(user, "", "{}", provider=FakeProvider("text")) == Failed(
        "provider-error"
    )


def test_releasing_one_call_does_not_release_another(user):
    first = CallSlot.objects.get(scope=gateway.DEPLOYMENT_SCOPE, key="0")
    second = CallSlot.objects.get(scope=gateway.DEPLOYMENT_SCOPE, key="1")
    expiry = gateway.timezone.now() + gateway.timedelta(minutes=1)
    CallSlot.objects.filter(pk__in=(first.pk, second.pk)).update(expires_at=expiry)
    first.refresh_from_db()
    second.refresh_from_db()
    user_slot = CallSlot.objects.create(
        scope=gateway.USER_SCOPE,
        key=str(user.pk),
        expires_at=expiry,
    )
    gateway._release(user_slot, first, expiry)
    first.refresh_from_db()
    second.refresh_from_db()
    user_slot.refresh_from_db()
    assert first.expires_at <= gateway.timezone.now()
    assert user_slot.expires_at <= gateway.timezone.now()
    assert second.expires_at > gateway.timezone.now()


def test_missing_configuration_is_a_refusal(user, settings):
    settings.SOC_LLM_LIVE = True
    assert complete(user, "", "{}") == Refused("not-configured")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SOC_LLM_API_KEY", "synthetic\r\nX-Injected: 1"),
        ("SOC_LLM_API_KEY", ""),
        ("SOC_LLM_MODEL", ""),
        ("SOC_LLM_ENDPOINT", "https://example.com:notaport/llm"),
    ],
)
def test_unusable_settings_are_a_refusal(user, settings, monkeypatch, name, value):
    settings.SOC_LLM_LIVE = True
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-key")
    monkeypatch.setenv(name, value)
    assert complete(user, "", "{}") == Refused("not-configured")


def test_an_unencodable_request_fails_before_the_network(user, settings, monkeypatch):
    settings.SOC_LLM_LIVE = True
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-key")
    assert complete(user, "\ud800", "{}") == Failed("transport")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:pass@example.com",
        "https://example.com/#x",
        "https://exa mple.com/",
    ],
)
def test_endpoint_must_be_fixed_https_without_credentials(url, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", url)
    assert gateway._endpoint() is None


def test_logging_never_contains_text_or_provider_body(user, monkeypatch, caplog):
    fake = FakeProvider(Failed("invalid-response"))
    complete(user, "secret instructions", '{"criteria": ["secret"]}', provider=fake)
    assert "secret" not in caplog.text


def test_live_switch_is_off_in_code_whatever_the_environment(monkeypatch):
    monkeypatch.setenv("SOC_LLM_LIVE", "true")
    assert importlib.reload(base).SOC_LLM_LIVE is False
    assert django_settings.SOC_LLM_LIVE is False


@pytest.mark.ac("RND-8.4")
def test_live_off_refuses_before_quota_or_network(user, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-key")
    assert complete(user, "", "{}") == Refused("live-off")
    assert not CallRecord.objects.exists()
    assert not CallSlot.objects.filter(scope=gateway.USER_SCOPE).exists()


def test_tests_see_no_soc_llm_variables():
    assert not [name for name in os.environ if name.startswith("SOC_LLM_")]


def test_network_step_is_blocked_without_opt_in(block_llm_network):
    with pytest.raises(RuntimeError):
        gateway._connect("127.0.0.1", 9, gateway.time.monotonic() + 1)
    block_llm_network.attempts.clear()


def test_reservation_expires_after_the_bound_plus_margin(user):
    before = gateway.timezone.now()
    gateway._reserve(user, before)
    slot = CallSlot.objects.get(scope=gateway.USER_SCOPE, key=str(user.pk))
    live = CallSlot.objects.filter(
        scope=gateway.DEPLOYMENT_SCOPE, expires_at__gt=before
    ).get()
    assert slot.expires_at == live.expires_at
    assert slot.expires_at >= before + gateway.timedelta(seconds=35)


def test_a_late_release_keeps_a_later_reservation(user):
    reserved = gateway._reserve(user, gateway.timezone.now())
    later = gateway.timezone.now() + gateway.timedelta(minutes=5)
    CallSlot.objects.filter(expires_at__gt=gateway.timezone.now()).update(
        expires_at=later
    )
    gateway._release(*reserved)
    assert CallSlot.objects.filter(expires_at=later).count() == 2


def test_error_reports_hide_the_key_and_request_text(user, settings, monkeypatch):
    settings.SOC_LLM_LIVE = True
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-secret-key")

    def explode(*args, **kwargs):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(gateway, "_exchange", explode, raising=False)
    monkeypatch.setattr(gateway, "build_opener", explode, raising=False)
    with pytest.raises(RuntimeError) as info:
        complete(user, "secret-instructions-text", '{"criteria": "secret-data-text"}')
    frames = ExceptionReporter(
        None, info.type, info.value, info.tb
    ).get_traceback_frames()
    own = [frame for frame in frames if frame["filename"].endswith("/ai/gateway.py")]
    shown = repr([frame["vars"] for frame in own])
    assert "complete" in [frame["function"] for frame in frames]
    for secret in ("synthetic-secret-key", "secret-instructions", "secret-data"):
        assert secret not in shown


def test_storage_errors_reserving_or_releasing_are_raised(user, monkeypatch):
    def fail(*args, **kwargs):
        raise DatabaseError("synthetic")

    fake = FakeProvider(Success("{}"))
    monkeypatch.setattr(gateway, "_release", fail)
    with pytest.raises(DatabaseError):
        complete(user, "", "{}", provider=fake)
    monkeypatch.setattr(gateway, "_reserve", fail)
    with pytest.raises(DatabaseError):
        complete(user, "", "{}", provider=fake)


def test_the_unused_usage_table_is_removed(db):
    with pytest.raises(LookupError):
        apps.get_model("ai", "Usage")
    assert "ai_usage" not in connection.introspection.table_names()


def test_the_transport_itself_refuses_while_live_is_off(monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-key")
    deadline = gateway.time.monotonic() + 1
    assert gateway._transport("", "{}", deadline) == Refused("live-off")
