"""Explicit, bounded SoC repeatability probe; never run by pytest or CI.

Run from the repo root with its virtual environment. Without --live this prints
the schedule only, without loading .env or opening a provider connection.
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.base"
django.setup()

from ai import context_comparison, drafting, feedback, gateway
from relay.settings.dotenv import load_dotenv

MODELS = ("llama3.1:8b", "qwen3.6:35b", "x-test-2")
TARGETS = ("drafting-boundary", "feedback-complete")
REPEATS = 5
ORDER_SEED = 20261109


def digest(value):
    """Return a SHA-256 without retaining its source text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_hash(model, case):
    """Hash exactly the JSON bytes built by the current gateway transport."""
    return digest(
        json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": case.instructions},
                    {"role": "user", "content": case.data},
                ],
                "temperature": 0,
                "stream": False,
            },
            ensure_ascii=False,
        )
    )


def schedule():
    """Interleave all 12 model/input cells within each of five shuffled blocks."""
    cases = [
        case
        for case in context_comparison.corpus()
        if any(case.id.startswith(target + "-") for target in TARGETS)
    ]
    if len(cases) != 4 or any(
        len(case.instructions) + len(case.data) > gateway.INPUT_LIMIT for case in cases
    ):
        raise ValueError("Unexpected or oversized fixed corpus.")
    rng = random.Random(ORDER_SEED)
    result = []
    for repeat in range(1, REPEATS + 1):
        block = [(model, case) for model in MODELS for case in cases]
        rng.shuffle(block)
        result.extend((repeat, model, case) for model, case in block)
    return result


def observe(result, case):
    """Keep only equality hashes and structural observations, never reply text."""
    row = context_comparison.score(case, result)
    row.update(reply_sha256=None, validated_sha256=None)
    if isinstance(result, gateway.Success):
        row["reply_sha256"] = digest(result.text)
        try:
            parsed = (
                [asdict(item) for item in drafting.parse(result.text, ["C1"])]
                if case.feature == "drafting"
                else feedback.parse(result.text)
            )
        except drafting.InvalidReply:
            pass
        else:
            row["validated_sha256"] = digest(
                json.dumps(parsed, sort_keys=True, ensure_ascii=False)
            )
    else:
        row["code"] = result.code
    return row


def main():
    """Print a safe schedule, or execute exactly one bounded live pilot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    jobs = schedule()
    if not args.live:
        print(
            json.dumps(
                {
                    "calls_if_live": len(jobs),
                    "temperature": 0,
                    "repeats": REPEATS,
                    "order_seed": ORDER_SEED,
                    "cells": [
                        {
                            "model": model,
                            "id": case.id,
                            "request_sha256": request_hash(model, case),
                        }
                        for _, model, case in jobs[:12]
                    ],
                },
                indent=2,
            )
        )
        return 0
    if args.output is None:
        parser.error("--live requires --output (a new JSONL file)")
    # Explicit operator authorization is required before using this mode.
    # This local probe calls the existing transport, outside app DB accounting.
    load_dotenv()
    if gateway._configuration() is None:
        print("Probe refused: missing or invalid SoC configuration.", file=sys.stderr)
        return 1
    with args.output.open("x", encoding="utf-8") as output:
        for ordinal, (repeat, model, case) in enumerate(jobs, 1):
            os.environ["SOC_LLM_MODEL"] = model
            started_at = datetime.now(UTC).isoformat()
            start = time.monotonic()
            result = gateway._transport(
                case.instructions, case.data, start + gateway.TOTAL_TIMEOUT
            )
            row = {
                "ordinal": ordinal,
                "repeat": repeat,
                "model": model,
                "started_at": started_at,
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "request_sha256": request_hash(model, case),
                **observe(result, case),
            }
            line = json.dumps(row, ensure_ascii=True)
            output.write(line + "\n")
            output.flush()
            print(line, flush=True)
            if isinstance(result, gateway.Refused) and result.code in {
                "quota",
                "not-configured",
                "live-off",
            }:
                print("Probe stopped after provider/configuration refusal.")
                return 1
            time.sleep(1)  # Serial calls, at most 60/minute; no automatic retries.
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - suppress private error text
        # Configuration, provider data and exception text must remain private.
        print("Probe stopped; inspect the saved numeric/hash rows.", file=sys.stderr)
        raise SystemExit(1) from None
