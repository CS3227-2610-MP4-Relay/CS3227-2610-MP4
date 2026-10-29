"""Private result entry and persistence under the shared round lock (RES-2)."""

from contextlib import contextmanager
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from accounts.workspaces import workspace_records

from .models import Build, Case, Result, Round

STALE = "This build is no longer current. Reload the round to record a result."
SUBMITTED = "This result has already been submitted."


class Conflict(Exception):
    """A fixed-text state/build/submission refusal, rendered by entry as 409."""


@dataclass
class Entry:
    """Authorized context valid for the duration of an entry operation."""

    tester: User
    round: Round
    case: Case
    build: Build
    result: Result | None


@contextmanager
def entry(tester, round_id, case_id, build_id, *, write=False):
    """Authorize a tuple, then yield it; writes hold the round lock throughout.

    The caller validates form fields and calls `save` only inside a write
    context. Denials precede validation; database errors roll back on exit.
    Reads take no row lock and never create a result.
    """
    if not tester.is_authenticated or tester.role != User.Role.TESTER:
        raise PermissionDenied
    with transaction.atomic():
        rounds = workspace_records(tester, Round).exclude(state=Round.State.DRAFT)
        if write:
            rounds = rounds.select_for_update()
        round_ = get_object_or_404(rounds, pk=round_id)
        case = get_object_or_404(round_.cases, pk=case_id)
        build = get_object_or_404(round_.builds.filter(cases=case), pk=build_id)
        if round_.state != Round.State.OPEN:
            raise Conflict(
                "This action is not available while the round is "
                f"{round_.get_state_display()}."
            )
        if round_.builds.filter(cases=case).order_by("-pk").first().pk != build.pk:
            raise Conflict(STALE)
        result = Result.objects.filter(tester=tester, case=case, build=build).first()
        if write and result is not None and result.submitted_at is not None:
            raise Conflict(SUBMITTED)
        yield Entry(tester, round_, case, build, result)


def save(current, outcome, observation, *, submit=False):
    """Persist validated fields inside `entry(..., write=True)`; never delete."""
    result = current.result or Result(
        tester=current.tester, case=current.case, build=current.build
    )
    if result.submitted_at is not None:
        raise Conflict(SUBMITTED)
    result.outcome = outcome
    result.observation = observation
    if submit:
        result.submitted_at = timezone.now()
    result.save()
    current.result = result
    return result
