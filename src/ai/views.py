"""The Test Coordinator's transient AI drafting pages (RND-8)."""

import json
import logging

from django.db import DatabaseError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from rounds import services
from rounds.forms import CaseForm
from rounds.models import Round
from rounds.views import coordinator_view, own_round, state_conflict

from . import drafting, gateway
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
    """Return one gateway call's drafts and error message (RND-8.1, 8.4-8.6)."""
    labels = [f"C{index}" for index in range(1, len(selected) + 1)]
    text = [
        {"label": label, "text": drafting.clean(item.text).strip()}
        for label, item in zip(labels, selected, strict=True)
    ]
    if not any(item["text"] for item in text):
        return [], drafting.NO_DRAFTS
    data = json.dumps({"criteria": text}, ensure_ascii=False)
    try:
        result = gateway.complete(user, drafting.INSTRUCTIONS, data)
    except DatabaseError:
        raise
    except Exception:  # noqa: BLE001 - fixed user-facing failure
        logger.warning("Drafting gateway raised")
        result = gateway.Failed("provider-error")
    if not isinstance(result, gateway.Success):
        logger.warning("Drafting gateway %s: %s", type(result).__name__, result.code)
        return [], drafting.UNKNOWN
    try:
        parsed = drafting.parse(result.text, labels)
    except drafting.InvalidReply as invalid:
        logger.warning("Drafting reply rejected: %s", invalid.code)
        return [], drafting.UNKNOWN
    if not parsed:
        return [], drafting.NO_DRAFTS
    order = {label: i for i, label in enumerate(labels)}
    by_label = dict(zip(labels, selected, strict=True))
    drafts = []
    for item in parsed:
        covered = [by_label[label] for label in sorted(item.criteria, key=order.get)]
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
        if not 1 <= len(selected) <= drafting.MAX_CRITERIA:
            selection_error = drafting.SELECT
        elif round_.cases.count() >= services.CASE_LIMIT:
            selection_error = services.CASE_LIMIT_MESSAGE
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
