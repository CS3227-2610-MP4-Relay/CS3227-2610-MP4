"""Shared preflight and reporting for the explicit operator experiment commands."""

import json
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.views.decorators.debug import sensitive_variables

from . import gateway


@sensitive_variables()
def preflight(options, corpus, count, refusal):
    """Return the operator, configured model and corpus, or refuse with no call.

    `corpus` builds the fixed cases; any failed check raises `CommandError`
    with only the fixed `refusal` text.
    """
    try:
        if not (
            options["live"]
            and settings.SOC_LLM_LIVE
            and re.fullmatch(r"[0-9a-f]{40}", options["revision"])
            and (model := gateway.configured_model())
        ):
            raise ValueError
        user = get_user_model().objects.get(pk=options["user_id"])
        cases = corpus()
        if (
            len(cases) != count
            or len({case.id for case in cases}) != count
            or any(
                len(case.instructions) + len(case.data) > gateway.INPUT_LIMIT
                for case in cases
            )
        ):
            raise ValueError
    except Exception:  # noqa: BLE001 - only fixed preflight text is exposed
        raise CommandError(refusal) from None
    return user, model, cases


@sensitive_variables()
def show_response(stderr, case, result):
    """Write one escaped untrusted reply line for a `Success` (SEC-INJ-1.5)."""
    if isinstance(result, gateway.Success):
        stderr.write(
            json.dumps({"id": case.id, "response": result.text}, ensure_ascii=True),
            style_func=lambda text: text,
        )


def status(result):
    """Name a gateway result's outcome; anything else is unattempted."""
    if isinstance(result, gateway.Success):
        return "success"
    if isinstance(result, gateway.Refused):
        return "refused"
    if isinstance(result, gateway.Failed):
        return "failed"
    return "unattempted"
