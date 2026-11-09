"""Fake-transport verification for the explicitly invoked local experiment."""

import importlib.util
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai import gateway

PATH = (
    Path(__file__).resolve().parents[3]
    / "experiments/app-context/full-comparison/runner.py"
)


@pytest.fixture
def runner():
    previous = os.environ.get("DJANGO_SETTINGS_MODULE")
    spec = importlib.util.spec_from_file_location("full_comparison_runner", PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert os.environ.get("DJANGO_SETTINGS_MODULE") == previous
    return module


@pytest.mark.parametrize(
    "inherited", ["relay.settings.local", "relay.settings.production"]
)
def test_uninitialized_startup_selects_safe_settings_before_setup(
    monkeypatch, inherited
):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", inherited)
    monkeypatch.setattr(
        sys.modules["django.apps"], "apps", SimpleNamespace(ready=False)
    )
    selected = []
    monkeypatch.setattr(
        sys.modules["django"],
        "setup",
        lambda: selected.append(os.environ["DJANGO_SETTINGS_MODULE"]),
    )
    spec = importlib.util.spec_from_file_location("full_comparison_startup", PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert selected == ["relay.settings.base"]
    monkeypatch.setattr(module, "load_dotenv", lambda: pytest.fail("dotenv called"))
    assert module.main([]) == 0


def test_inputs_schedule_and_exact_request_order(runner):
    ordered = runner.cells()
    assert len(ordered) == len({c.request_sha256 for c in ordered}) == 108
    fixture = json.loads(
        (runner.HERE.parent / "calibration/fixtures.json").read_bytes()
    )
    targets = {s["id"]: s for s in fixture["scenarios"]}
    for cell in ordered:
        data = json.loads(cell.data)
        assert list(data)[-1] == "background"
        background = data.pop("background")
        assert type(background) is str
        assert bool(background) == (cell.condition != "relevant-only")
        assert data == targets[cell.scenario["id"]]["data"]
    assert ordered[0].scenario["id"] == "D1"
    assert [c.condition for c in ordered[:3]] == list(runner.CONDITIONS)
    rng = random.Random(20261110)
    jobs = runner.schedule(ordered)
    assert len(jobs) == 540
    for repeat in range(1, 6):
        expected = list(ordered)
        rng.shuffle(expected)
        assert jobs[(repeat - 1) * 108 : repeat * 108] == [
            (repeat, c) for c in expected
        ]
    assert set(Counter(c.request_sha256 for _, c in jobs).values()) == {5}
    with pytest.raises(ValueError):
        runner.schedule(ordered[:-1])


def test_parsing_target_labels_sanitization_and_array_order(runner):
    cell = next(c for c in runner.cells() if c.scenario["id"] == "D2")
    draft = {
        "title": "Archive",
        "steps": "1. Select Archive.",
        "expected_result": "Archived.",
        "criteria": ["C2", "C1"],
    }
    row, candidate = runner.observe(
        gateway.Success(json.dumps({"drafts": [draft]})), cell
    )
    assert row["schema_accepted"] is True and row["accepted_items"] == 1
    draft["criteria"].reverse()
    other, _ = runner.observe(gateway.Success(json.dumps({"drafts": [draft]})), cell)
    assert row["validated_sha256"] != other["validated_sha256"]
    draft["criteria"] = ["C99"]
    invalid, candidate = runner.observe(
        gateway.Success(json.dumps({"drafts": [draft]})), cell
    )
    assert invalid["schema_error"] == "label" and candidate is None
    private, _ = runner.observe(gateway.Failed("SECRET", gateway.Usage(-1)), cell)
    assert private["code"] == "provider-error"
    assert private["prompt_tokens"] is None
    assert "SECRET" not in json.dumps(private)


@pytest.fixture
def offline_live(runner, monkeypatch, tmp_path, settings):
    ordered = runner.cells()
    frozen = runner.manifest(ordered)
    monkeypatch.setattr(runner, "HERE", tmp_path)
    monkeypatch.setattr(runner, "cells", lambda: ordered)
    monkeypatch.setattr(runner, "manifest", lambda cells: frozen)
    monkeypatch.setattr(runner, "load_dotenv", lambda: None)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        gateway,
        "_configuration",
        lambda: ("https://synthetic.invalid", os.environ["SOC_LLM_MODEL"], "synthetic"),
    )
    settings.SOC_LLM_LIVE = True
    (tmp_path / "frozen.json").write_text(json.dumps(frozen), encoding="utf-8")
    return tmp_path, frozen


def test_default_offline_and_freeze_no_overwrite(runner, monkeypatch, tmp_path, capsys):
    ordered = runner.cells()
    manifest = runner.manifest(ordered)
    monkeypatch.setattr(runner, "HERE", tmp_path)
    monkeypatch.setattr(runner, "cells", lambda: ordered)
    monkeypatch.setattr(runner, "manifest", lambda cells: manifest)
    monkeypatch.setattr(runner, "load_dotenv", lambda: pytest.fail("dotenv called"))
    assert runner.main([]) == 0
    assert json.loads(capsys.readouterr().out)["calls_if_live"] == 540
    assert runner.main(["--freeze"]) == 0
    raw = (tmp_path / "frozen.json").read_bytes()
    assert b"\n" in raw and b"\r\n" not in raw
    assert runner.main(["--freeze"]) == 1
    assert (tmp_path / "frozen.json").read_bytes() == raw


def test_freeze_tamper_precedes_dotenv_and_output(runner, offline_live, monkeypatch):
    folder, frozen = offline_live
    frozen["calls"] = 541
    # The on-disk freeze retains 540 while the computed current manifest changed.
    monkeypatch.setattr(runner, "load_dotenv", lambda: pytest.fail("dotenv called"))
    output = folder / "rows.jsonl"
    assert runner.main(["--live", "--show-candidates", "--output", str(output)]) == 1
    assert not output.exists()


def test_all_model_configuration_preflight_precedes_calls(
    runner, offline_live, monkeypatch
):
    folder, _ = offline_live
    checked = []

    def configuration():
        model = os.environ["SOC_LLM_MODEL"]
        checked.append(model)
        return None if model == runner.MODELS[-1] else ("url", model, "key")

    monkeypatch.setattr(gateway, "_configuration", configuration)
    monkeypatch.setattr(gateway, "_transport", lambda *args: pytest.fail("provider"))
    output = folder / "rows.jsonl"
    assert runner.main(["--live", "--show-candidates", "--output", str(output)]) == 1
    assert checked == list(runner.MODELS)
    assert not output.exists()


def test_full_budget_dedup_cell_isolation_and_stdout_privacy(
    runner, offline_live, monkeypatch, capsys
):
    folder, _ = offline_live
    attempts = []
    sleeps = []

    def transport(instructions, data, deadline):
        attempts.append((instructions, data, deadline))
        key = "drafts" if "Draft manual" in instructions else "questions"
        return gateway.Success(json.dumps({key: []}), gateway.Usage(10, 2, 12))

    monkeypatch.setattr(gateway, "_transport", transport)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)
    output = folder / "rows.jsonl"
    assert runner.main(["--live", "--show-candidates", "--output", str(output)]) == 0
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert b"\n" in output.read_bytes() and b"\r\n" not in output.read_bytes()
    views = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(attempts) == len(rows) == len(views) == 540
    assert sleeps == [1] * 539
    assert all(deadline > 0 for _, _, deadline in attempts)
    assert len({r["grading_id"] for r in rows}) == 108
    assert set(Counter(r["grading_id"] for r in rows).values()) == {5}
    assert sum("untrusted_candidate" in view for view in views) == 108
    assert all(
        not {"model", "condition", "data", "request_sha256"} & view.keys()
        for view in views
    )
    assert "untrusted_candidate" not in output.read_text()
    assert rows[0]["id"] == "call-0001" and rows[-1]["id"] == "call-0540"
    assert runner.main(["--live", "--show-candidates", "--output", str(output)]) == 1
    assert len(attempts) == 540


