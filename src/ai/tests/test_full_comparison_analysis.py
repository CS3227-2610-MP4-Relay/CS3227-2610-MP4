"""Offline metadata audit, duplicate weighting, and scenario paired summaries."""

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from ai import drafting, gateway


@pytest.fixture(scope="module")
def analysis(app_context_tree):
    spec = importlib.util.spec_from_file_location(
        "comparison_analysis", app_context_tree / "analyze.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def experiment(analysis, app_context_tree):
    scenarios = {
        s["id"]: s
        for s in analysis.load_json(
            app_context_tree.parent / "calibration/fixtures.json"
        )["scenarios"]
    }
    schedule = [
        {
            "scenario": scenario,
            "model": model,
            "condition": condition,
            "repetition": rep,
            "request_sha256": "a" * 64,
        }
        for rep in range(1, 6)
        for scenario in scenarios
        for model in analysis.MODELS
        for condition in analysis.CONDITIONS
    ]
    rows = []
    assessments = []
    ids = {}
    for ordinal, job in enumerate(schedule, 1):
        cell = tuple(job[key] for key in ("scenario", "model", "condition"))
        if cell not in ids:
            ids[cell] = f"g-{len(ids) + 1:04d}"
            assessments.append(
                {
                    "candidate": ids[cell],
                    "scenario": job["scenario"],
                    "checks": {
                        check["id"]: {
                            "judgment": "met",
                            "evidence": "/drafts"
                            if job["scenario"].startswith("D")
                            else "/questions",
                            "reason": "Supported by collection.",
                        }
                        for check in scenarios[job["scenario"]]["checks"]
                    },
                }
            )
        rows.append(
            dict(
                job,
                id=f"call-{ordinal:04d}",
                ordinal=ordinal,
                started_at="2026-11-10T00:00:00+00:00",
                elapsed_ms=100,
                freeze_sha256="b" * 64,
                instructions_version="drafting-2"
                if job["scenario"].startswith("D")
                else "observation-feedback-3",
                status="success",
                code=None,
                schema_accepted=True,
                schema_error=None,
                accepted_items=1,
                reply_sha256="c" * 64,
                validated_sha256="d" * 64,
                grading_id=ids[cell],
                prompt_tokens=10,
                completion_tokens=None,
                total_tokens=None,
                interrupted=False,
            )
        )
    hashes = {"fixtures.json": "e" * 64, "rubric.md": "f" * 64}
    documents = [
        {
            "version": "1",
            "assessor": "test",
            "inputs": hashes.copy(),
            "assessments": assessments,
        }
    ]
    return rows, schedule, scenarios, documents, hashes


def run(analysis, experiment, partial=False):
    return analysis.summarize(*experiment, "b" * 64, partial=partial)


def test_duplicate_weighting_and_paired_means(analysis, experiment):
    rows, _, _, documents, _ = experiment
    target = next(a for a in documents[0]["assessments"] if a["scenario"] == "D1")
    for check in target["checks"].values():
        check["judgment"] = "unmet"
    result = run(analysis, experiment)
    cell = result["cells"][0]
    assert cell["attempts"] == 5
    assert cell["unique_parsed"] == 1
    assert cell["all_checks_met"] == 0
    assert next(iter(cell["criteria"].values()))["unmet"] == 5
    aggregate = result["scenario_averages"][0]
    assert aggregate["success_per_attempt"]["mean"] == pytest.approx(5 / 6)
    paired = result["paired_deltas"][0]
    assert paired["success_per_attempt"]["mean_delta"] == pytest.approx(1 / 6)
    assert cell["tokens"]["completion_tokens"] == {
        "sum_available": None,
        "available": 0,
        "missing": 5,
    }
    assert len(rows) == 540


def test_missing_judgment_default_rejected_partial_visible(analysis, experiment):
    experiment[3][0]["assessments"].pop()
    with pytest.raises(ValueError, match="missing accepted"):
        run(analysis, experiment)
    result = run(analysis, experiment, partial=True)
    assert result["assessed_unique"] == 107
    assert result["cells"][-1]["fully_assessed"] == 0
    assert next(iter(result["cells"][-1]["criteria"].values()))["ungraded"] == 5


@pytest.mark.parametrize(
    "mutation,error",
    [
        (lambda e: e[3][0]["inputs"].update({"rubric.md": "0" * 64}), "hash mismatch"),
        (
            lambda e: e[3][0]["assessments"].append(
                copy.deepcopy(e[3][0]["assessments"][0])
            ),
            "duplicate grading",
        ),
        (
            lambda e: e[3][0]["assessments"][0].update(scenario="D2"),
            "scenario mismatch",
        ),
        (lambda e: e[0][0].update(request_sha256="0" * 64), "frozen request"),
        (lambda e: e[0][0].update(elapsed_ms=float("nan")), "elapsed"),
        (lambda e: e[0][0].update(raw="unsafe"), "measurement fields"),
        (lambda e: e[0][108].update(grading_id="g-9999"), "duplicate did not reuse"),
    ],
)
def test_audit_rejects_mismatches(analysis, experiment, mutation, error):
    mutation(experiment)
    with pytest.raises(ValueError, match=error):
        run(analysis, experiment)


def test_failure_unavailable_and_unattempted_denominators(analysis, experiment):
    rows = experiment[0]
    rows[0].update(
        status="failed",
        code="timeout",
        schema_accepted=None,
        accepted_items=None,
        reply_sha256=None,
        validated_sha256=None,
        grading_id=None,
    )
    rows[108].update(
        schema_accepted=False,
        schema_error="json",
        accepted_items=None,
        validated_sha256=None,
        grading_id=None,
    )
    check = next(iter(experiment[3][0]["assessments"][0]["checks"].values()))
    check["judgment"] = "unavailable"
    cell = run(analysis, experiment)["cells"][0]
    assert (
        cell["attempts"],
        cell["provider_failures"],
        cell["schema_failures"],
        cell["schema_accepted"],
    ) == (5, 1, 1, 3)
    assert cell["fully_assessed"] == 0
    assert cell["success_per_assessed"] is None
    assert next(iter(cell["criteria"].values())) == {
        "met": 0,
        "unmet": 0,
        "unavailable": 3,
        "ungraded": 2,
    }
    del rows[108:]
    with pytest.raises(ValueError, match="incomplete"):
        run(analysis, experiment)
    # Only judgments relevant to attempted accepted answers may be supplied.
    experiment[3][0]["assessments"] = [
        a
        for a in experiment[3][0]["assessments"]
        if a["candidate"] in {row["grading_id"] for row in rows}
    ]
    partial = run(analysis, experiment, partial=True)
    assert partial["cells"][0]["unattempted"] == 4


@pytest.mark.parametrize(
    "pointer,feature,count,expected",
    [
        ("/drafts/0/expected_result", "drafting", 1, True),
        ("/drafts/1", "drafting", 1, False),
        ("/questions", "feedback", 0, True),
        ("/questions/0", "feedback", 0, False),
        ("/drafts/0/criteria/0", "drafting", 1, False),
        ("/questions/0/title", "feedback", 1, False),
    ],
)
def test_structural_evidence_pointers(analysis, pointer, feature, count, expected):
    assert analysis.pointer_valid(pointer, feature, count) is expected


def test_frozen_order_hash_and_requests(analysis):
    requests = [
        {
            "scenario": f"{prefix}{index}",
            "model": model,
            "condition": condition,
            "request_sha256": "a" * 64,
        }
        for prefix in "DF"
        for index in range(1, 7)
        for model in analysis.MODELS
        for condition in analysis.CONDITIONS
    ]
    manifest = {
        "version": 1,
        "order_seed": 20261110,
        "repetitions": 5,
        "calls": 540,
        "sha256": {},
        "requests": requests,
        "schedule_sha256": "wrong",
    }
    with pytest.raises(ValueError, match="schedule hash"):
        analysis.frozen_schedule(manifest)
    rng = analysis.random.Random(20261110)
    jobs = []
    for rep in range(1, 6):
        block = list(requests)
        rng.shuffle(block)
        jobs.extend(
            [
                [
                    rep,
                    row["scenario"],
                    row["model"],
                    row["condition"],
                    row["request_sha256"],
                ]
                for row in block
            ]
        )
    manifest["schedule_sha256"] = hashlib.sha256(
        json.dumps(jobs, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    assert len(analysis.frozen_schedule(manifest)) == 540
    manifest["requests"][0]["scenario"] = "D2"
    with pytest.raises(ValueError, match="frozen request"):
        analysis.frozen_schedule(manifest)


def test_unexpected_source_rejected_before_any_read(analysis, monkeypatch):
    def forbidden(path):
        pytest.fail("unexpected file read")

    monkeypatch.setattr(analysis, "digest", forbidden)
    with pytest.raises(ValueError, match="source paths"):
        analysis.audit_sources(
            {".env.local": "a" * 64}, Path(analysis.__file__).parents[3]
        )


def test_interrupted_invocation_retained_and_stops(analysis, experiment):
    rows = experiment[0]
    del rows[1:]
    rows[0].update(
        status="failed",
        code="provider-error",
        schema_accepted=None,
        schema_error=None,
        accepted_items=None,
        reply_sha256=None,
        validated_sha256=None,
        grading_id=None,
        interrupted=True,
    )
    experiment[3][0]["assessments"] = []
    result = run(analysis, experiment, partial=True)
    assert result["attempts"] == 1
    assert result["interrupted_invocations"] == 1
    assert result["cells"][0]["provider_failures"] == 1
    rows[0]["code"] = "timeout"
    with pytest.raises(ValueError, match="interrupted"):
        run(analysis, experiment, partial=True)


@pytest.mark.parametrize(
    "field,code",
    [("title", "title"), ("steps", "steps"), ("expected_result", "expected")],
)
def test_production_parser_errors_survive_runner_and_analysis(
    analysis, experiment, field, code, monkeypatch, app_context_tree
):
    spec = importlib.util.spec_from_file_location(
        "analysis_runner_regression", app_context_tree / "runner.py"
    )
    runner = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, runner)
    spec.loader.exec_module(runner)
    draft = {
        "title": "Save item",
        "steps": "Select Save.",
        "expected_result": "Item appears.",
        "criteria": ["C1"],
    }
    draft[field] = ""
    reply = json.dumps({"drafts": [draft]})
    with pytest.raises(drafting.InvalidReply) as failure:
        drafting.parse(reply, ["C1"])
    assert failure.value.code == code
    row = experiment[0][0]
    cell = runner.Cell(row["model"], row["condition"], experiment[2]["D1"], "{}")
    observed, candidate = runner.observe(gateway.Success(reply), cell)
    assert candidate is None
    assert observed["schema_error"] == code
    row.update(observed)
    result = run(analysis, experiment)
    assert result["cells"][0]["schema_failures"] == 1
    assert result["cells"][0]["schema_accepted"] == 4
    if field == "expected_result":
        row["schema_error"] = "expected_result"
        with pytest.raises(ValueError, match="schema error"):
            run(analysis, experiment)
