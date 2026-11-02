"""Explicit synthetic comparison; no provider execution by pytest or CI."""

import json
import os
import re
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.views.decorators.debug import sensitive_variables

from ai import context_comparison as comparison
from ai import drafting, feedback, gateway


class Command(BaseCommand):
    """Run eight paired requests with text-free summaries and opt-in inspection."""

    help = "Compare selected and broader synthetic context; requires --live."

    def add_arguments(self, parser):
        """Require explicit execution, operator identity and source revision."""
        parser.add_argument("--live", action="store_true")
        parser.add_argument("--show-responses", action="store_true")
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument("--revision", required=True)

    @sensitive_variables()
    def handle(self, *args, **options):
        """Preflight all pairs, then run once through normal accounting."""
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
            cases = comparison.corpus()
            if (
                len(cases) != 8
                or len({c.id for c in cases}) != 8
                or any(
                    len(c.instructions) + len(c.data) > gateway.INPUT_LIMIT
                    for c in cases
                )
            ):
                raise ValueError
        except Exception:  # noqa: BLE001 - expose only fixed preflight text
            raise CommandError("Comparison preflight refused; no calls made.") from None
        rows, interrupted, invocations = [], False, 0
        for case in cases:
            result, elapsed = None, None
            if not interrupted:
                invocations += 1
                started = time.monotonic()
                try:
                    result = gateway.complete(user, case.instructions, case.data)
                    elapsed = int(max(0, time.monotonic() - started) * 1000)
                except Exception:  # noqa: BLE001 - never expose exception text
                    result, interrupted = gateway.Failed("comparison-interrupted"), True
            if options["show_responses"] and isinstance(result, gateway.Success):
                self.stderr.write(
                    json.dumps(
                        {"id": case.id, "response": result.text}, ensure_ascii=True
                    ),
                    style_func=lambda text: text,
                )
            rows.append(
                {**comparison.score(case, result), "command_elapsed_ms": elapsed}
            )
        self.stdout.write(
            json.dumps(
                {
                    "revision": options["revision"],
                    "model": model,
                    "corpus_version": comparison.CORPUS_VERSION,
                    "instructions_versions": {
                        "drafting": drafting.INSTRUCTIONS_VERSION,
                        "feedback": feedback.INSTRUCTIONS_VERSION,
                    },
                    "invocations": invocations,
                    "cases": rows,
                }
            )
        )
        if interrupted:
            raise CommandError("Comparison interrupted; remaining cases unavailable.")
