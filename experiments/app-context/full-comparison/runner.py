"""Bounded local comparison; default mode validates inputs without provider access."""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
if not apps.ready:
    os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.base"
    django.setup()

from ai import drafting, feedback, gateway
from relay.settings.dotenv import load_dotenv

MODELS = ("llama3.1:8b", "qwen3.6:35b", "x-test-2")
CONDITIONS = ("relevant-only", "app-clutter", "off-topic")
TARGETS = tuple(f"{feature}{i}" for feature in "DF" for i in range(1, 7))
REPEATS = 5
ORDER_SEED = 20261110
FIXTURE_HASH = "f39c53a3568f284d62db8f58428c5dcbc74b5b8b9a682c65aa010a92e40206b1"
SOURCE_PATHS = (
    "experiments/app-context/full-comparison/runner.py",
    "experiments/app-context/full-comparison/method.md",
    "experiments/app-context/full-comparison/rubric.md",
    "experiments/app-context/full-comparison/backgrounds.json",
    "experiments/app-context/calibration/fixtures.json",
    "experiments/app-context/calibration/clarification.md",
    "src/ai/drafting.py",
    "src/ai/feedback.py",
    "src/ai/gateway.py",
    "src/rounds/forms.py",
    "src/rounds/models.py",
)


def digest(raw):
    """Hash bytes without retaining their source."""
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    """Encode sorted object keys while preserving all array order."""
    return json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")


@dataclass(frozen=True)
class Cell:
    """One immutable model, target and background request."""

    model: str
    condition: str
    scenario: dict
    data: str

    @property
    def feature(self):
        """Return the production feature module for this target."""
        return drafting if self.scenario["feature"] == "drafting" else feedback

    @property
    def request_sha256(self):
        """Hash the exact JSON body the production transport constructs."""
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.feature.INSTRUCTIONS},
                {"role": "user", "content": self.data},
            ],
            "temperature": 0,
            "stream": False,
        }
        return digest(json.dumps(request, ensure_ascii=False).encode("utf-8"))


def cells():
    """Validate frozen calibration targets and construct exactly 108 requests."""
    raw = (HERE.parent / "calibration/fixtures.json").read_bytes()
    if digest(raw) != FIXTURE_HASH:
        raise ValueError("fixtures-changed")
    scenarios = json.loads(raw)["scenarios"]
    if [s["id"] for s in scenarios] != list(TARGETS):
        raise ValueError("invalid-targets")
    backgrounds = json.loads((HERE / "backgrounds.json").read_bytes())
    if set(backgrounds) != set(CONDITIONS[1:]) or any(
        type(value) is not str or not value.strip() for value in backgrounds.values()
    ):
        raise ValueError("invalid-backgrounds")
    result = []
    for scenario in scenarios:
        expected = "drafting" if scenario["id"].startswith("D") else "feedback"
        if scenario["feature"] != expected or "background" in scenario["data"]:
            raise ValueError("invalid-target")
        for model in MODELS:
            for condition in CONDITIONS:
                data = dict(scenario["data"], background=backgrounds.get(condition, ""))
                cell = Cell(
                    model, condition, scenario, json.dumps(data, ensure_ascii=False)
                )
                if (
                    len(cell.feature.INSTRUCTIONS) + len(cell.data)
                    > gateway.INPUT_LIMIT
                ):
                    raise ValueError("oversized-input")
                result.append(cell)
    return result


def schedule(ordered):
    """Shuffle a fresh complete 108-cell block for each of five repetitions."""
    if len(ordered) != 108:
        raise ValueError("invalid-budget")
    rng = random.Random(ORDER_SEED)
    jobs = []
    for repetition in range(1, REPEATS + 1):
        block = list(ordered)
        rng.shuffle(block)
        jobs.extend((repetition, cell) for cell in block)
    return jobs


def manifest(ordered):
    """Build the source and exact-request freeze without dotenv or networking."""
    return {
        "version": 1,
        "order_seed": ORDER_SEED,
        "repetitions": REPEATS,
        "calls": 540,
        "sha256": {path: digest((ROOT / path).read_bytes()) for path in SOURCE_PATHS},
        "requests": [
            {
                "scenario": cell.scenario["id"],
                "model": cell.model,
                "condition": cell.condition,
                "request_sha256": cell.request_sha256,
            }
            for cell in ordered
        ],
        "schedule_sha256": digest(
            canonical(
                [
                    [
                        rep,
                        cell.scenario["id"],
                        cell.model,
                        cell.condition,
                        cell.request_sha256,
                    ]
                    for rep, cell in schedule(ordered)
                ]
            )
        ),
    }


