"""Freeze and audit constructed calibration artifacts without provider calls."""

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import django

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.test"
django.setup()

from ai import drafting, feedback, gateway

FROZEN_PATHS = (
    HERE / "fixtures.json",
    HERE / "reference.json",
    HERE / "rubric.md",
    HERE / "README.md",
    Path(__file__),
    ROOT / "src/ai/drafting.py",
    ROOT / "src/ai/feedback.py",
    ROOT / "src/ai/gateway.py",
)


def read(name):
    """Read a calibration artifact using strict JSON decoding."""
    return json.loads(
        (HERE / name).read_text(encoding="utf-8"),
        object_pairs_hook=drafting._no_repeated_keys,
        parse_constant=drafting._reject_constant,
    )


def digest(path):
    """Hash exact bytes, preserving the identity of frozen inputs."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(name, value):
    """Create evidence without replacing a prior run's output."""
    text = value if isinstance(value, str) else json.dumps(value, indent=2) + "\n"
    with (HERE / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def indexed(rows, key):
    """Reject duplicate identities before indexing artifact records."""
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate identity")
    return result


def validate(fixtures, references):
    """Check corpus coverage, exact parser results and reference completeness."""
    scenarios = indexed(fixtures["scenarios"], "id")
    candidates = indexed(fixtures["candidates"], "id")
    expected_ids = {f"{prefix}{n}" for prefix in ("D", "F") for n in range(1, 7)}
    if set(scenarios) != expected_ids or len(candidates) != 24:
        raise ValueError("Expected twelve scenarios and twenty-four candidates")
    if set(references) != set(candidates):
        raise ValueError("Reference candidate coverage mismatch")
    old = json.loads((HERE.parent / "grader-rehearsal/fixtures.json").read_bytes())
    for original in old["scenarios"]:
        if scenarios[original["id"]] != original:
            raise ValueError("Approved D1/F2/F3 scenario changed")
    rows = []
    for identity, scenario in scenarios.items():
        feature = drafting if identity.startswith("D") else feedback
        if scenario["feature"] != ("drafting" if feature is drafting else "feedback"):
            raise ValueError("Feature/scenario mismatch")
        data = scenario["data"]
        if len(feature.INSTRUCTIONS) + len(json.dumps(data)) > gateway.INPUT_LIMIT:
            raise ValueError("Oversized target")
        checks = indexed(scenario["checks"], "id")
        pair = [c for c in candidates.values() if c["scenario"] == identity]
        if len(pair) != 2:
            raise ValueError("Each scenario must have two candidates")
        good_count = 0
        for candidate in pair:
            reply = json.dumps(candidate["reply"], ensure_ascii=True)
            if feature is drafting:
                labels = [item["label"] for item in data["criteria"]]
                parsed = {"drafts": [asdict(d) for d in drafting.parse(reply, labels)]}
            else:
                parsed = {"questions": feedback.parse(reply)}
            if json.loads(json.dumps(parsed)) != candidate["reply"]:
                raise ValueError("Parser changed candidate content")
            reference = references[candidate["id"]]
            if set(reference["checks"]) != set(checks) or set(
                reference["rationale"]
            ) != set(checks):
                raise ValueError("Reference criterion coverage mismatch")
            if not set(reference["checks"].values()) <= {"met", "unmet"}:
                raise ValueError("Invalid reference judgment")
            if any(
                not str(reason).strip() for reason in reference["rationale"].values()
            ):
                raise ValueError("Missing reference rationale")
            good = all(value == "met" for value in reference["checks"].values())
            if good != (reference["intended"] == "good"):
                raise ValueError("Reference classification mismatch")
            good_count += good
            rows.append(
                {
                    "candidate": candidate["id"],
                    "scenario": identity,
                    "items": len(next(iter(parsed.values()))),
                }
            )
        if good_count != 1:
            raise ValueError("Expected one good and one flawed reference per scenario")
    return scenarios, candidates, rows


def resolve_pointer(reply, pointer):
    """Ensure evidence points into the candidate instead of an invented field."""
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Evidence must be a JSON pointer into the reply")
    value = reply
    for part in pointer[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def audit(scenarios, candidates, references, rows):
    """Compare complete saved judgments with frozen references, retaining errors."""
    judgments = read("judgments.json")
    for name in ("fixtures.json", "rubric.md"):
        if judgments["inputs"][name] != digest(HERE / name):
            raise ValueError("Judgment input hash mismatch")
    assessments = indexed(judgments["assessments"], "candidate")
    if set(assessments) != set(candidates):
        raise ValueError("Assessment candidate coverage mismatch")
    disagreements = []
    for row in rows:
        identity = row["candidate"]
        assessment = assessments[identity]
        checks = indexed(scenarios[row["scenario"]]["checks"], "id")
        actual = assessment["checks"]
        expected = references[identity]["checks"]
        if assessment["scenario"] != row["scenario"] or set(actual) != set(checks):
            raise ValueError("Assessment scenario/criterion coverage mismatch")
        for criterion, item in actual.items():
            if item["judgment"] not in {"met", "unmet", "unavailable"}:
                raise ValueError("Invalid assessment judgment")
            if not isinstance(item["reason"], str) or not item["reason"].strip():
                raise ValueError("Missing assessment reason")
            resolve_pointer(candidates[identity]["reply"], item["evidence"])
            if item["judgment"] != expected[criterion]:
                disagreements.append(
                    {
                        "candidate": identity,
                        "criterion": criterion,
                        "reference": expected[criterion],
                        **item,
                        "reference_reason": references[identity]["rationale"][
                            criterion
                        ],
                    }
                )
        values = [item["judgment"] for item in actual.values()]
        unavailable = values.count("unavailable")
        row.update(
            criteria=len(checks),
            unavailable=unavailable,
            matched=sum(actual[k]["judgment"] == v for k, v in expected.items()),
            reference_good=all(v == "met" for v in expected.values()),
            assessed_good=None if unavailable else all(v == "met" for v in values),
        )
    return {
        "version": "calibration-audit-1",
        "audited_at": datetime.now(UTC).isoformat(),
        "judgments_sha256": digest(HERE / "judgments.json"),
        "frozen_sha256": digest(HERE / "frozen.json"),
        "candidates": len(rows),
        "criteria": sum(r["criteria"] for r in rows),
        "matched": sum(r["matched"] for r in rows),
        "unavailable": sum(r["unavailable"] for r in rows),
        "exact_candidates": sum(r["matched"] == r["criteria"] for r in rows),
        "false_accepts": sum(
            r["assessed_good"] is True and not r["reference_good"] for r in rows
        ),
        "false_rejects": sum(
            r["assessed_good"] is False and r["reference_good"] for r in rows
        ),
        "unavailable_candidates": sum(r["assessed_good"] is None for r in rows),
        "rows": rows,
        "disagreements": disagreements,
    }


def render(result):
    """Render agreement evidence without treating reference labels as human truth."""
    lines = [
        "# Calibration results",
        "",
        "One fresh GPT-6.1 Sol grader assessed 24 constructed answers with reference",
        "labels withheld by instruction. See [method and limitations](README.md).",
        "",
        (
            f"Criterion agreement: **{result['matched']}/{result['criteria']}**; "
            f"unavailable: **{result['unavailable']}**."
        ),
        f"Exact candidate agreement: **{result['exact_candidates']}/24**.",
        (
            f"False accepts against references: **{result['false_accepts']}**; "
            f"false rejects: **{result['false_rejects']}**; "
            f"unavailable candidates: **{result['unavailable_candidates']}**."
        ),
        "",
        "These are model-authored references, not human-validated ground truth.",
        "Agreement measures this sample, not accuracy on future live outputs.",
        "",
        "| Candidate | Scenario | Reference | Graded | Criterion agreement |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in sorted(result["rows"], key=lambda item: item["candidate"]):
        expected = "good" if row["reference_good"] else "flawed"
        actual = {True: "all met", False: "some unmet", None: "unavailable"}[
            row["assessed_good"]
        ]
        lines.append(
            f"| {row['candidate']} | {row['scenario']} | {expected} | {actual} | "
            f"{row['matched']}/{row['criteria']} |"
        )
    lines.extend(["", "## Disagreements", ""])
    if not result["disagreements"]:
        lines.append(
            "None in this pass. No grades or references were changed after grading."
        )
    for item in result["disagreements"]:
        lines.extend(
            [
                (
                    f"- **{item['candidate']} / {item['criterion']}**: "
                    f"reference `{item['reference']}`, "
                    f"grader `{item['judgment']}`."
                ),
                f"  Grader ({item['evidence']}): {item['reason']}",
                f"  Reference: {item['reference_reason']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- [Constructed targets, checks and answers](fixtures.json)",
            "- [Original reference labels and reasons](reference.json)",
            "- [Grader judgments and reasons](judgments.json)",
            "- [Frozen input/source hashes](frozen.json)",
            "- [Machine-readable audit](audit.json)",
            f"- Judgments SHA-256: `{result['judgments_sha256']}`.",
            f"- Frozen manifest SHA-256: `{result['frozen_sha256']}`.",
            "",
            "The full context comparison remains unrun. Inspect disagreements before",
            "using these rules on live outputs; retain the original pass above.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    """Validate, freeze once, or audit completed grading without live model calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    fixtures = read("fixtures.json")
    references = indexed(read("reference.json")["references"], "candidate")
    scenarios, candidates, rows = validate(fixtures, references)
    hashes = {
        str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
        for path in FROZEN_PATHS
    }
    if args.freeze:
        write_new(
            "frozen.json",
            {"frozen_at": datetime.now(UTC).isoformat(), "sha256": hashes},
        )
    elif (HERE / "frozen.json").exists() and read("frozen.json")["sha256"] != hashes:
        raise ValueError("Frozen source or input changed")
    if args.audit:
        if not (HERE / "frozen.json").exists():
            raise ValueError("Freeze inputs before grading")
        if any((HERE / name).exists() for name in ("audit.json", "results.md")):
            raise ValueError("Audit outputs already exist")
        result = audit(scenarios, candidates, references, rows)
        write_new("audit.json", result)
        write_new("results.md", render(result))
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in {"rows", "disagreements"}},
                indent=2,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "scenarios": len(scenarios),
                    "schema_accepted": len(rows),
                    "candidates": len(candidates),
                    "frozen": args.freeze,
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
