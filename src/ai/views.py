"""The Test Coordinator's transient AI drafting pages (RND-8)."""

import logging

from django.db import DatabaseError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from rounds.forms import CaseForm
from rounds.models import Round
from rounds.services import CASE_LIMIT
from rounds.views import coordinator_view, own_round, state_conflict

from . import drafting, failures, gateway
from .forms import DraftSelectForm

logger = logging.getLogger(__name__)


def _posted_text(request, name, limit, *, title=False):
    """Return a cleaned posted field, or "" when over twice its RND-2 limit."""
    value = request.POST.get(name, "")
    if len(value) > 2 * limit:
        return ""
    return drafting.clean(value, title=title)


@sensitive_variables()
def _suggest(user, selected):
    """Return transient drafts and an error message for `selected` (RND-8.4-8.10)."""
    labels = drafting.labels(len(selected))
    data = drafting.encode([item.text for item in selected])
    if data is None:
        return [], drafting.NO_DRAFTS
    try:
        result = gateway.complete(user, drafting.INSTRUCTIONS, data)
    except DatabaseError:
        raise
    except Exception:  # noqa: BLE001 - fixed user-facing failure
        logger.warning("Drafting gateway raised")
        result = gateway.Failed("provider-error")
    if not isinstance(result, gateway.Success):
        logger.warning("Drafting gateway %s: %s", type(result).__name__, result.code)
        return [], failures.message(
            result,
            unavailable=drafting.UNAVAILABLE,
            not_set_up=drafting.NOT_SET_UP,
            manual=drafting.MANUAL,
        )
    try:
        parsed = drafting.parse(result.text, labels)
    except drafting.InvalidReply as invalid:
        logger.warning("Drafting reply rejected: %s", invalid.code)
        return [], drafting.UNAVAILABLE
    if not parsed:
        return [], drafting.NO_DRAFTS
    drafts = []
    for item in parsed:
        covered = [
            criterion
            for label, criterion in zip(labels, selected, strict=True)
            if label in item.criteria
        ]
        drafts.append(
            {
                "title": item.title,
                "steps": item.steps,
                "expected_result": item.expected_result,
                "covered": covered,
                "ids": [criterion.pk for criterion in covered],
            }
        )
    return drafts, None


@coordinator_view(["GET", "POST"])
@sensitive_post_parameters("criteria")
@sensitive_variables("selected", "drafts", "error", "context")
def draft_page(request, round_id):
    """Show the drafting selection, then transient suggestions (RND-8.1-8.8)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    form = DraftSelectForm(round_, request.POST if request.method == "POST" else None)
    drafts, error, selection_error = [], None, ""
    if request.method == "POST" and form.is_valid():
        selected = list(form.cleaned_data["criteria"])
        if not 1 <= len(selected) <= 5:
            selection_error = drafting.SELECT
        elif round_.cases.count() >= CASE_LIMIT:
            selection_error = (
                f"This round has reached its limit of {CASE_LIMIT} test cases."
            )
        else:
            drafts, error = _suggest(request.user, selected)
    context = {
        "form": form,
        "round": round_,
        "drafts": drafts,
        "error": error,
        "selection_error": selection_error,
    }
    return render(request, "ai/draft.html", context)


@coordinator_view(["POST"])
@sensitive_post_parameters("title", "steps", "expected_result", "criteria")
@sensitive_variables("posted", "own", "chosen", "initial", "form")
def use_draft(request, round_id):
    """Pre-fill the normal New test case form from posted draft text (RND-8.2)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    posted = set(request.POST.getlist("criteria"))
    own = {str(item.pk): item for item in round_.criteria.all()}
    chosen = [item for key, item in own.items() if key in posted]
    initial = {
        "title": _posted_text(request, "title", drafting.TITLE_LIMIT, title=True),
        "steps": _posted_text(request, "steps", drafting.STEPS_LIMIT),
        "expected_result": _posted_text(
            request, "expected_result", drafting.EXPECTED_LIMIT
        ),
        "criteria": [item.pk for item in chosen],
    }
    form = CaseForm(round_, initial=initial)
    context = {
        "form": form,
        "title": "New test case",
        "button": "Add test case",
        "round": round_,
        "prefilled": True,
        "form_action": reverse("rounds:case-new", args=[round_.pk]),
    }
    return render(request, "rounds/round_form.html", context)
