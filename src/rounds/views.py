"""The coordinator's round pages (RND-1), under the rules for every round action."""

import logging
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.workspaces import workspace_records

from .forms import RoundForm
from .models import Round
from .services import RoundLimitReached, create_round

logger = logging.getLogger(__name__)


def coordinator_view(methods):
    """Make a rounds view accepting `methods`, with every shared layer in order.

    Outermost, `never_cache` marks every response it returns, 405s included;
    then the method check (405); then sign-in and role before any lookup, with
    any storage failure, including loading the session or user, as the 503.
    """

    def decorate(view):
        @wraps(view)
        def checked(request, *args, **kwargs):
            try:
                if not request.user.is_authenticated:
                    return redirect("accounts:sign-in")
                if request.user.role != User.Role.COORDINATOR:
                    raise PermissionDenied
                return view(request, *args, **kwargs)
            except DatabaseError:
                logger.exception("A round request failed in storage.")
                return render(request, "503.html", status=503)

        return never_cache(require_http_methods(methods)(checked))

    return decorate


def own_round(request, round_id, *, lock=False):
    """Return the user's workspace's round, or 404 for any other or missing."""
    rounds = workspace_records(request.user, Round)
    if lock:
        rounds = rounds.select_for_update()
    return get_object_or_404(rounds, pk=round_id)


def state_conflict(request, round_):
    """Refuse an action the round's state does not allow."""
    context = {"state": round_.get_state_display()}
    return render(request, "rounds/conflict.html", context, status=409)


def form_page(request, form, title, button):
    """Show the round title form."""
    context = {"form": form, "title": title, "button": button}
    return render(request, "rounds/round_form.html", context)


@coordinator_view(["GET", "POST"])
def new_round(request):
    """Create a Draft round in the signed-in coordinator's workspace."""
    if request.method == "GET":
        return form_page(request, RoundForm(), "New round", "Create round")
    form = RoundForm(request.POST)
    if form.is_valid():
        try:
            made = create_round(request.user.workspace, form.cleaned_data["title"])
        except RoundLimitReached as limit:
            form.add_error("title", str(limit))
        else:
            return redirect(made)
    return form_page(request, form, "New round", "Create round")


@coordinator_view(["GET"])
def round_page(request, round_id):
    """Show a round's title and state."""
    return render(request, "rounds/round.html", {"round": own_round(request, round_id)})


@coordinator_view(["GET", "POST"])
def edit_round(request, round_id):
    """Change a Draft round's title."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    if request.method == "GET":
        form = RoundForm(initial={"title": round_.title})
        return form_page(request, form, "Edit round", "Save")
    form = RoundForm(request.POST)
    if not form.is_valid():
        return form_page(request, form, "Edit round", "Save")
    with transaction.atomic():
        round_ = own_round(request, round_id, lock=True)
        if round_.state != Round.State.DRAFT:
            return state_conflict(request, round_)
        round_.title = form.cleaned_data["title"]
        round_.save(update_fields=["title"])
    return redirect(round_)
