"""Bounded nine-call operator pilot; default mode is an offline preflight only."""

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.base"
django.setup()

from ai import drafting, feedback, gateway
from relay.settings.dotenv import load_dotenv

MODELS = ("llama3.1:8b", "qwen3.6:35b", "x-test-2")
FIXTURE_HASH = "2b07171b2b0a04808fd3127af8214d92f8258327c0c37393ac04ed8a7bf5e8d8"
ORDER_SEED = 20261109


def digest(value):
    """Hash bytes without retaining their source."""
    return hashlib.sha256(value).hexdigest()


def jobs():
    """Preflight the exact three targets and produce the bounded shuffled plan."""
    raw = (HERE / "fixtures.json").read_bytes()
    if digest(raw) != FIXTURE_HASH:
        raise ValueError("Frozen fixtures changed")
    scenarios = json.loads(raw)["scenarios"]
    if len(scenarios) != 3 or {s["id"] for s in scenarios} != {"D1", "F2", "F3"}:
        raise ValueError("Unexpected corpus")
    result = []
    for scenario in scenarios:
        feature = drafting if scenario["feature"] == "drafting" else feedback
        data = json.dumps(scenario["data"], ensure_ascii=False)
        if len(feature.INSTRUCTIONS) + len(data) > gateway.INPUT_LIMIT:
            raise ValueError("Oversized target")
        result.extend((model, scenario, feature, data) for model in MODELS)
    random.Random(ORDER_SEED).shuffle(result)
    return result


def observe(result, scenario):
    """Return safe measurements and a transient accepted candidate, if any."""
    status = (
        "success"
        if isinstance(result, gateway.Success)
        else "refused"
        if isinstance(result, gateway.Refused)
        else "failed"
    )
    usage = gateway._checked_usage(result.usage)
    row = {
        "status": status,
        "code": None if status == "success" else result.code,
        "schema_accepted": None,
        "schema_error": None,
        "accepted_items": None,
        "reply_sha256": None,
        "validated_sha256": None,
        **{key: getattr(usage, key, None) for key in gateway.TOKEN_FIELDS},
    }
    candidate = None
    if status == "success":
        row["reply_sha256"] = digest(result.text.encode("utf-8"))
        try:
            if scenario["feature"] == "drafting":
                labels = [item["label"] for item in scenario["data"]["criteria"]]
                items = [asdict(item) for item in drafting.parse(result.text, labels)]
                candidate = {"drafts": items}
            else:
                items = feedback.parse(result.text)
                candidate = {"questions": items}
        except drafting.InvalidReply as error:
            row.update(schema_accepted=False, schema_error=error.code)
        else:
            row.update(
                schema_accepted=True,
                accepted_items=len(items),
                validated_sha256=digest(
                    json.dumps(candidate, sort_keys=True, ensure_ascii=True).encode()
                ),
            )
    return row, candidate


def main():
    """Print an offline plan or run at most nine explicitly authorized attempts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--show-candidates", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    schedule = jobs()
    if not args.live:
        if args.show_candidates:
            parser.error("--show-candidates requires --live")
        print(
            json.dumps(
                {
                    "calls_if_live": len(schedule),
                    "models": MODELS,
                    "scenarios": ["D1", "F2", "F3"],
                    "condition": "relevant-only",
                    "temperature": 0,
                    "repetitions": 1,
                    "order_seed": ORDER_SEED,
                    "fixtures_sha256": FIXTURE_HASH,
                },
                indent=2,
            )
        )
        return 0
    if args.output is None or args.output.exists():
        parser.error("--live requires --output pointing to a new file")
    load_dotenv()
    for model in MODELS:
        os.environ["SOC_LLM_MODEL"] = model
        if gateway._configuration() is None:
            raise ValueError("Configuration unavailable")
    runner_hash = digest(Path(__file__).read_bytes())
    method_hash = digest((HERE / "live-method.md").read_bytes())
    with args.output.open("x", encoding="utf-8") as output:
        for ordinal, (model, scenario, feature, data) in enumerate(schedule, 1):
            os.environ["SOC_LLM_MODEL"] = model
            call_id = f"live-{ordinal:02d}"
            started_at = datetime.now(UTC).isoformat()
            started = time.monotonic()
            result = gateway._transport(
                feature.INSTRUCTIONS, data, started + gateway.TOTAL_TIMEOUT
            )
            elapsed = int((time.monotonic() - started) * 1000)
            observations, candidate = observe(result, scenario)
            request = {
                "model": model,
                "messages": [
                    {"role": "system", "content": feature.INSTRUCTIONS},
                    {"role": "user", "content": data},
                ],
                "temperature": 0,
                "stream": False,
            }
            row = {
                "id": call_id,
                "ordinal": ordinal,
                "scenario": scenario["id"],
                "model": model,
                "started_at": started_at,
                "elapsed_ms": elapsed,
                "request_sha256": digest(
                    json.dumps(request, ensure_ascii=False).encode("utf-8")
                ),
                "fixtures_sha256": FIXTURE_HASH,
                "runner_sha256": runner_hash,
                "method_sha256": method_hash,
                "instructions_version": feature.INSTRUCTIONS_VERSION,
                **observations,
            }
            output.write(json.dumps(row, ensure_ascii=True) + "\n")
            output.flush()
            view = {
                "id": call_id,
                "scenario": scenario["id"],
                "status": row["status"],
                "schema_accepted": row["schema_accepted"],
                "schema_error": row["schema_error"],
            }
            if args.show_candidates and candidate is not None:
                view["untrusted_candidate"] = candidate
            print(json.dumps(view, ensure_ascii=True), flush=True)
            if isinstance(result, gateway.Refused):
                print("Pilot stopped after refusal; no retry.", flush=True)
                return 1
            time.sleep(1)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - suppress private text
        print("Pilot stopped; inspect saved measurement rows.", file=sys.stderr)
        raise SystemExit(1) from None
