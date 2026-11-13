"""Result entry, persistence and round-scoped reads (RES-2, RES-3, RND-4).

Entry and saving run under the shared round lock; the read helpers limit
cases, criteria, builds and results to one round for the review and history.
"""

from contextlib import contextmanager
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from accounts.workspaces import workspace_records

from .models import Build, Case, Criterion, Result, Round

STALE = "This build is no longer current. Reload the round to record a result."
SUBMITTED = "This result has already been submitted."
CHANGED = "Your saved draft changed. Reload the result before saving or submitting."


class Conflict(Exception):
    """A fixed-text state/build/submission refusal, rendered by entry as 409."""


def state_message(round_):
    """The refusal of an action `round_`'s state does not allow."""
    state = round_.get_state_display()
    return f"This action is not available while the round is {state}."


def cases_with_current_build(round_):
    """Return the round's cases with their criteria and builds limited to it.

    Each case's `current_build` is its newest covering build in the round, or
    None; the link tables alone do not tie criteria or builds to the round.
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


def covered_results(round_):
    """Return results whose case and build are in the round, the build covering it."""
    return Result.objects.filter(
        case__round=round_, build__round=round_, build__cases=F("case_id")
    )


def listed_results(round_):
    """Return the submitted results RND-4 lists: covered, by its workspace's users."""
    return covered_results(round_).filter(
        submitted_at__isnull=False, tester__workspace=round_.workspace_id
    )


def current_build_coverage(round_):
    """Count the round's cases with a listed result for their current build (RND-1).

    A case's current build is its newest covering build in the round, as in
    `cases_with_current_build`; one query, whatever the case or result count.
    """
    newest = (
        Build.objects.filter(round=round_, cases=OuterRef("case_id"))
        .order_by("-id")
        .values("id")[:1]
    )
    return (
        listed_results(round_)
        .filter(build_id=Subquery(newest))
        .values("case_id")
        .distinct()
        .count()
    )


def has_pending_drafts(round_, current):
    """Read only eligible draft existence for an authorized Open round's builds."""
    pairs = Q(pk__in=[])
    for case_id, build in current.items():
        pairs |= Q(case_id=case_id, build_id=build.pk)
    return (
        covered_results(round_)
        .filter(
            pairs,
            submitted_at__isnull=True,
            tester__workspace_id=round_.workspace_id,
            tester__role=User.Role.TESTER,
        )
        .exists()
    )


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
            raise Conflict(state_message(round_))
        if round_.builds.filter(cases=case).order_by("-pk").first().pk != build.pk:
            raise Conflict(STALE)
        result = Result.objects.filter(tester=tester, case=case, build=build).first()
        if write and result is not None and result.submitted_at is not None:
            raise Conflict(SUBMITTED)
        yield Entry(tester, round_, case, build, result)


def check_revision(current, revision):
    """Reject stale or malformed form revisions after entry's domain denials."""
    expected = str(current.result.revision if current.result else 0)
    if str(revision) != expected:
        raise Conflict(CHANGED)


def save(current, outcome, observation, *, revision, submit=False):
    """Persist validated fields inside `entry(..., write=True)`; never delete."""
    result = current.result or Result(
        tester=current.tester, case=current.case, build=current.build
    )
    if result.submitted_at is not None:
        raise Conflict(SUBMITTED)
    check_revision(current, revision)
    if current.result is not None:
        result.revision += 1
    result.outcome = outcome
    result.observation = observation
    if submit:
        result.submitted_at = timezone.now()
    result.save()
    current.result = result
    return result
