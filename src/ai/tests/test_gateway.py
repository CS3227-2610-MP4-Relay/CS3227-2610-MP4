"""Focused checks for the shared gateway's bounds and outcomes."""

import importlib
import logging
import os
import threading
import time

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.db import DatabaseError, connection, transaction
from django.views.debug import ExceptionReporter

from accounts.models import User
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
        for _ in range(gateway.USER_CALLS - 1)
    )
    failing = FakeProvider(Failed("transport"))
    assert complete(user, "", "{}", provider=failing) == Failed("transport")
    assert len(failing.calls) == 1
    fake = FakeProvider(Success("{}"))
    assert complete(user, "", "{}", provider=fake) == Refused("busy-or-quota")
    assert fake.calls == []


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


def test_logging_never_contains_text_or_provider_body(user, caplog):
    caplog.set_level(logging.DEBUG, logger="ai")

    def explode(instructions, data):
        raise RuntimeError("secret provider body")

    complete(
        user,
        "secret instructions",
        '{"criteria": ["secret data"]}',
        provider=FakeProvider(explode),
    )
    assert [
        record.getMessage() for record in caplog.records if record.name == "ai.gateway"
    ] == ["LLM gateway outcome: provider-error"]
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
        gateway._exchange("https://127.0.0.1:9/llm", {}, b"", 0)
    block_llm_network.attempts.clear()


def test_reservation_expires_after_the_bound_plus_margin(user):
    before = gateway.timezone.now()
    gateway._reserve(user)
    slot = CallSlot.objects.get(scope=gateway.USER_SCOPE, key=str(user.pk))
    live = CallSlot.objects.filter(
        scope=gateway.DEPLOYMENT_SCOPE, expires_at__gt=before
    ).get()
    assert slot.expires_at == live.expires_at
    assert slot.expires_at >= before + gateway.timedelta(seconds=35)


def test_a_late_release_keeps_a_later_reservation(user):
    reserved, _ = gateway._reserve(user)
    later = gateway.timezone.now() + gateway.timedelta(minutes=5)
    CallSlot.objects.filter(expires_at__gt=gateway.timezone.now()).update(
        expires_at=later
    )
    gateway._release(*reserved)
    assert CallSlot.objects.filter(expires_at=later).count() == 2


class _Escape(BaseException):
    """Not an Exception, so it passes the transport's catch-all, as a cancel would."""


@pytest.mark.llm_transport
@pytest.mark.parametrize("escape", ["transport", "release"])
def test_error_reports_hide_the_key_and_request_text(
    user, settings, monkeypatch, escape
):
    """Frames that can reach an error report show no key or request text.

    Any Exception in the transport becomes Failed("transport"), so a report can
    only come from a BaseException inside it, or from a storage error in
    `complete`. aiohttp's session is replaced, so no connection is opened.
    """
    settings.SOC_LLM_LIVE = True
    monkeypatch.setenv("SOC_LLM_ENDPOINT", "https://127.0.0.1:9/llm")
    monkeypatch.setenv("SOC_LLM_MODEL", "synthetic")
    monkeypatch.setenv("SOC_LLM_API_KEY", "synthetic-secret-key")
    raised = _Escape if escape == "transport" else gateway.aiohttp.ClientError

    def session(*args, **kwargs):
        raise raised("synthetic")

    def release(*args):
        raise DatabaseError("synthetic")

    monkeypatch.setattr(gateway.aiohttp, "ClientSession", session)
    if escape == "release":
        monkeypatch.setattr(gateway, "_release", release)
    expected = _Escape if escape == "transport" else DatabaseError
    with pytest.raises(expected) as info:
        complete(user, "secret-instructions-text", '{"criteria": "secret-data-text"}')
    if escape == "transport":
        now = gateway.timezone.now()
        assert not CallSlot.objects.filter(expires_at__gt=now).exists()
    frames = ExceptionReporter(
        None, info.type, info.value, info.tb
    ).get_traceback_frames()
    own = [frame for frame in frames if frame["filename"].endswith("/ai/gateway.py")]
    shown = repr([frame["vars"] for frame in own])
    functions = [frame["function"] for frame in own]
    assert "complete" in functions
    if escape == "transport":
        assert {"_transport", "_exchange"} <= set(functions)
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


def deployment_records(count):
    CallRecord.objects.bulk_create(
        CallRecord(
            scope=gateway.DEPLOYMENT_CALLS_SCOPE,
            key="all",
            created_at=gateway.timezone.now(),
        )
        for _ in range(count)
    )


@pytest.mark.ac("RND-8.4")
def test_a_third_call_in_flight_is_refused_deployment_wide(user):
    CallSlot.objects.filter(scope=gateway.DEPLOYMENT_SCOPE).update(
        expires_at=gateway.timezone.now() + gateway.timedelta(minutes=1)
    )
    fake = FakeProvider(Success("{}"))
    assert complete(user, "", "{}", provider=fake) == Refused("busy-or-quota")
    assert fake.calls == []