def observe(result, cell):
    """Sanitize gateway metadata and parse transient candidate text."""
    result = gateway._checked_result(result)
    status = (
        "success"
        if isinstance(result, gateway.Success)
        else "refused"
        if isinstance(result, gateway.Refused)
        else "failed"
    )
    usage = result.usage or gateway.Usage()
    row = {
        "status": status,
        "code": None if status == "success" else result.code,
        "schema_accepted": None,
        "schema_error": None,
        "accepted_items": None,
        "reply_sha256": None,
        "validated_sha256": None,
        "grading_id": None,
        **{key: getattr(usage, key) for key in gateway.TOKEN_FIELDS},
    }
    candidate = None
    if status == "success":
        row["reply_sha256"] = digest(result.text.encode("utf-8"))
        try:
            if cell.feature is drafting:
                labels = [item["label"] for item in cell.scenario["data"]["criteria"]]
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
                validated_sha256=digest(canonical(candidate)),
            )
    return row, candidate


def run(jobs, output, freeze_hash, show_candidates):
    """Run the fixed schedule serially, emitting safe rows and transient candidates."""
    if len(jobs) != 540:
        raise ValueError("invalid-budget")
    seen = {}
    for ordinal, (repetition, cell) in enumerate(jobs, 1):
        os.environ["SOC_LLM_MODEL"] = cell.model
        started_at = datetime.now(UTC).isoformat()
        start = time.monotonic()
        interrupted = False
        try:
            result = gateway._transport(
                cell.feature.INSTRUCTIONS, cell.data, start + gateway.TOTAL_TIMEOUT
            )
        except (Exception, KeyboardInterrupt):  # noqa: BLE001 - preserve safe attempt
            result = gateway.Failed("provider-error")
            interrupted = True
        elapsed = int(max(0, time.monotonic() - start) * 1000)
        observations, candidate = observe(result, cell)
        view = {
            "ordinal": ordinal,
            "status": observations["status"],
            "schema_accepted": observations["schema_accepted"],
            "interrupted": interrupted,
        }
        if candidate is not None:
            key = (
                cell.scenario["id"],
                cell.model,
                cell.condition,
                canonical(candidate),
            )
            if key not in seen:
                seen[key] = f"g-{len(seen) + 1:04d}"
                if show_candidates:
                    view.update(
                        grading_id=seen[key],
                        scenario=cell.scenario["id"],
                        untrusted_candidate=candidate,
                    )
            observations["grading_id"] = seen[key]
        row = {
            "id": f"call-{ordinal:04d}",
            "ordinal": ordinal,
            "repetition": repetition,
            "scenario": cell.scenario["id"],
            "model": cell.model,
            "condition": cell.condition,
            "started_at": started_at,
            "elapsed_ms": elapsed,
            "request_sha256": cell.request_sha256,
            "freeze_sha256": freeze_hash,
            "instructions_version": cell.feature.INSTRUCTIONS_VERSION,
            "interrupted": interrupted,
            **observations,
        }
        output.write(json.dumps(row, ensure_ascii=True) + "\n")
        output.flush()
        print(json.dumps(view, ensure_ascii=True), flush=True)
        if interrupted:
            print("comparison-interrupted", file=sys.stderr)
            return 1
        if observations["status"] == "refused":
            print("comparison-refused", file=sys.stderr)
            return 1
        if ordinal < len(jobs):
            time.sleep(1)
    return 0


def main(argv=None):
    """Preflight offline, explicitly freeze, or execute the verified live schedule."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--show-candidates", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.freeze and args.live or args.show_candidates and not args.live:
            raise ValueError("invalid-options")
        ordered = cells()
        frozen = manifest(ordered)
        path = HERE / "frozen.json"
        if args.freeze:
            with path.open("x", encoding="utf-8") as target:
                json.dump(frozen, target, indent=2)
            print(json.dumps({"status": "frozen", "calls_if_live": 540}))
            return 0
        if not args.live:
            print(
                json.dumps(
                    {
                        "status": "preflight",
                        "calls_if_live": 540,
                        "cells": len(ordered),
                        "order_seed": ORDER_SEED,
                    }
                )
            )
            return 0
        if not args.show_candidates or args.output is None or args.output.exists():
            raise ValueError("invalid-output")
        frozen_raw = path.read_bytes()
        if json.loads(frozen_raw) != frozen:
            raise ValueError("freeze-changed")
        load_dotenv()
        if not settings.SOC_LLM_LIVE:
            raise ValueError("live-disabled")
        for model in MODELS:
            os.environ["SOC_LLM_MODEL"] = model
            config = gateway._configuration()
            if config is None or config[1] != model:
                raise ValueError("invalid-configuration")
        with args.output.open("x", encoding="utf-8") as output:
            return run(schedule(ordered), output, digest(frozen_raw), True)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - private text suppressed
        print("comparison-stopped", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
