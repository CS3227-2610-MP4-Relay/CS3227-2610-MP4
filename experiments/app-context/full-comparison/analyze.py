"""Offline audit and descriptive, scenario-weighted comparison.

Evidence pointers are checked structurally against recorded collection sizes;
candidate contents are deliberately unavailable and cannot be rechecked here.
"""

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).resolve().parent
MODELS = ("llama3.1:8b", "qwen3.6:35b", "x-test-2")
CONDITIONS = ("relevant-only", "app-clutter", "off-topic")
HASH = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_PATHS = {
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
}
FIELDS = {
    "id",
    "ordinal",
    "repetition",
    "scenario",
    "model",
    "condition",
    "started_at",
    "elapsed_ms",
    "request_sha256",
    "freeze_sha256",
    "instructions_version",
    "status",
    "code",
    "schema_accepted",
    "schema_error",
    "accepted_items",
    "reply_sha256",
    "validated_sha256",
    "grading_id",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "interrupted",
}


def require(ok, message):
    """Raise a safe audit error without echoing arbitrary input contents."""
    if not ok:
        raise ValueError(message)


def digest(path):
    """Hash an authorized source artifact."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    """Read JSON while rejecting duplicate object keys."""

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs)


def finite(value, integer=False):
    """Accept only finite nonnegative numeric measurements."""
    return (
        (type(value) is int if integer else type(value) in (int, float))
        and math.isfinite(value)
        and value >= 0
    )


def pointer_valid(pointer, feature, count):
    """Validate schema-addressable pointers, without retaining candidate text."""
    collection = "drafts" if feature == "drafting" else "questions"
    if pointer == f"/{collection}":
        return True
    if not isinstance(pointer, str):
        return False
    parts = pointer.split("/")
    if len(parts) < 3 or parts[0] or parts[1] != collection:
        return False
    if not re.fullmatch(r"0|[1-9][0-9]*", parts[2]) or int(parts[2]) >= count:
        return False
    if feature == "feedback":
        return len(parts) == 3
    return len(parts) == 3 or (
        len(parts) == 4
        and parts[3] in {"title", "steps", "expected_result", "criteria"}
    )


def spread(values):
    """Describe a measured distribution, preserving unavailable values."""
    return {
        key: function(values) if values else None
        for key, function in (
            ("mean", mean),
            ("median", median),
            ("min", min),
            ("max", max),
        )
    }


def audit_judgments(documents, accepted, scenarios, hashes, partial):
    """Validate complete scenario-specific assessments and their provenance."""
    judgments = {}
    for document in documents:
        require(
            set(document) == {"version", "assessor", "inputs", "assessments"},
            "invalid judgment document fields",
        )
        require(
            isinstance(document["version"], str) and bool(document["version"]),
            "missing judgment version",
        )
        require(
            isinstance(document["assessor"], str) and bool(document["assessor"]),
            "missing assessor",
        )
        require(document["inputs"] == hashes, "judgment input hash mismatch")
        require(isinstance(document["assessments"], list), "invalid assessments")
        for assessment in document["assessments"]:
            require(
                set(assessment) == {"candidate", "scenario", "checks"},
                "invalid assessment fields",
            )
            identifier = assessment["candidate"]
            require(
                isinstance(identifier, str)
                and identifier in accepted
                and identifier not in judgments,
                "unknown or duplicate grading ID",
            )
            row = accepted[identifier]
            scenario = scenarios[row["scenario"]]
            require(
                assessment["scenario"] == row["scenario"], "judgment scenario mismatch"
            )
            checks = assessment["checks"]
            require(
                isinstance(checks, dict)
                and set(checks) == {check["id"] for check in scenario["checks"]},
                "judgment check coverage mismatch",
            )
            for check in checks.values():
                require(
                    isinstance(check, dict)
                    and set(check) == {"judgment", "evidence", "reason"},
                    "invalid check fields",
                )
                require(
                    check["judgment"] in {"met", "unmet", "unavailable"},
                    "invalid judgment value",
                )
                require(
                    isinstance(check["reason"], str) and bool(check["reason"].strip()),
                    "missing judgment reason",
                )
                require(
                    pointer_valid(
                        check["evidence"], scenario["feature"], row["accepted_items"]
                    ),
                    "invalid evidence pointer",
                )
            judgments[identifier] = {
                key: check["judgment"] for key, check in checks.items()
            }
    require(
        partial or set(judgments) == set(accepted), "missing accepted-answer judgment"
    )
    return judgments


def summarize(
    rows, schedule, scenarios, documents, hashes, freeze_sha256, partial=False
):
    """Audit normalized frozen schedule and rows, then summarize all 108 cells."""
    require(len(schedule) == 540, "frozen schedule must contain 540 calls")
    require(
        len(rows) <= 540 and (partial or len(rows) == 540),
        "incomplete or excessive measurement count",
    )
    groups = defaultdict(list)
    expected_groups = Counter()
    accepted = {}
    parsed_ids = {}
    for expected in schedule:
        expected_groups[
            tuple(expected[key] for key in ("scenario", "model", "condition"))
        ] += 1
    require(
        len(expected_groups) == 108 and set(expected_groups.values()) == {5},
        "invalid frozen cell budget",
    )
    for index, row in enumerate(rows):
        require(
            isinstance(row, dict) and set(row) == FIELDS, "invalid measurement fields"
        )
        expected = schedule[index]
        require(
            row["ordinal"] == index + 1
            and type(row["ordinal"]) is int
            and row["id"] == f"call-{index + 1:04d}",
            "measurement order mismatch",
        )
        for key in ("repetition", "scenario", "model", "condition", "request_sha256"):
            require(row[key] == expected[key], "measurement/frozen request mismatch")
        require(
            row["scenario"] in scenarios
            and row["model"] in MODELS
            and row["condition"] in CONDITIONS,
            "unknown cell",
        )
        require(row["freeze_sha256"] == freeze_sha256, "freeze hash mismatch")
        require(
            isinstance(row["instructions_version"], str)
            and bool(row["instructions_version"]),
            "missing instructions version",
        )
        require(
            isinstance(row["started_at"], str) and bool(row["started_at"]),
            "missing start timestamp",
        )
        try:
            timestamp = datetime.fromisoformat(row["started_at"])
        except ValueError as error:
            raise ValueError("invalid start timestamp") from error
        require(timestamp.tzinfo is not None, "missing timestamp timezone")
        require(finite(row["elapsed_ms"]), "invalid elapsed time")
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            require(
                row[key] is None or finite(row[key], integer=True),
                "invalid token count",
            )
        for key in ("request_sha256", "reply_sha256", "validated_sha256"):
            require(
                (key != "request_sha256" and row[key] is None)
                or (isinstance(row[key], str) and HASH.fullmatch(row[key])),
                "invalid content hash",
            )
        version = (
            "drafting-2"
            if scenarios[row["scenario"]]["feature"] == "drafting"
            else "observation-feedback-3"
        )
        require(row["instructions_version"] == version, "instructions version mismatch")
        require(
            row["status"] in {"success", "failed", "refused"}, "invalid provider status"
        )
        require(type(row["interrupted"]) is bool, "invalid interrupted flag")
        require(
            not row["interrupted"]
            or (
                index == len(rows) - 1
                and row["status"] == "failed"
                and row["code"] == "provider-error"
            ),
            "invalid interrupted invocation",
        )
        if row["status"] == "success":
            require(
                row["code"] is None
                and type(row["schema_accepted"]) is bool
                and row["reply_sha256"] is not None,
                "invalid success metadata",
            )
            errors = {
                "json",
                "repeated-key",
                "too-long",
                "surrogate",
                "object",
                "drafts",
                "draft-keys",
                "title",
                "steps",
                "expected",
                "criteria",
                "label",
                "duplicate-label",
                "questions",
                "question",
            }
            require(
                row["schema_error"] is None
                if row["schema_accepted"]
                else row["schema_error"] in errors,
                "invalid schema error",
            )
        else:
            codes = (
                {"timeout", "transport", "invalid-response", "provider-error"}
                if row["status"] == "failed"
                else {
                    "live-off",
                    "input-too-large",
                    "busy-or-quota",
                    "not-configured",
                    "provider-refused",
                    "quota",
                }
            )
            require(
                row["code"] in codes
                and row["schema_accepted"] is None
                and row["schema_error"] is None
                and row["reply_sha256"] is None,
                "invalid failure metadata",
            )
            require(
                index == len(rows) - 1 if row["status"] == "refused" else True,
                "calls continued after refusal",
            )
        cell = tuple(row[key] for key in ("scenario", "model", "condition"))
        if row["schema_accepted"]:
            require(
                row["reply_sha256"] is not None
                and row["validated_sha256"] is not None
                and finite(row["accepted_items"], integer=True)
                and row["accepted_items"] <= 5,
                "invalid accepted metadata",
            )
            identifier = row["grading_id"]
            require(
                isinstance(identifier, str) and re.fullmatch(r"g-[0-9]{4}", identifier),
                "invalid grading ID",
            )
            parsed = (*cell, row["validated_sha256"])
            require(
                parsed not in parsed_ids or parsed_ids[parsed] == identifier,
                "exact duplicate did not reuse grading ID",
            )
            if identifier in accepted:
                previous = accepted[identifier]
                require(
                    all(
                        previous[key] == row[key]
                        for key in (
                            "scenario",
                            "model",
                            "condition",
                            "validated_sha256",
                            "accepted_items",
                        )
                    ),
                    "grading ID reused for different answer/cell",
                )
            parsed_ids[parsed] = identifier
            accepted[identifier] = row
        else:
            require(
                all(
                    row[key] is None
                    for key in ("validated_sha256", "grading_id", "accepted_items")
                ),
                "rejected answer has grading metadata",
            )
        groups[cell].append(row)
    judgments = audit_judgments(documents, accepted, scenarios, hashes, partial)
    cells = []
    for cell in expected_groups:
        scenario, model, condition = cell
        calls = groups[cell]
        criteria = {check["id"]: Counter() for check in scenarios[scenario]["checks"]}
        vectors = set()
        all_met = fully_assessed = 0
        for row in calls:
            judgment = judgments.get(row["grading_id"])
            if judgment:
                if "unavailable" not in judgment.values():
                    vectors.add(tuple(judgment[key] for key in criteria))
                fully_assessed += "unavailable" not in judgment.values()
                all_met += all(value == "met" for value in judgment.values())
            for key, counts in criteria.items():
                counts[judgment[key] if judgment else "ungraded"] += 1
        for counts in criteria.values():
            counts["ungraded"] += 5 - len(calls)
        schema_accepted = sum(row["schema_accepted"] is True for row in calls)
        provider_failures = sum(row["reply_sha256"] is None for row in calls)
        cells.append(
            {
                "scenario": scenario,
                "feature": scenarios[scenario]["feature"],
                "model": model,
                "condition": condition,
                "attempts": len(calls),
                "unattempted": 5 - len(calls),
                "schema_accepted": schema_accepted,
                "provider_failures": provider_failures,
                "schema_failures": len(calls) - provider_failures - schema_accepted,
                "criteria": {
                    key: {
                        value: counts[value]
                        for value in ("met", "unmet", "unavailable", "ungraded")
                    }
                    for key, counts in criteria.items()
                },
                "all_checks_met": all_met,
                "fully_assessed": fully_assessed,
                "success_per_attempt": all_met / len(calls) if calls else None,
                "success_per_assessed": all_met / fully_assessed
                if fully_assessed
                else None,
                "schema_acceptance_per_attempt": schema_accepted / len(calls)
                if calls
                else None,
                "unique_raw": len(
                    {row["reply_sha256"] for row in calls if row["reply_sha256"]}
                ),
                "unique_parsed": len(
                    {
                        row["validated_sha256"]
                        for row in calls
                        if row["validated_sha256"]
                    }
                ),
                "unique_criterion_vectors": len(vectors),
                "latency_ms": spread([row["elapsed_ms"] for row in calls]),
                "tokens": {
                    key: {
                        "sum_available": sum(
                            row[key] for row in calls if row[key] is not None
                        )
                        if any(row[key] is not None for row in calls)
                        else None,
                        "available": sum(row[key] is not None for row in calls),
                        "missing": sum(row[key] is None for row in calls),
                    }
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                },
            }
        )
    for cell in cells:
        cell["latency_mean_ms"] = cell["latency_ms"]["mean"]
        for kind in ("schema_failures", "provider_failures"):
            cell[f"{kind}_per_attempt"] = (
                cell[kind] / cell["attempts"] if cell["attempts"] else None
            )
        for key, tokens in cell["tokens"].items():
            cell[f"{key}_mean_available"] = (
                tokens["sum_available"] / tokens["available"]
                if tokens["available"]
                else None
            )
    metrics = (
        "success_per_attempt",
        "success_per_assessed",
        "schema_acceptance_per_attempt",
        "schema_failures_per_attempt",
        "provider_failures_per_attempt",
        "latency_mean_ms",
        "prompt_tokens_mean_available",
        "completion_tokens_mean_available",
        "total_tokens_mean_available",
    )
    aggregates = []
    paired = []
    for feature in ("drafting", "feedback"):
        for model in MODELS:
            for condition in CONDITIONS:
                selected = [
                    cell
                    for cell in cells
                    if (cell["feature"], cell["model"], cell["condition"])
                    == (feature, model, condition)
                ]
                aggregates.append(
                    {
                        "feature": feature,
                        "model": model,
                        "condition": condition,
                        "scenario_count": len(selected),
                        **{
                            metric: {
                                "mean": mean(values) if values else None,
                                "available_scenarios": len(values),
                            }
                            for metric in metrics
                            for values in [
                                [
                                    cell[metric]
                                    for cell in selected
                                    if cell[metric] is not None
                                ]
                            ]
                        },
                    }
                )
            for condition in CONDITIONS[1:]:
                pairs = [
                    (
                        next(
                            cell
                            for cell in cells
                            if (cell["scenario"], cell["model"], cell["condition"])
                            == (other["scenario"], model, "relevant-only")
                        ),
                        other,
                    )
                    for other in cells
                    if (other["feature"], other["model"], other["condition"])
                    == (feature, model, condition)
                ]
                paired.append(
                    {
                        "feature": feature,
                        "model": model,
                        "condition_minus_relevant_only": condition,
                        **{
                            metric: {
                                "mean_delta": mean(values) if values else None,
                                "paired_scenarios": len(values),
                            }
                            for metric in metrics
                            for values in [
                                [
                                    other[metric] - baseline[metric]
                                    for baseline, other in pairs
                                    if baseline[metric] is not None
                                    and other[metric] is not None
                                ]
                            ]
                        },
                    }
                )
    return {
        "version": "full-comparison-summary-1",
        "partial": partial,
        "attempts": len(rows),
        "interrupted_invocations": sum(row["interrupted"] for row in rows),
        "accepted_unique": len(accepted),
        "assessed_unique": len(judgments),
        "cells": cells,
        "scenario_averages": aggregates,
        "paired_deltas": paired,
        "limitations": [
            (
                "Evidence pointers checked structurally only; "
                "candidate contents were not retained."
            ),
            (
                "Descriptive model assessments, not human validation "
                "or independent-call inference."
            ),
            (
                "Unavailable judgments excluded from fully assessed denominator; "
                "failures remain in attempted denominator."
            ),
            (
                "Quality vectors use fully assessed answers only; "
                "five repeats without variation do not establish determinism."
            ),
        ],
    }


def frozen_schedule(manifest):
    """Reconstruct the shuffled execution order using only frozen metadata."""
    require(
        set(manifest)
        == {
            "version",
            "order_seed",
            "repetitions",
            "calls",
            "sha256",
            "requests",
            "schedule_sha256",
        },
        "invalid freeze fields",
    )
    require(
        (
            manifest["version"],
            manifest["order_seed"],
            manifest["repetitions"],
            manifest["calls"],
        )
        == (1, 20261110, 5, 540),
        "invalid freeze settings",
    )
    expected = [
        (f"{prefix}{i}", model, condition)
        for prefix in "DF"
        for i in range(1, 7)
        for model in MODELS
        for condition in CONDITIONS
    ]
    require(len(manifest["requests"]) == 108, "invalid request count")
    for row, cell in zip(manifest["requests"], expected, strict=True):
        require(
            set(row) == {"scenario", "model", "condition", "request_sha256"},
            "invalid frozen request fields",
        )
        require(
            tuple(row[key] for key in ("scenario", "model", "condition")) == cell
            and isinstance(row["request_sha256"], str)
            and HASH.fullmatch(row["request_sha256"]),
            "invalid frozen request",
        )
    rng = random.Random(20261110)
    result = []
    for repetition in range(1, 6):
        block = list(manifest["requests"])
        rng.shuffle(block)
        result.extend(dict(row, repetition=repetition) for row in block)
    serialized = [
        [
            row[key]
            for key in (
                "repetition",
                "scenario",
                "model",
                "condition",
                "request_sha256",
            )
        ]
        for row in result
    ]
    actual = hashlib.sha256(
        json.dumps(serialized, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    require(manifest["schedule_sha256"] == actual, "frozen schedule hash mismatch")
    return result


def main(argv=None):
    """Audit local frozen artifacts and write a new JSON summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args(argv)
    manifest = load_json(HERE / "frozen.json")
    schedule = frozen_schedule(manifest)
    root = HERE.parents[2]
    audit_sources(manifest["sha256"], root)
    scenarios = {
        scenario["id"]: scenario
        for scenario in load_json(HERE.parent / "calibration/fixtures.json")[
            "scenarios"
        ]
    }
    # Parse each JSONL line through the same duplicate-key rejecting loader.
    rows = []
    for line in args.measurements.read_text(encoding="utf-8").splitlines():

        def pairs(items):
            result = {}
            for key, value in items:
                require(key not in result, "duplicate measurement key")
                result[key] = value
            return result

        rows.append(json.loads(line, object_pairs_hook=pairs))
    hashes = {
        "fixtures.json": digest(HERE.parent / "calibration/fixtures.json"),
        "rubric.md": digest(HERE / "rubric.md"),
    }
    summary = summarize(
        rows,
        schedule,
        scenarios,
        [load_json(path) for path in sorted(args.judgments.glob("*.json"))],
        hashes,
        digest(HERE / "frozen.json"),
        args.partial,
    )
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, allow_nan=False)
        output.write("\n")
    return 0


def audit_sources(sources, root):
    """Reject all unexpected paths before reading any frozen source file."""
    require(
        isinstance(sources, dict) and set(sources) == SOURCE_PATHS,
        "invalid frozen source paths",
    )
    for relative, expected_hash in sources.items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root), "unsafe frozen source path")
        require(digest(path) == expected_hash, "frozen source hash mismatch")


if __name__ == "__main__":
    raise SystemExit(main())
