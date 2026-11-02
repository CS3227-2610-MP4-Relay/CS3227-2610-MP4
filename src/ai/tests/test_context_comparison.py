"""Offline paired-input and structural-observation checks; no quality grader."""

import json

import pytest

from ai import context_comparison as comparison
from ai import drafting, feedback, gateway

pytestmark = pytest.mark.ac("CTX-1.2", "CTX-1.3", "CTX-1.4", "CTX-1.5", "CTX-1.7")


def test_fixed_pairs_preserve_core_instructions_order_and_allowance():
    cases = comparison.corpus()
    assert len(cases) == len({case.id for case in cases}) == 8
    for index, name in enumerate(
        (
            "drafting-boundary",
            "drafting-state",
            "feedback-incomplete",
            "feedback-complete",
        )
    ):
        pair = cases[index * 2 : index * 2 + 2]
        assert [c.arm for c in pair] == (
            ["selected", "broader"] if index % 2 == 0 else ["broader", "selected"]
        )
        selected, broader = sorted(pair, key=lambda c: c.arm, reverse=True)
        core, broad = json.loads(selected.data), json.loads(broader.data)
        background = broad.pop("background")
        assert broad == core and background == comparison.BACKGROUND
        assert set(background) == {"visible_case_criteria"}
        module = drafting if index < 2 else feedback
        for case in pair:
            assert case.id == f"{name}-{case.arm}"
            assert case.instructions == module.INSTRUCTIONS
            assert len(case.instructions) + len(case.data) <= gateway.INPUT_LIMIT
        if index < 2:
            assert set(core) == {"criteria"}
            assert [c["label"] for c in core["criteria"]] == ["C1"]
        else:
            assert set(core) == {"observation", "case", "criteria"}
            assert "Available" in core["case"]["steps"]
    assert "1 to 40" in cases[0].data and "41" in cases[0].data
    assert "Cancelling" in cases[2].data
    assert (
        json.loads(cases[4].data)["observation"] == "The CSV included the wrong rows."
    )
    assert "Sample-2" in cases[6].data and "twice" in cases[6].data


@pytest.mark.parametrize("index", [0, 4])
@pytest.mark.parametrize("valid", [False, True])
def test_empty_and_invalid_replies_are_distinct(index, valid):
    case = comparison.corpus()[index]
    key = "drafts" if index == 0 else "questions"
    row = comparison.score(
        case, gateway.Success(json.dumps({key: []}) if valid else "x")
    )
    assert row["status"] == "success" and row["schema_accepted"] is valid
    assert row["accepted_items"] == (0 if valid else None)
    assert "response" not in row and "data" not in row


def test_current_parsers_keep_target_labels_and_count_accepted_items():
    case = comparison.corpus()[1]
    draft = {
        "title": "Name",
        "steps": "1. Save.",
        "expected_result": "Saved.",
        "criteria": ["C1"],
    }
    assert (
        comparison.score(case, gateway.Success(json.dumps({"drafts": [draft]})))[
            "accepted_items"
        ]
        == 1
    )
    draft["criteria"] = ["C2"]
    assert (
        comparison.score(case, gateway.Success(json.dumps({"drafts": [draft]})))[
            "schema_accepted"
        ]
        is False
    )
    assert (
        comparison.score(
            comparison.corpus()[4], gateway.Success('{"questions":["Which row?"]}')
        )["accepted_items"]
        == 1
    )


@pytest.mark.parametrize(
    "result,status",
    [
        (None, "unattempted"),
        (gateway.Refused("private"), "refused"),
        (gateway.Failed("private"), "failed"),
    ],
)
def test_unavailable_results_exclude_private_codes_and_quality_claims(result, status):
    row = comparison.score(comparison.corpus()[0], result)
    assert row["status"] == status
    assert row["schema_accepted"] is row["accepted_items"] is None
    assert all(row[field] is None for field in gateway.TOKEN_FIELDS)
    assert "private" not in json.dumps(row)


@pytest.mark.parametrize(
    "usage,expected",
    [
        (None, (None, None, None)),
        (gateway.Usage(True, -1, "3"), (None, None, None)),
        (gateway.Usage(0, 2**63, 9), (0, None, 9)),
        (gateway.Usage(3, 4, 2**63 - 1), (3, 4, 2**63 - 1)),
    ],
)
def test_optional_counts_are_independent_checked_values(usage, expected):
    row = comparison.score(comparison.corpus()[0], gateway.Failed("timeout", usage))
    assert tuple(row[field] for field in gateway.TOKEN_FIELDS) == expected
