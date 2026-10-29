"""Tester availability, private result entry and read-only history (RES)."""

import logging
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.workspaces import workspace_records

from . import results
from .models import Build, Criterion, Result, Round
from .result_forms import ResultForm

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


@tester_view
def home(request):
    """List the rounds this tester can read."""
    return render(
        request,
        "rounds/tester_home.html",
        {"title": "Tester home", "rounds": available_rounds(request.user)},
    )


@tester_view
def detail(request, round_id):
    """Show cases and latest covering builds in one authorized published round."""
    round_ = get_object_or_404(available_rounds(request.user), pk=round_id)
    cases = list(
        round_.cases.prefetch_related(
            Prefetch("criteria", queryset=Criterion.objects.filter(round=round_)),
            Prefetch(
                "builds",
                queryset=Build.objects.filter(round=round_).order_by("-id"),
            ),
        )
    )
    for case in cases:
        case.current_build = next(iter(case.builds.all()), None)
    return render(
        request, "rounds/tester_round.html", {"round": round_, "cases": cases}
    )


@tester_view
def history(request, round_id):
    """Read this tester's saved results with their original authorized context."""
    round_ = get_object_or_404(available_rounds(request.user), pk=round_id)
    saved = (
        Result.objects.filter(
            tester=request.user,
            case__round=round_,
            build__round=round_,
            build__cases=F("case_id"),
        )
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
            form = ResultForm(
                request.POST if request.method == "POST" else None,
                initial={"outcome": saved.outcome, "observation": saved.observation}
                if saved
                else None,
            )
            if request.method == "POST" and form.is_valid():
                results.save(
                    current,
                    form.cleaned_data["outcome"],
                    form.cleaned_data["observation"],
                    submit=form.cleaned_data["action"] == "submit",
                )
                return redirect("accounts:tester-result", round_id, case_id, build_id)
            return render(
                request, "rounds/tester_result.html", {"entry": current, "form": form}
            )
    except results.Conflict as conflict:
        if str(conflict) == "This action is not available while the round is Closed.":
            return render(
                request, "rounds/conflict.html", {"state": "Closed"}, status=409
            )
        return render(
            request,
            "rounds/tester_result.html",
            {"conflict": str(conflict)},
            status=409,
        )