@pytest.mark.parametrize("kind", ["refusal", "exception", "keyboard-interrupt"])
def test_stop_without_retry_and_failure_privacy(
    runner, offline_live, monkeypatch, capsys, kind
):
    folder, _ = offline_live
    attempts = []

    def transport(*args):
        attempts.append(args)
        if kind == "exception":
            raise RuntimeError("PRIVATE PROVIDER BODY")
        if kind == "keyboard-interrupt":
            raise KeyboardInterrupt("PRIVATE PROVIDER BODY")
        return gateway.Refused("quota")

    monkeypatch.setattr(gateway, "_transport", transport)
    output = folder / "rows.jsonl"
    assert runner.main(["--live", "--show-candidates", "--output", str(output)]) == 1
    assert len(attempts) == 1
    capture = capsys.readouterr()
    assert "PRIVATE" not in capture.out + capture.err + output.read_text()
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["interrupted"] is (kind != "refusal")
    if kind != "refusal":
        assert rows[0]["status"] == "failed"
        assert rows[0]["code"] == "provider-error"
        assert rows[0]["reply_sha256"] is None
        assert rows[0]["validated_sha256"] is None
        assert rows[0]["elapsed_ms"] >= 0
        assert json.loads(capture.out)["interrupted"] is True


def test_background_validation_and_source_hash_tamper(runner, monkeypatch, tmp_path):
    (tmp_path / "calibration").mkdir()
    folder = tmp_path / "full-comparison"
    folder.mkdir()
    raw = (runner.HERE.parent / "calibration/fixtures.json").read_bytes()
    source = tmp_path / "calibration/fixtures.json"
    source.write_bytes(raw)
    (folder / "backgrounds.json").write_text(
        json.dumps({"app-clutter": [], "off-topic": "text"})
    )
    monkeypatch.setattr(runner, "HERE", folder)
    with pytest.raises(ValueError, match="invalid-backgrounds"):
        runner.cells()
    source.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="fixtures-changed"):
        runner.cells()
