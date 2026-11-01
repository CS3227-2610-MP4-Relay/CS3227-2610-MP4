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

from . import results
from .models import Criterion, Result
from .result_forms import ResultForm
from .results import available_rounds

logger = logging.getLogger(__name__)


def tester_view(view=None, *, methods=("GET",)):
    """Make a tester view accepting `methods`, with every shared layer in order.

    Outermost, `never_cache` marks every response, 405s included; then the
    method check (405); then sign-in and the tester role before any lookup.
    Any storage failure, including loading the session or user, gives the 503.
    It logs a fixed message without the traceback, because a database error's
    text can carry a tester's observation or request fields, which must never
    be logged (RES-2); the coordinator's views log the traceback instead.
    """
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
    cases = results.cases_with_current_builds(round_)
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
    except results.StateConflict as conflict:
        context = {"state": conflict.state}
        return render(request, "rounds/conflict.html", context, status=409)
    except results.Conflict as conflict:
        return render(
            request,
            "rounds/tester_result.html",
            {"conflict": str(conflict)},
            status=409,
        )
