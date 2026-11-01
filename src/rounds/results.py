"""Round reads for the tester and coordinator result pages, and private entry.

Result entry and persistence run under the shared round lock (RES-2).
"""

from contextlib import contextmanager
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from accounts.workspaces import workspace_records

from .models import Build, Case, Criterion, Result, Round

STALE = "This build is no longer current. Reload the round to record a result."
SUBMITTED = "This result has already been submitted."


class Conflict(Exception):
    """A fixed-text state/build/submission refusal, rendered by entry as 409."""


class StateConflict(Conflict):
    """The round is not Open; `state` is its display name for the conflict page."""

    def __init__(self, state):
        super().__init__(f"This action is not available while the round is {state}.")
        self.state = state


def available_rounds(user):
    """Return the tester's workspace's published rounds, newest first."""
    return workspace_records(user, Round).filter(
        state__in=[Round.State.OPEN, Round.State.CLOSED]
    )


def cases_with_current_builds(round_):
    """Return the round's cases, each with its `current_build` (newest covering).

    `round_` must already be authorized for the caller: this filters by the
    round only. Linked criteria and covering builds are limited to the round,
    since the link tables do not tie them to it.
    """
    cases = list(
        round_.cases.prefetch_related(
            Prefetch("criteria", queryset=Criterion.objects.filter(round=round_)),
            Prefetch(
                "builds", queryset=Build.objects.filter(round=round_).order_by("-id")
            ),
        )
    )
    for case in cases:
        case.current_build = next(iter(case.builds.all()), None)
    return cases


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
        rounds = available_rounds(tester)
        if write:
            rounds = rounds.select_for_update()
        round_ = get_object_or_404(rounds, pk=round_id)
        case = get_object_or_404(round_.cases, pk=case_id)
        build = get_object_or_404(round_.builds.filter(cases=case), pk=build_id)
        if round_.state != Round.State.OPEN:
            raise StateConflict(round_.get_state_display())
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
