"""Explicit operator evaluation; never invoked by pytest or CI against a provider."""

import json

from django.core.management.base import BaseCommand, CommandError
from django.views.decorators.debug import sensitive_variables

from ai import drafting, evaluation, experiments, feedback, gateway


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
        user, model, cases = experiments.preflight(
            options,
            evaluation.corpus,
            12,
            "Evaluation preflight refused; no calls made.",
        )
        rows, interrupted = [], False
        for case in cases:
            if interrupted:
                result = None
            else:
                try:
                    result = gateway.complete(user, case.instructions, case.data)
                except Exception:  # noqa: BLE001 - no provider/storage exception text
                    result, interrupted = gateway.Failed("evaluation-interrupted"), True
            if options["show_responses"]:
                experiments.show_response(self.stderr, case, result)
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
