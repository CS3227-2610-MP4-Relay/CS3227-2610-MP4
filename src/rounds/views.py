"""The coordinator's round pages (RND-1 to 6), under the action rules."""

import logging
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.db.models import F, Prefetch
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.workspaces import workspace_records

from . import services
from .forms import CaseForm, CriterionForm, PublishForm, RetestForm, RoundForm
from .models import Case, Criterion, Result, Round
from .results import cases_with_current_builds
from .services import RoundLimitReached, create_round
from .templatetags.rounds_text import retest_message

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


def show_round(request, round_, refused=None, publish_form=None):
    """Render the round page; `refused` is a (criterion ID, message) pair.

    Builds come oldest first, so each case's current build is the last one
    covering it (RND-3). Linked criteria and covered cases are limited to the
    round, since the link tables do not tie them to it.
    """
    own_cases = Prefetch("cases", queryset=Case.objects.filter(round=round_))
    builds = list(round_.builds.prefetch_related(own_cases))
    current = {case.pk: build for build in builds for case in build.cases.all()}
    own_criteria = Prefetch("criteria", queryset=Criterion.objects.filter(round=round_))
    cases = list(round_.cases.prefetch_related(own_criteria))
    for case in cases:
        case.current_build = current.get(case.pk)
    draft = round_.state == Round.State.DRAFT
    context = {
        "round": round_,
        "draft": draft,
        "open": round_.state == Round.State.OPEN,
        "cases": cases,
        "builds": builds,
        "refused": refused,
        "publish_form": publish_form or (PublishForm() if draft else None),
    }
    return render(request, "rounds/round.html", context)


@coordinator_view(["GET"])
def round_page(request, round_id):
    """Show a round's title, state, criteria and cases."""
    return show_round(request, own_round(request, round_id))


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


# RND-2: each kind of record, by the round's related name.
RECORDS = {
    "criteria": (CriterionForm, "acceptance criterion"),
    "cases": (CaseForm, "test case"),
}


def url_record_id(kind, criterion_id, case_id):
    """The record ID the URL names, or None on an add route; 0 is an ID too."""
    return criterion_id if kind == "criteria" else case_id


def round_record(request, round_id, kind, record_id, *, lock=False):
    """Return the user's round and its record named in the URL, or 404."""
    round_ = own_round(request, round_id, lock=lock)
    if record_id is None:
        return round_, None
    return round_, get_object_or_404(getattr(round_, kind), pk=record_id)


def save_record(kind, round_, record, data):
    """Add a criterion or case to the locked round, or change `record`."""
    if kind == "criteria" and record is None:
        services.add_criterion(round_, data["text"])
    elif kind == "criteria":
        services.save_criterion(record, data["text"])
    else:
        ids = [item.pk for item in data.pop("criteria")]
        if record is None:
            services.add_case(round_, data, ids)
        else:
            services.save_case(record, data, ids)


