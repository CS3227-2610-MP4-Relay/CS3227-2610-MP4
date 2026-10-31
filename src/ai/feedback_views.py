"""Explicit, transient feedback for the authenticated tester's draft (RES-4)."""

import logging

from django.db import DatabaseError, connection
from django.shortcuts import render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from rounds import results
from rounds.tester import tester_view

from . import feedback, gateway

logger = logging.getLogger(__name__)
UNAVAILABLE = (
    "Feedback is unavailable right now. You can still edit your result yourself."
)
EMPTY = "No missing details were suggested. You can still edit your result yourself."
TOO_LONG = (
    "This observation and test case are too long for feedback. "
    "You can still edit your result yourself."
)
CHANGED = "Your saved draft or test case changed. Reload before requesting feedback."


@sensitive_variables()
def _load(user, round_id, case_id, build_id):
    """Read authorized eligible source fully inside a short read transaction."""
    with results.entry(user, round_id, case_id, build_id) as entry:
        if entry.result is None:
            raise results.Conflict("Save a draft before requesting feedback.")
        if entry.result.submitted_at is not None:
            raise results.Conflict(results.SUBMITTED)
        criteria = list(entry.case.criteria.filter(round=entry.round).order_by("pk"))
        return entry, criteria, feedback.snapshot(entry, criteria)


@tester_view(methods=("GET", "POST"))
@sensitive_post_parameters()
@sensitive_variables()
def feedback_page(request, round_id, case_id, build_id):
    """Show source and, on POST only, rechecked questions without writing it."""
    try:
        entry, criteria, source = _load(request.user, round_id, case_id, build_id)
        questions, message = [], ""
        if request.method == "POST":
            try:
                data = feedback.encode(source)
            except feedback.InputTooLarge:
                message = TOO_LONG
            else:
                # Tests may have an outer rollback transaction; runtime does not.
                if not connection.in_atomic_block:
                    connection.close()
                try:
                    result = gateway.complete(request.user, feedback.INSTRUCTIONS, data)
                except DatabaseError:
                    raise
                except Exception:  # noqa: BLE001 - fixed failure, no exception text
                    logger.warning("Feedback gateway failed")
                    result = gateway.Failed("provider-error")
                entry, criteria, current = _load(
                    request.user, round_id, case_id, build_id
                )
                if current != source:
                    raise results.Conflict(CHANGED)
                message = UNAVAILABLE
                if isinstance(result, gateway.Success):
                    try:
                        questions = feedback.parse(result.text)
                    except feedback.InvalidReply as invalid:
                        logger.warning("Feedback reply rejected: %s", invalid.code)
                    else:
                        message = "" if questions else EMPTY
        return render(
            request,
            "ai/feedback.html",
            {
                "entry": entry,
                "criteria": criteria,
                "questions": questions,
                "message": message,
            },
        )
    except results.Conflict as conflict:
        return render(
            request, "ai/feedback.html", {"conflict": str(conflict)}, status=409
        )
