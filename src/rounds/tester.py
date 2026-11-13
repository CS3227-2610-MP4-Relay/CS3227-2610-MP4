"""Tester availability, private result entry and read-only history (RES)."""

import logging
from collections import Counter
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.workspaces import workspace_records

from . import results
from .models import Criterion, Round
from .result_forms import ResultForm
from .views import conflict_page

logger = logging.getLogger(__name__)


def tester_view(view=None, *, methods=("GET",)):
    """Check method and tester role before reads, including lazy authentication."""
    if view is None:
        return lambda wrapped: tester_view(wrapped, methods=methods)

    @wraps(view)
    def checked(request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return redirect("accounts:sign-in")
            if request.user.role != User.Role.TESTER:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        except DatabaseError:
            logger.error("A tester request failed in storage.")
            return render(request, "503.html", status=503)

    return never_cache(require_http_methods(methods)(checked))


def available_rounds(user):
    """Return the tester's workspace's published rounds, newest first."""
    return workspace_records(user, Round).filter(
        state__in=[Round.State.OPEN, Round.State.CLOSED]
    )


# Each RES-1.5 action and the RES-1.9 status naming the same classification.
STATUSES = {
    "Record result": "Not recorded",
    "Continue draft": "Draft",
    "View result": "Submitted",
}


def classified_cases(tester, round_):
    """Return the round's cases, each with the tester's own current-build action.

    Only an Open round reads results; one query covers every case. A case's
    `result_action` and `result_status` follow its row for its current build.
    """
    cases = results.cases_with_current_build(round_)
    saved = (
        {
            (case_id, build_id): submitted_at
            for case_id, build_id, submitted_at in results.covered_results(round_)
            .filter(
                tester=tester,
                case_id__in=[case.pk for case in cases],
                build_id__in=[
                    case.current_build.pk for case in cases if case.current_build
                ],
            )
            .values_list("case_id", "build_id", "submitted_at")
        }
        if round_.state == Round.State.OPEN
        else {}
    )
    for case in cases:
        pair = (case.pk, case.current_build.pk) if case.current_build else None
        if pair not in saved:
            case.result_action = "Record result"
        elif saved[pair] is None:
            case.result_action = "Continue draft"
        else:
            case.result_action = "View result"
        case.result_status = STATUSES[case.result_action]
    return cases


@tester_view
def home(request):
    """List the rounds this tester can read, Open first, with own Open progress."""
    rounds = list(available_rounds(request.user))
    open_rounds = [round_ for round_ in rounds if round_.state == Round.State.OPEN]
    closed_rounds = [round_ for round_ in rounds if round_.state != Round.State.OPEN]
    for round_ in open_rounds:
        actions = Counter(
            case.result_action for case in classified_cases(request.user, round_)
        )
        round_.progress = [actions[action] for action in STATUSES]
    return render(
        request,
        "rounds/tester_home.html",
        {
            "title": "Tester home",
            "rounds": open_rounds + closed_rounds,
            "open_rounds": open_rounds,
            "closed_rounds": closed_rounds,
        },
    )


@tester_view
def detail(request, round_id):
    """Show cases and latest covering builds in one authorized published round."""
    round_ = get_object_or_404(available_rounds(request.user), pk=round_id)
    cases = classified_cases(request.user, round_)
    return render(
        request, "rounds/tester_round.html", {"round": round_, "cases": cases}
    )


@tester_view
def history(request, round_id):
    """Read this tester's saved results with their original authorized context."""
    round_ = get_object_or_404(available_rounds(request.user), pk=round_id)
    saved = (
        results.covered_results(round_)
        .filter(tester=request.user)
        .select_related("case", "build")
        .prefetch_related(
            Prefetch("case__criteria", queryset=Criterion.objects.filter(round=round_))
        )
        .order_by("-build_id", "case_id")
    )
    return render(
        request, "rounds/tester_history.html", {"round": round_, "results": saved}
    )


@tester_view(methods=("GET", "POST"))
def result_entry(request, round_id, case_id, build_id):
    """Read or write only the signed-in tester's current-build result."""
    try:
        with results.entry(
            request.user, round_id, case_id, build_id, write=request.method == "POST"
        ) as current:
            saved = current.result
            if request.method == "POST":
                results.check_revision(current, request.POST.get("revision"))
            form = ResultForm(
                request.POST if request.method == "POST" else None,
                initial={
                    "outcome": saved.outcome if saved else "",
                    "observation": saved.observation if saved else "",
                    "revision": saved.revision if saved else 0,
                },
            )
            if request.method == "POST" and form.is_valid():
                results.save(
                    current,
                    form.cleaned_data["outcome"],
                    form.cleaned_data["observation"],
                    revision=form.cleaned_data["revision"],
                    submit=form.cleaned_data["action"] == "submit",
                )
                destination = (
                    "accounts:tester-feedback"
                    if form.cleaned_data["action"] == "feedback"
                    else "accounts:tester-result"
                )
                return redirect(destination, round_id, case_id, build_id)
            return render(
                request, "rounds/tester_result.html", {"entry": current, "form": form}
            )
    except results.Conflict as conflict:
        return conflict_page(
            request,
            str(conflict),
            back=reverse("accounts:tester-round", args=[round_id]),
        )