@coordinator_view(["GET", "POST"])
def record_form(request, round_id, kind, criterion_id=None, case_id=None):
    """Add or edit a Draft round's criterion or case."""
    form_class, noun = RECORDS[kind]
    record_id = url_record_id(kind, criterion_id, case_id)
    round_, record = round_record(request, round_id, kind, record_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    initial = model_to_dict(record) if record is not None else None
    data = request.POST if request.method == "POST" else None
    form = form_class(round_, data, initial=initial)
    if data is not None and form.is_valid():
        # A refusal leaves the transaction by its exception, so nothing commits.
        try:
            with transaction.atomic():
                round_, record = round_record(
                    request, round_id, kind, record_id, lock=True
                )
                if round_.state != Round.State.DRAFT:
                    return state_conflict(request, round_)
                save_record(kind, round_, record, dict(form.cleaned_data))
        except services.Refused as refused:
            form.add_error(refused.field, str(refused))
        else:
            return redirect(round_)
    context = {
        "form": form,
        "title": f"{'New' if record is None else 'Edit'} {noun}",
        "button": f"Add {noun}" if record is None else "Save",
        "round": round_,
    }
    return render(request, "rounds/round_form.html", context)


@coordinator_view(["POST"])
def delete_record(request, round_id, kind, criterion_id=None, case_id=None):
    """Delete a Draft round's case, or its criterion if no case links to it."""
    record_id = url_record_id(kind, criterion_id, case_id)
    try:
        with transaction.atomic():
            round_, record = round_record(request, round_id, kind, record_id, lock=True)
            if round_.state != Round.State.DRAFT:
                return state_conflict(request, round_)
            if kind == "criteria":
                services.delete_criterion(record)
            else:
                services.delete_case(record)
    except services.Refused as refused:
        return show_round(request, round_, (record.pk, str(refused)))
    return redirect(round_)


@coordinator_view(["POST"])
def publish_round(request, round_id):
    """Open a Draft round on its first build, covering every case (RND-3)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    form = PublishForm(request.POST)
    if not form.is_valid():
        return show_round(request, round_, publish_form=form)
    # A refusal leaves the transaction by its exception, so nothing commits.
    try:
        with transaction.atomic():
            round_ = own_round(request, round_id, lock=True)
            if round_.state != Round.State.DRAFT:
                return state_conflict(request, round_)
            services.publish(round_, form.cleaned_data["label"])
    except services.Refused as refused:
        form.add_error(refused.field, str(refused))
        return show_round(request, round_, publish_form=form)
    messages.success(request, "Round published.")
    return redirect(round_)


@coordinator_view(["POST"])
def close_round(request, round_id):
    """Close an Open round for good; nothing reopens it (RND-6)."""
    with transaction.atomic():
        round_ = own_round(request, round_id, lock=True)
        if round_.state != Round.State.OPEN:
            return state_conflict(request, round_)
        services.close(round_)
    messages.success(request, "Round closed.")
    return redirect(round_)


@coordinator_view(["GET", "POST"])
def retest_round(request, round_id):
    """Ask for chosen cases of an Open round to be tested on a new build (RND-5)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.OPEN:
        return state_conflict(request, round_)
    data = request.POST if request.method == "POST" else None
    form = RetestForm(round_, data)
    if data is not None and form.is_valid():
        ids = [case.pk for case in form.cleaned_data["cases"]]
        # A refusal leaves the transaction by its exception, so nothing commits.
        try:
            with transaction.atomic():
                round_ = own_round(request, round_id, lock=True)
                if round_.state != Round.State.OPEN:
                    return state_conflict(request, round_)
                build = services.request_retest(round_, form.cleaned_data["label"], ids)
        except services.RoundNotOpen:
            round_.refresh_from_db(fields=["state"])
            return state_conflict(request, round_)
        except services.Refused as refused:
            form.add_error(refused.field, str(refused))
        else:
            # Counted from the request, so nothing reads storage after the commit.
            text = retest_message(len(set(ids)), build.label)
            messages.success(request, text, extra_tags="retest")
            return redirect(round_)
    context = {
        "form": form,
        "title": "Request a retest",
        "button": "Request retest",
        "round": round_,
    }
    return render(request, "rounds/round_form.html", context)


@coordinator_view(["GET"])
def results_page(request, round_id):
    """List an Open or Closed round's submitted results by case and build (RND-4).

    Only rows whose case and covering build are in the round and whose tester
    is in its workspace show; everything is read before rendering.
    """
    round_ = own_round(request, round_id)
    if round_.state == Round.State.DRAFT:
        return state_conflict(request, round_)
    cases = cases_with_current_builds(round_)
    submitted = (
        Result.objects.filter(
            submitted_at__isnull=False,
            case__round=round_,
            build__round=round_,
            build__cases=F("case_id"),
            tester__workspace=round_.workspace_id,
        )
        .select_related("tester", "build")
        .order_by("-build_id", "-submitted_at", "-id")
    )
    by_case = {}
    for result in submitted:
        by_case.setdefault(result.case_id, []).append(result)
    for case in cases:
        current = getattr(case.current_build, "pk", None)
        rows = by_case.get(case.pk, [])
        case.current_results = [row for row in rows if row.build_id == current]
        case.earlier_results = [row for row in rows if row.build_id != current]
    context = {"round": round_, "cases": cases}
    return render(request, "rounds/results.html", context)