def test_one_free_deployment_slot_is_enough(user):
    CallSlot.objects.filter(scope=gateway.DEPLOYMENT_SCOPE, key="0").update(
        expires_at=gateway.timezone.now() + gateway.timedelta(minutes=1)
    )
    assert complete(user, "", "{}", provider=FakeProvider(Success("{}"))) == Success(
        "{}"
    )


@pytest.mark.ac("RND-8.4")
@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        (gateway.DEPLOYMENT_CALLS - 1, Success("{}")),
        (gateway.DEPLOYMENT_CALLS, Refused("busy-or-quota")),
    ],
    ids=["just-below", "at-limit"],
)
def test_deployment_quota_boundary(user, existing, expected):
    deployment_records(existing)
    assert complete(user, "", "{}", provider=FakeProvider(Success("{}"))) == expected


class SlowProvider:
    """Hold each call open long enough for a competing reservation to see it."""

    def __init__(self, delay=1.5):
        self.delay = delay
        self.connections = []

    def complete(self, instructions, data):
        self.connections.append(connection.connection)
        time.sleep(self.delay)
        return Success("{}")


def gate_quota(monkeypatch, parties):
    """Make reservations meet inside their transaction, if locking lets them."""
    barrier = threading.Barrier(parties)
    real = gateway._quota

    def meet(scope, *args):
        if scope == gateway.USER_CALLS_SCOPE:
            try:
                barrier.wait(timeout=1)
            except threading.BrokenBarrierError:
                pass
        return real(scope, *args)

    monkeypatch.setattr(gateway, "_quota", meet)


def run_together(users, provider):
    results = [None] * len(users)

    def run(index, user):
        try:
            results[index] = complete(user, "", "{}", provider=provider)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=pair) for pair in enumerate(users)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    return results


def outcomes(results):
    return sorted(type(result).__name__ for result in results)


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("RND-8.4")
def test_two_racing_calls_for_one_user_reserve_once(user, monkeypatch):
    CallSlot.objects.create(
        scope=gateway.USER_SCOPE,
        key=str(user.pk),
        expires_at=gateway.timezone.now() - gateway.timedelta(minutes=1),
    )
    gate_quota(monkeypatch, 2)
    results = run_together([user, user], SlowProvider())
    assert outcomes(results) == ["Refused", "Success"]
    assert CallRecord.objects.filter(scope=gateway.USER_CALLS_SCOPE).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("RND-8.4")
def test_three_racing_users_share_two_deployment_slots(
    user, tester, other_workspace, monkeypatch
):
    third = User.objects.create_user(
        "coord-ai10002",
        "Synthetic16Chars",
        workspace=other_workspace,
        role="coordinator",
    )
    gate_quota(monkeypatch, 3)
    results = run_together([user, tester, third], SlowProvider())
    assert outcomes(results) == ["Refused", "Success", "Success"]


@pytest.mark.django_db(transaction=True)
def test_no_database_connection_is_held_during_the_call(user):
    provider = SlowProvider(delay=0)
    assert complete(user, "", "{}", provider=provider) == Success("{}")
    assert provider.connections == [None]


@pytest.mark.django_db(transaction=True)
def test_a_reservation_that_waits_for_locks_is_timed_after_the_wait(
    user, settings, monkeypatch
):
    """Slot expiry and the deadline start once the locks are held, not before."""
    settings.SOC_LLM_LIVE = True
    held, released, seen = threading.Event(), {}, {}

    def hold_locks():
        try:
            with transaction.atomic():
                list(
                    CallSlot.objects.select_for_update().filter(
                        scope=gateway.DEPLOYMENT_SCOPE
                    )
                )
                held.set()
                time.sleep(1)
                released["wall"] = gateway.timezone.now()
                released["clock"] = time.monotonic()
        finally:
            connection.close()

    def transport(instructions, data, deadline):
        seen["deadline"] = deadline
        return Success("{}")

    real_reserve, real_release = gateway._reserve, gateway._release

    def reserve(*args):
        seen["reserved"] = real_reserve(*args)
        return seen["reserved"]

    def release(*args):
        seen["expires"] = args[-1]
        return real_release(*args)

    monkeypatch.setattr(gateway, "_transport", transport)
    monkeypatch.setattr(gateway, "_reserve", reserve)
    monkeypatch.setattr(gateway, "_release", release)
    thread = threading.Thread(target=hold_locks)
    thread.start()
    assert held.wait(5)
    assert complete(user, "", "{}") == Success("{}")
    thread.join(5)
    bound = gateway.TOTAL_TIMEOUT + gateway.RELEASE_MARGIN
    assert seen["expires"] >= released["wall"] + gateway.timedelta(seconds=bound)
    assert seen["deadline"] >= released["clock"] + gateway.TOTAL_TIMEOUT
    assert seen["deadline"] == seen["reserved"][1] + gateway.TOTAL_TIMEOUT
