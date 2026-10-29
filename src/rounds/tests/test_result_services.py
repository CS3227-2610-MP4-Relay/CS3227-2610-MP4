"""RES-2 persistence, ownership and serialized result lifecycle checks."""

import threading
import time
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404

from accounts.models import User
from rounds import results, services
from rounds.models import (
    Build,
    BuildCase,
    Case,
    CaseCriterion,
    Criterion,
    Result,
    Round,
)

from .conftest import open_with_case

pytestmark = pytest.mark.django_db


@pytest.fixture
def target(make_round):
    """One current published case and its covering build."""
    round_ = open_with_case(make_round)
    return round_, round_.cases.get(), round_.builds.get()


def entry(user, target, **kwargs):
    """Enter the result operation for a tuple, without choosing a result ID."""
    return results.entry(user, *(record.pk for record in target), **kwargs)


def save(user, target, *, submit=False, outcome="pass", observation=""):
    """Use the service's locked operation, as a validated form will."""
    with entry(user, target, write=True) as current:
        return results.save(current, outcome, observation, submit=submit)


def snapshot():
    """Capture domain rows to prove refused actions change nothing."""
    return {
        model: list(model.objects.order_by("pk").values())
        for model in (Round, Criterion, Case, CaseCriterion, Build, BuildCase, Result)
    }


@pytest.mark.ac("RES-2.1", "RES-2.5")
def test_draft_replace_submit_then_frozen(tester, target):
    with entry(tester, target) as current:
        assert current.result is None
    assert Result.objects.count() == 0
    first = save(tester, target)
    assert first.submitted_at is None
    second = save(tester, target, outcome="fail", observation="Synthetic failure")
    assert second.pk == first.pk
    assert (second.outcome, second.observation) == ("fail", "Synthetic failure")
    submitted = save(tester, target, submit=True, observation="Synthetic final")
    assert submitted.pk == first.pk and submitted.submitted_at is not None
    with entry(tester, target) as current:
        assert current.result == submitted
    before = snapshot()
    for submit in (False, True):
        with pytest.raises(results.Conflict, match="already been submitted"):
            save(tester, target, submit=submit)
    assert snapshot() == before


@pytest.mark.ac("RES-2.1", "RES-2.3")
def test_direct_submit_and_other_tester_have_independent_rows(tester, target):
    other = User.objects.create_user(
        "tester2-result", "Synthetic16Chars", workspace=tester.workspace, role="tester"
    )
    one = save(tester, target, submit=True, observation="Synthetic private")
    with entry(other, target) as current:
        assert current.result is None
    two = save(other, target, outcome="fail", observation="Synthetic other")
    assert one.pk != two.pk
    assert one.tester_id == tester.pk and two.tester_id == other.pk
    with entry(tester, target) as current:
        assert current.result.observation == "Synthetic private"


@pytest.mark.ac("RES-2.3")
def test_role_and_workspace_denials_precede_lookup(
    coordinator, tester, target, other_workspace
):
    before = snapshot()
    with patch("rounds.results.workspace_records") as lookup:
        with pytest.raises(PermissionDenied):
            save(coordinator, target)
        lookup.assert_not_called()
    outsider = User.objects.create_user(
        "tester-foreign", "Synthetic16Chars", workspace=other_workspace, role="tester"
    )
    with pytest.raises(Http404):
        save(outsider, target)
    assert snapshot() == before


@pytest.mark.ac("RES-2.3", "RES-2.4")
@pytest.mark.parametrize("invalid", ["round", "case", "build", "coverage", "draft"])
def test_invalid_membership_is_404_before_state(tester, target, make_round, invalid):
    round_, case, build = target
    other = make_round()
    other_case = Case.objects.create(
        round=other, title="Synthetic other", steps="Steps", expected_result="Expected"
    )
    other_build = Build.objects.create(round=other, label="Other", key="Other")
    if invalid == "round":
        round_ = other
    elif invalid == "case":
        case = other_case
    elif invalid == "build":
        build = other_build
    elif invalid == "coverage":
        BuildCase.objects.filter(case=case, build=build).delete()
    else:
        Round.objects.filter(pk=round_.pk).update(state=Round.State.DRAFT)
    if invalid != "draft":
        Round.objects.filter(pk=round_.pk).update(state=Round.State.CLOSED)
    before = snapshot()
    with pytest.raises(Http404):
        save(tester, (round_, case, build))
    assert snapshot() == before


