"""Validate authored fixtures and audit saved semantic judgments without live calls."""

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import django

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ["DJANGO_SETTINGS_MODULE"] = "relay.settings.test"
django.setup()

from ai import drafting, feedback, gateway


def read(name):
    """Read one fixed local JSON artifact."""
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def digest(name):
    """Hash the exact artifact bytes used for grading or checking."""
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def index(rows, key):
    """Index records, rejecting duplicate identities instead of overwriting them."""
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate artifact identity")
    return result


def validate(fixtures):
    """Apply current feature parsers and input bounds to each constructed answer."""
    scenarios = index(fixtures["scenarios"], "id")
    index(fixtures["candidates"], "id")
    results = []
    for candidate in fixtures["candidates"]:
        scenario = scenarios[candidate["scenario"]]
        data = scenario["data"]
        feature = scenario["feature"]
        if feature not in {"drafting", "feedback"}:
            raise ValueError("Unknown feature")
        instructions = (
            drafting.INSTRUCTIONS if feature == "drafting" else feedback.INSTRUCTIONS
        )
        if len(instructions) + len(json.dumps(data)) > gateway.INPUT_LIMIT:
            raise ValueError("Oversized target input")
        reply = json.dumps(candidate["reply"], ensure_ascii=True)
        row = {"candidate": candidate["id"], "scenario": scenario["id"]}
        try:
            items = (
                [
                    asdict(item)
                    for item in drafting.parse(
                        reply, [criterion["label"] for criterion in data["criteria"]]
                    )
                ]
                if feature == "drafting"
                else feedback.parse(reply)
            )
        except drafting.InvalidReply as error:
            row.update(schema_accepted=False, schema_error=error.code, items=None)
        else:
            row.update(schema_accepted=True, schema_error=None, items=len(items))
        results.append(row)
    return results


def audit(fixtures, rows, judgments):
    """Check complete judgment coverage and compare it with authored references."""
    for name in ("fixtures.json", "reference.json"):
        if judgments["inputs"][name] != digest(name):
            raise ValueError("Graded inputs changed")
    references = index(read("reference.json")["references"], "candidate")
    assessments = index(judgments["assessments"], "candidate")
    scenarios = index(fixtures["scenarios"], "id")
    identities = {row["candidate"] for row in rows}
    if set(references) != identities or set(assessments) != identities:
        raise ValueError("Candidate coverage mismatch")
    for row in rows:
        if not row["schema_accepted"]:
            raise ValueError("Rejected candidate must not have semantic judgments")
        identity = row["candidate"]
        checks = index(scenarios[row["scenario"]]["checks"], "id")
        actual = assessments[identity]["checks"]
        expected = references[identity]["checks"]
        if set(actual) != set(checks) or set(expected) != set(checks):
            raise ValueError("Criterion coverage mismatch")
        for item in actual.values():
            if item["judgment"] not in {"met", "unmet", "unavailable"}:
                raise ValueError("Unknown judgment")
            if not item["evidence"] or not item["reason"]:
                raise ValueError("Missing assessment evidence")
        unavailable = sum(item["judgment"] == "unavailable" for item in actual.values())
        matched = sum(
            actual[key]["judgment"] == value for key, value in expected.items()
        )
        row.update(
            assessed_checks=len(checks) - unavailable,
            unavailable_checks=unavailable,
            matching_checks=matched,
            all_checks_met=(
                None
                if unavailable
                else all(v["judgment"] == "met" for v in actual.values())
            ),
        )
    return references, assessments


def report(fixtures, rows, judgments, references, assessments):
    """Render saved assessments and constructed answers for the human to inspect."""
    lines = [
        "# Three-scenario rehearsal results",
        "",
        "Status: coordinator grading completed; human inspection pending.",
        "",
        "See [method and limitations](README.md). These are authored answers,",
        "not SoC outputs. The assessor also authored and saw the reference labels.",
        "No independent calibration or full comparison was run.",
        "",
        f"Assessor: {judgments['assessor']}; one recorded grading pass.",
        "",
        (
            "| Candidate | Scenario | Schema | Items | All checks met | "
            "Reference agreement |"
        ),
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        matched = f"{row['matching_checks']}/{row['assessed_checks']}"
        outcome = {True: "yes", False: "no", None: "unavailable"}[row["all_checks_met"]]
        lines.append(
            f"| {row['candidate']} | {row['scenario']} | accepted | "
            f"{row['items']} | {outcome} | {matched} |"
        )
    unavailable = sum(row["unavailable_checks"] for row in rows)
    lines.extend(
        [
            "",
            f"Unavailable judgments: {unavailable}.",
            "Agreement is with authored references. It does not estimate accuracy",
            "on unseen answers and is not a scenario quality score.",
            "",
            "## Frozen grading inputs",
            "",
            "| Artifact | SHA-256 |",
            "| --- | --- |",
        ]
    )
    for name, value in judgments["inputs"].items():
        lines.append(f"| [{name}]({name}) | `{value}` |")
    lines.extend(
        [
            "",
            (
                "Current parser versions: "
                f"`{drafting.INSTRUCTIONS_VERSION}` / "
                f"`{feedback.INSTRUCTIONS_VERSION}`."
            ),
            "",
            "Exact targets and rubric definitions are in [fixtures](fixtures.json).",
        ]
    )
    for candidate in fixtures["candidates"]:
        identity = candidate["id"]
        lines.extend(
            [
                "",
                f"## {identity}: {candidate['scenario']}",
                "",
                f"Constructed reference: {references[identity]['intended']}.",
                "",
                "```json",
                json.dumps(candidate["reply"], ensure_ascii=False, indent=2),
                "```",
                "",
                "| Check | Judgment | Expected | Evidence field | Reason |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for key, item in assessments[identity]["checks"].items():
            expected = references[identity]["checks"][key]
            cells = [key, item["judgment"], expected, item["evidence"], item["reason"]]
            lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    (HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    """Run schema checks, optionally auditing saved grades and writing the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    fixtures = read("fixtures.json")
    rows = validate(fixtures)
    if args.report:
        judgments = read("judgments.json")
        references, assessments = audit(fixtures, rows, judgments)
        report(fixtures, rows, judgments, references, assessments)
    print(json.dumps(rows, indent=2))
    return int(any(not row["schema_accepted"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
