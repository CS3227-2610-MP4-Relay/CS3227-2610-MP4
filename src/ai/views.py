"""The Test Coordinator's transient AI drafting pages (RND-8)."""

import json
import logging

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from rounds.forms import CaseForm
from rounds.models import Round
from rounds.services import CASE_LIMIT
from rounds.views import coordinator_view, own_round, state_conflict

from . import drafting, gateway
from .forms import DraftSelectForm

logger = logging.getLogger(__name__)


def _form(round_, data=None):
    form = DraftSelectForm(round_, data)
    form.fields["criteria"].error_messages.update(
        {"invalid_choice": drafting.FOREIGN, "invalid_pk_value": drafting.FOREIGN}
    )
    return form


@never_cache
@coordinator_view(["GET", "POST"])
@sensitive_post_parameters("criteria")
def draft_page(request, round_id):
    """Show the drafting selection, then transient suggestions (RND-8.1-8.8)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    form = _form(round_, request.POST if request.method == "POST" else None)
    drafts, error, selection_error, selected = [], None, "", []
    if request.method == "POST" and form.is_valid():
        selected = list(form.cleaned_data["criteria"])
        if not 1 <= len(selected) <= 5:
            selection_error = drafting.SELECT
        elif round_.cases.count() >= CASE_LIMIT:
            selection_error = (
                f"This round has reached its limit of {CASE_LIMIT} test cases."
            )
        else:
            labels = [f"C{index}" for index in range(1, len(selected) + 1)]
            text = [
                {"label": label, "text": drafting.clean(item.text).strip()}
                for label, item in zip(labels, selected, strict=True)
            ]
            if not any(item["text"] for item in text):
                error = drafting.NO_DRAFTS
            else:
                data = json.dumps({"criteria": text}, ensure_ascii=False)
                try:
                    result = gateway.complete(request.user, drafting.INSTRUCTIONS, data)
                except Exception:  # noqa: BLE001 - fixed user-facing failure
                    logger.warning("Drafting gateway raised")
                    result = gateway.Failed("provider-error")
                if isinstance(result, gateway.Success):
                    try:
                        parsed = drafting.parse(result.text, labels)
                    except drafting.InvalidReply as invalid:
                        logger.warning("Drafting reply rejected: %s", invalid.code)
                        error = drafting.UNKNOWN
                    else:
                        if not parsed:
                            error = drafting.NO_DRAFTS
                        else:
                            order = {label: i for i, label in enumerate(labels)}
                            by_label = dict(zip(labels, selected, strict=True))
                            drafts = [
                                {
                                    "title": item.title,
                                    "steps": item.steps,
                                    "expected_result": item.expected_result,
                                    "covered": [
                                        by_label[label]
                                        for label in sorted(
                                            item.criteria, key=order.get
                                        )
                                    ],
                                    "ids": [
                                        by_label[label].pk
                                        for label in sorted(
                                            item.criteria, key=order.get
                                        )
                                    ],
                                }
                                for item in parsed
                            ]
                else:
                    logger.warning(
                        "Drafting gateway %s: %s",
                        type(result).__name__,
                        result.code,
                    )
                    error = drafting.UNKNOWN
    context = {
        "form": form,
        "round": round_,
        "drafts": drafts,
        "error": error,
        "selection_error": selection_error,
    }
    return render(request, "ai/draft.html", context)


@never_cache
@coordinator_view(["POST"])
@sensitive_post_parameters("title", "steps", "expected_result", "criteria")
def use_draft(request, round_id):
    """Pre-fill the normal New test case form from posted draft text (RND-8.2)."""
    round_ = own_round(request, round_id)
    if round_.state != Round.State.DRAFT:
        return state_conflict(request, round_)
    posted = set(request.POST.getlist("criteria"))
    own = {str(item.pk): item for item in round_.criteria.all()}
    chosen = [item for key, item in own.items() if key in posted]
    initial = {
        "title": drafting.clean(request.POST.get("title", ""), title=True),
        "steps": drafting.clean(request.POST.get("steps", "")),
        "expected_result": drafting.clean(request.POST.get("expected_result", "")),
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