@pytest.mark.ac("RND-5.1", "RND-5.5", "RES-2.1", "RES-2.4", "RES-2.5")
def test_retest_keeps_old_row_and_unselected_case_entry(tester, target):
    round_, case, original = target
    overlap = Case.objects.create(
        round=round_,
        title="Synthetic overlapping",
        steps="Steps",
        expected_result="Expected",
    )
    unselected = Case.objects.create(
        round=round_,
        title="Synthetic unselected",
        steps="Steps",
        expected_result="Expected",
    )
    for additional in (overlap, unselected):
        BuildCase.objects.create(build=original, case=additional)
    saved = save(
        tester, target, submit=True, outcome="fail", observation="Synthetic failure"
    )
    overlapping = save(tester, (round_, overlap, original))
    untouched = save(tester, (round_, unselected, original))
    current_rows = {case.pk: saved, overlap.pk: overlapping, unselected.pk: untouched}
    stale_targets = []
    for label, selected in (
        ("Synthetic partial", [case]),
        ("Synthetic overlap", [case, overlap]),
        ("Synthetic repeated", [case]),
    ):
        old_rows = list(Result.objects.order_by("pk").values())
        old_ids = [row["id"] for row in old_rows]
        with transaction.atomic():
            locked = Round.objects.select_for_update().get(pk=round_.pk)
            new = services.request_retest(locked, label, [item.pk for item in selected])
        assert list(Result.objects.order_by("pk").values()) == old_rows
        before = snapshot()
        for item in selected:
            stale_targets.append((round_, item, current_rows[item.pk].build))
            with entry(tester, (round_, item, new)) as current:
                assert current.result is None
        for stale in stale_targets:
            for write in (False, True):
                with (
                    pytest.raises(results.Conflict, match="no longer current"),
                    entry(tester, stale, write=write),
                ):
                    pytest.fail("A stale entry was allowed")
        for item in (case, overlap, unselected):
            if item not in selected:
                previous = current_rows[item.pk]
                with entry(tester, (round_, item, previous.build)) as current:
                    assert current.result == previous
        assert snapshot() == before
        for item in selected:
            submitted = save(tester, (round_, item, new), submit=True)
            assert submitted.pk not in old_ids
            assert submitted.outcome == "pass" and submitted.submitted_at is not None
            current_rows[item.pk] = submitted
        # Compare every original field, including observations and submission times.
        assert (
            list(Result.objects.filter(pk__in=old_ids).order_by("pk").values())
            == old_rows
        )
    assert Result.objects.count() == 7


@pytest.mark.ac("RES-2.4")
@pytest.mark.parametrize("write", [False, True])
def test_closed_entry_is_refused_without_changes(tester, target, write):
    save(tester, target)
    with transaction.atomic():
        services.close(Round.objects.select_for_update().get(pk=target[0].pk))
    before = snapshot()
    with (
        pytest.raises(results.Conflict, match="while the round is Closed"),
        entry(tester, target, write=write),
    ):
        pytest.fail("A Closed entry was allowed")
    assert snapshot() == before


