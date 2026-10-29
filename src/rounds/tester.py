"""Read-only tester availability for Open and Closed workspace rounds (RES-1)."""

import logging
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from accounts.models import User
from accounts.workspaces import workspace_records

from .models import Build, Criterion, Round

logger = logging.getLogger(__name__)


def tester_view(view):
    """Check method and tester role before reads, including lazy authentication."""

    @wraps(view)
    def checked(request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return redirect("accounts:sign-in")
            if request.user.role != User.Role.TESTER:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        except DatabaseError:
            logger.exception("A tester request failed in storage.")
            return render(request, "503.html", status=503)

    return never_cache(require_GET(checked))


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
