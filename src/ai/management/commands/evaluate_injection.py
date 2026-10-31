"""Explicit operator evaluation; never invoked by pytest or CI against a provider."""

import json
import os
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.views.decorators.debug import sensitive_variables

from ai import drafting, evaluation, feedback, gateway


class Command(BaseCommand):
    """Run one bounded corpus with summaries and optional untrusted reply inspection."""

    help = "Measure exact injection markers; requires explicit --live operator action."

    def add_arguments(self, parser):
        """Require the operator identity and explicitly supplied source revision."""
        parser.add_argument("--live", action="store_true")
        parser.add_argument(
            "--show-responses",
            action="store_true",
            help="Show escaped untrusted replies on stderr; do not retain.",
        )
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument("--revision", required=True)

    @sensitive_variables()
    def handle(self, *args, **options):
        """Preflight requests; expose replies only through explicit inspection."""
        try:
            key = os.environ.get("SOC_LLM_API_KEY", "").strip()
            model = os.environ.get("SOC_LLM_MODEL", "").strip()
            if not (
                options["live"]
                and settings.SOC_LLM_LIVE
                and re.fullmatch(r"[0-9a-f]{40}", options["revision"])
                and gateway._endpoint()
                and model
                and key
                and key.isascii()
                and key.isprintable()
            ):
                raise ValueError
            user = get_user_model().objects.get(pk=options["user_id"])
            cases = evaluation.corpus()
            if (
                len(cases) != 12
                or len({case.id for case in cases}) != 12
                or any(
                    len(case.instructions) + len(case.data) > gateway.INPUT_LIMIT
                    for case in cases
                )
            ):
                raise ValueError
        except Exception:  # noqa: BLE001 - only fixed preflight text is exposed
            raise CommandError("Evaluation preflight refused; no calls made.") from None
        rows, interrupted = [], False
        for case in cases:
            if interrupted:
                result = None
            else:
                try:
                    result = gateway.complete(user, case.instructions, case.data)
                except Exception:  # noqa: BLE001 - no provider/storage exception text
                    result, interrupted = gateway.Failed("evaluation-interrupted"), True
            if options["show_responses"] and isinstance(result, gateway.Success):
                self.stderr.write(
                    json.dumps(
                        {"id": case.id, "response": result.text}, ensure_ascii=True
                    )
                )
            rows.append(evaluation.score(case, result))
        self.stdout.write(
            json.dumps(
                {
                    "revision": options["revision"],
                    "model": model,
                    "corpus_version": evaluation.CORPUS_VERSION,
                    "instructions_versions": {
                        "drafting": drafting.INSTRUCTIONS_VERSION,
                        "feedback": feedback.INSTRUCTIONS_VERSION,
                    },
                    "cases": rows,
                    "totals": evaluation.aggregate(rows),
                }
            )
        )
        if interrupted:
            raise CommandError("Evaluation interrupted; remaining cases unavailable.")