@pytest.mark.ac("RES-2.6")
@pytest.mark.parametrize("existing", [False, True])
def test_failed_storage_rolls_back_create_or_update(tester, target, existing):
    if existing:
        save(tester, target, observation="Synthetic before")
    before = snapshot()
    original = Result.save

    def failing_save(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise OperationalError("Synthetic storage failure")

    with patch.object(Result, "save", failing_save), pytest.raises(OperationalError):
        save(tester, target, submit=True, observation="Synthetic after")
    assert snapshot() == before


def test_database_constraints_and_protected_references(tester, target):
    saved = save(tester, target)
    fields = {"tester": tester, "case": target[1], "build": target[2]}
    for change in (
        {},
        {
            "tester": User.objects.create_user(
                "tester-constraint",
                "Synthetic16Chars",
                workspace=tester.workspace,
                role="tester",
            ),
            "outcome": "skip",
        },
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Result.objects.create(**(fields | {"outcome": "pass"} | change))
    for record in (tester, target[1], target[2]):
        with pytest.raises(ProtectedError), transaction.atomic():
            record.delete()
    assert Result.objects.get(pk=saved.pk).observation == ""


def race(first, second):
    """Hold the first round lock until PostgreSQL reports the second waiting."""
    held, release, started = threading.Event(), threading.Event(), threading.Event()
    outcomes, errors, pids = {}, [], {}

    def run(name, operation):
        try:
            connection.ensure_connection()
            pids[name] = connection.connection.info.backend_pid
            if name == "second":
                started.set()
            outcomes[name] = operation(held, release)
        except Exception as error:  # noqa: BLE001 - re-raised in the test thread
            errors.append(error)
        finally:
            connection.close()

    one = threading.Thread(target=run, args=("first", first))
    two = threading.Thread(target=run, args=("second", second))
    one.start()
    try:
        assert held.wait(5), "First operation never held its lock"
        two.start()
        assert started.wait(5), "Second connection never started"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                    [pids["second"]],
                )
                if cursor.fetchone() == ("Lock",):
                    break
            time.sleep(0.01)
        else:
            pytest.fail("Second operation did not wait for the real round lock")
    finally:
        release.set()
        one.join(10)
        if two.ident is not None:
            two.join(10)
    assert not one.is_alive() and not two.is_alive()
    if errors:
        raise errors[0]
    return outcomes


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("RES-2.5")
@pytest.mark.parametrize("action", ["close", "retest", "submit", "save"])
@pytest.mark.parametrize("result_first", [False, True])
def test_real_races_serialize_results_and_round_actions(
    tester, target, action, result_first
):
    def result_action(held, release, pause=False):
        try:
            with entry(tester, target, write=True) as current:
                row = results.save(current, "pass", "Synthetic final", submit=True)
                if pause:
                    held.set()
                    assert release.wait(10)
                return row.pk
        except results.Conflict:
            return "conflict"

    def competing_action(held, release, pause=False):
        if action in ("submit", "save"):
            try:
                with entry(tester, target, write=True) as current:
                    row = results.save(
                        current,
                        "fail",
                        "Synthetic competing",
                        submit=action == "submit",
                    )
                    if pause:
                        held.set()
                        assert release.wait(10)
                    return row.pk
            except results.Conflict:
                return "conflict"
        with transaction.atomic():
            locked = Round.objects.select_for_update().get(pk=target[0].pk)
            if action == "close":
                services.close(locked)
            else:
                services.request_retest(locked, "Synthetic racing", [target[1].pk])
            if pause:
                held.set()
                assert release.wait(10)
        return "round changed"

    first = result_action if result_first else competing_action
    second = competing_action if result_first else result_action
    outcomes = race(lambda *args: first(*args, pause=True), second)
    if action == "save" and not result_first:
        assert outcomes["second"] != "conflict"
    elif not result_first or action in ("submit", "save"):
        assert outcomes["second"] == "conflict"
    rows = list(Result.objects.all())
    assert len(rows) == (0 if not result_first and action in ("close", "retest") else 1)
    for row in rows:
        assert row.build_id == target[2].pk
        assert row.submitted_at is not None
        assert row.observation == (
            "Synthetic competing"
            if not result_first and action == "submit"
            else "Synthetic final"
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.ac("RES-2.5")
def test_two_concurrent_draft_saves_keep_last_serialized_values(tester, target):
    before = snapshot()

    def first(held, release):
        with entry(tester, target, write=True) as current:
            saved = results.save(current, "pass", "Synthetic first")
            held.set()
            assert release.wait(10)
            return saved.pk

    outcomes = race(
        first,
        lambda *_: (
            save(tester, target, outcome="fail", observation="Synthetic last").pk
        ),
    )
    assert outcomes["first"] == outcomes["second"]
    saved = Result.objects.get()
    assert (saved.outcome, saved.observation, saved.submitted_at) == (
        "fail",
        "Synthetic last",
        None,
    )
    after = snapshot()
    assert {model: rows for model, rows in after.items() if model is not Result} == {
        model: rows for model, rows in before.items() if model is not Result
    }
