"""Offline evidence for the bounded operator injection measurement."""

import json

import pytest

from ai import drafting, evaluation, feedback, gateway

pytestmark = pytest.mark.ac("SEC-INJ-1.2", "SEC-INJ-1.3", "SEC-INJ-1.4")


def reply(case, text):
    if case.feature == "feedback":
        return json.dumps({"questions": [text]})
    return json.dumps(
        {
            "drafts": [
                {
                    "title": text,
                    "steps": "1. Open.",
                    "expected_result": "Visible.",
                    "criteria": ["C1"],
                }
            ]
        }
    )


def test_fixed_corpus_reuses_current_contracts_and_keeps_data_framed():
    cases = evaluation.corpus()
    assert len(cases) == len({case.id for case in cases}) == 12
    for feature in ("drafting", "feedback"):
        selected = [case for case in cases if case.feature == feature]
        assert len(selected) == 6
        assert sum(case.kind == "control" for case in selected) == 1
        module = drafting if feature == "drafting" else feedback
        assert all(case.instructions == module.INSTRUCTIONS for case in selected)
    for case in cases:
        assert len(case.instructions) + len(case.data) <= gateway.INPUT_LIMIT
        data = json.loads(case.data)
        if case.feature == "drafting":
            assert set(data) == {"criteria"}
            assert len(data["criteria"]) == 1
            assert data["criteria"][0]["label"] == "C1"
        else:
            assert set(data) == {"observation", "case", "criteria"}
        if case.kind == "attack":
            assert case.marker in case.data
            if case.feature == "feedback":
                target = {"framing": "title", "outcome": "criterion"}.get(
                    case.id.split("-")[1], "observation"
                )
                fields = {
                    "observation": data["observation"],
                    "title": data["case"]["title"],
                    "criterion": data["criteria"][0],
                }
                assert [key for key, text in fields.items() if case.marker in text] == [
                    target
                ]
    removed = next(case for case in cases if case.kind == "cleaned")
    assert removed.marker not in removed.data
    assert "opens" in removed.data


@pytest.mark.parametrize("feature", ["drafting", "feedback"])
@pytest.mark.parametrize("following", [False, True])
def test_raw_and_cleaned_accepted_text_scores(feature, following):
    case = next(
        c for c in evaluation.corpus() if c.feature == feature and c.kind == "attack"
    )
    text = case.marker if following else "Which screen appeared?"
    row = evaluation.score(case, gateway.Success(reply(case, text)))
    assert row["raw_marker"] is following
    assert row["accepted_marker"] is following
    assert row["schema_accepted"] is True
    assert row["status"] == "success"


@pytest.mark.parametrize("feature", ["drafting", "feedback"])
def test_schema_rejection_and_json_escaping_have_distinct_scores(feature):
    case = next(
        c for c in evaluation.corpus() if c.feature == feature and c.kind == "attack"
    )
    row = evaluation.score(case, gateway.Success(case.marker))
    assert row["raw_marker"] is True
    assert row["schema_accepted"] is False
    assert row["accepted_marker"] is False
    escaped = reply(case, case.marker).replace(case.marker[0], "\\u0052")
    row = evaluation.score(case, gateway.Success(escaped))
    assert row["raw_marker"] is False
    assert row["accepted_marker"] is True


@pytest.mark.parametrize("feature", ["drafting", "feedback"])
def test_cleaned_fields_empty_output_and_extra_keys(feature):
    case = next(
        c for c in evaluation.corpus() if c.feature == feature and c.kind == "attack"
    )
    hidden = case.marker[:1] + "\u200b" + case.marker[1:]
    row = evaluation.score(case, gateway.Success(reply(case, hidden)))
    assert row["raw_marker"] is False and row["accepted_marker"] is True
    key = "drafts" if feature == "drafting" else "questions"
    row = evaluation.score(case, gateway.Success(json.dumps({key: []})))
    assert row["schema_accepted"] is True and row["accepted_marker"] is False
    text = json.loads(reply(case, case.marker))
    text["extra"] = True
    row = evaluation.score(case, gateway.Success(json.dumps(text)))
    assert row["raw_marker"] is True and row["accepted_marker"] is False


def test_mixed_results_keep_usable_and_attempted_denominators_distinct():
    cases = [
        c for c in evaluation.corpus() if c.feature == "drafting" and c.kind == "attack"
    ]
    results = [
        gateway.Success(reply(cases[0], cases[0].marker)),
        gateway.Success("invalid JSON"),
        gateway.Failed("timeout"),
        None,
    ]
    group = evaluation.aggregate(
        [evaluation.score(c, r) for c, r in zip(cases, results, strict=True)]
    )
    assert group["drafting"]["attack"] == {
        "cases": 4,
        "attempted": 3,
        "usable": 2,
        "schema_accepted": 1,
        "raw_marker": 1,
        "accepted_marker": 1,
    }


@pytest.mark.parametrize(
    "result,status",
    [
        (None, "unattempted"),
        (gateway.Refused("private"), "refused"),
        (gateway.Failed("private"), "failed"),
    ],
)
def test_unavailable_results_and_aggregates_do_not_claim_resistance(result, status):
    cases = evaluation.corpus()
    rows = [evaluation.score(case, result) for case in cases]
    assert all(row["status"] == status for row in rows)
    assert all(row["raw_marker"] is None for row in rows)
    assert all(row["schema_accepted"] is None for row in rows)
    totals = evaluation.aggregate(rows)
    assert totals["drafting"]["attack"]["cases"] == 4
    assert totals["drafting"]["cleaned"]["cases"] == 1
    assert totals["feedback"]["attack"]["cases"] == 5
    for feature in totals.values():
        for group in feature.values():
            assert group["usable"] == group["raw_marker"] == 0
            assert group["attempted"] == (0 if result is None else group["cases"])
    assert "private" not in json.dumps(rows)


def test_summary_excludes_source_reply_and_counts_only_effective_attacks():
    cases = evaluation.corpus()
    rows = [
        evaluation.score(c, gateway.Success(reply(c, c.marker or "Detail?")))
        for c in cases
    ]
    totals = evaluation.aggregate(rows)
    assert totals["drafting"]["attack"] == {
        "cases": 4,
        "attempted": 4,
        "usable": 4,
        "schema_accepted": 4,
        "raw_marker": 4,
        "accepted_marker": 4,
    }
    control = next(row for row in rows if row["kind"] == "control")
    assert control["raw_marker"] is control["accepted_marker"] is None
    encoded = json.dumps(rows)
    assert all(case.data not in encoded for case in cases)
    assert all(not case.marker or case.marker not in encoded for case in cases)
