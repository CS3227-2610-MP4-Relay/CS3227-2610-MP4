"""Focused checks for the shared gateway's bounds and outcomes."""

import json
from unittest import mock

import pytest

from ai import gateway
from ai.fakes import FakeProvider
from ai.gateway import Failed, Refused, Success, complete
from ai.models import CallRecord, CallSlot


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
    gateway._release(user_slot, first)
    first.refresh_from_db()
    second.refresh_from_db()
    user_slot.refresh_from_db()
    assert first.expires_at <= gateway.timezone.now()
    assert user_slot.expires_at <= gateway.timezone.now()
    assert second.expires_at > gateway.timezone.now()


def test_missing_configuration_is_a_refusal(user, monkeypatch):
    for name in ("SOC_LLM_ENDPOINT", "SOC_LLM_MODEL", "SOC_LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert complete(user, "", "{}") == Refused("not-configured")


@pytest.mark.parametrize(
    "url",
    ["http://example.com", "https://user:pass@example.com", "https://example.com/#x"],
)
def test_endpoint_must_be_fixed_https_without_credentials(url, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", url)
    assert gateway._endpoint() is None


def test_logging_never_contains_text_or_provider_body(user, monkeypatch, caplog):
    fake = FakeProvider(Failed("invalid-response"))
    complete(user, "secret instructions", '{"criteria": ["secret"]}', provider=fake)
    assert "secret" not in caplog.text


def test_transport_does_not_follow_redirects(user, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://example.com/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "secret")
    with mock.patch.object(gateway, "build_opener") as opener:
        opener.return_value.open.side_effect = gateway.HTTPError(
            "https://elsewhere.example", 302, "redirect", {}, None
        )
        assert complete(user, "", "{}") == Failed("transport")


def test_transport_decodes_one_text_object(user, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://example.com/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "secret")
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.read1.side_effect = [json.dumps({"text": "ok"}).encode(), b""]
    with mock.patch.object(gateway, "build_opener") as opener:
        opener.return_value.open.return_value = response
        assert complete(user, "", "{}") == Success("ok")


@pytest.mark.ac("RND-8.5")
def test_transport_accepts_a_20000_non_bmp_character_text(user, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://example.com/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "secret")
    response = mock.MagicMock()
    response.__enter__.return_value = response
    body = json.dumps({"text": "\U0001f600" * 20000}, ensure_ascii=False).encode()
    response.read1.side_effect = [
        body[index : index + 8192] for index in range(0, len(body), 8192)
    ] + [b""]
    with mock.patch.object(gateway, "build_opener") as opener:
        opener.return_value.open.return_value = response
        assert complete(user, "", "{}") == Success("\U0001f600" * 20000)


@pytest.mark.ac("RND-8.4")
def test_transport_enforces_the_whole_request_deadline(user, monkeypatch):
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://example.com/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "secret")
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.read1.return_value = b"x"
    deadline = mock.patch.object(gateway.time, "monotonic", side_effect=[0, 31])
    with mock.patch.object(gateway, "build_opener") as opener:
        opener.return_value.open.return_value = response
        with deadline:
            assert complete(user, "", "{}") == Failed("timeout")
