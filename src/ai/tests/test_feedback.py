"""Saved-draft source snapshots and the questions-only contract (RES-4)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai import feedback


def source_entry():
    """Synthetic already-authorized entry; authorization belongs to the view."""
    return SimpleNamespace(
        result=SimpleNamespace(pk=11, outcome="fail", observation=" Saved detail "),
        case=SimpleNamespace(
            pk=12, title="Case", steps="Steps", expected_result="Expected"
        ),
        build=SimpleNamespace(pk=13, label="Build"),
    )


@pytest.mark.ac("RES-4.3", "RES-4.8")
def test_source_encodes_only_cleaned_selected_text_and_keeps_raw_snapshot():
    entry = source_entry()
    entry.result.observation = " \u2800\u200bDetails\r\nNext\x00 "
    criteria = [
        SimpleNamespace(pk=18, text=" First "),
        SimpleNamespace(pk=20, text="\u3164"),
    ]
    source = feedback.snapshot(entry, criteria)
    assert json.loads(feedback.encode(source)) == {
        "observation": "Details\nNext",
        "case": {"title": "Case", "steps": "Steps", "expected_result": "Expected"},
        "criteria": ["First", ""],
    }
    assert entry.result.observation == " \u2800\u200bDetails\r\nNext\x00 "
    entry.result.observation = "Details\nNext"
    assert feedback.snapshot(entry, criteria) != source


@pytest.mark.ac("RES-4.3", "RES-4.8")
def test_empty_observation_and_non_ascii_case_are_not_omitted_or_ascii_escaped():
    entry = source_entry()
    entry.result.observation = ""
    entry.case.title = "Synthetic \u4e2d\u6587"
    encoded = feedback.encode(feedback.snapshot(entry, []))
    assert "\u4e2d\u6587" in encoded
    assert json.loads(encoded)["observation"] == ""
    assert json.loads(encoded)["criteria"] == []


@pytest.mark.ac("RES-4.6")
@pytest.mark.parametrize(
    ("object_name", "field", "value"),
    [
        ("result", "pk", 99),
        ("result", "outcome", "pass"),
        ("result", "observation", "Replacement"),
        ("case", "pk", 99),
        ("case", "title", "Replacement"),
        ("case", "steps", "Replacement"),
        ("case", "expected_result", "Replacement"),
        ("build", "pk", 99),
        ("build", "label", "Replacement"),
    ],
)
def test_snapshot_detects_each_source_change(object_name, field, value):
    entry = source_entry()
    criteria = [SimpleNamespace(pk=18, text="Criterion")]
    original = feedback.snapshot(entry, criteria)
    assert original == feedback.snapshot(entry, criteria)
    setattr(getattr(entry, object_name), field, value)
    assert original != feedback.snapshot(entry, criteria)


@pytest.mark.ac("RES-4.6")
@pytest.mark.parametrize("change", ["identity", "text", "add", "remove"])
def test_snapshot_freezes_criteria_values(change):
    entry = source_entry()
    criteria = [SimpleNamespace(pk=18, text="Criterion")]
    original = feedback.snapshot(entry, criteria)
    if change == "identity":
        criteria[0].pk = 99
    elif change == "text":
        criteria[0].text = "Replacement"
    elif change == "add":
        criteria.append(SimpleNamespace(pk=19, text="Added"))
    else:
        criteria.clear()
    assert original != feedback.snapshot(entry, criteria)


@pytest.mark.ac("RES-4.3")
@pytest.mark.parametrize("size", [7999, 8000, 8001])
def test_encoded_input_limit_includes_instructions_and_json_escaping(size):
    entry = source_entry()
    entry.result.observation = ""
    base = len(feedback.INSTRUCTIONS) + len(
        feedback.encode(feedback.snapshot(entry, []))
    )
    entry.result.observation = '"' * ((size - base) // 2) + "x" * ((size - base) % 2)
    source = feedback.snapshot(entry, [])
    if size > 8000:
        with pytest.raises(feedback.InputTooLarge):
            feedback.encode(source)
    else:
        assert len(feedback.INSTRUCTIONS) + len(feedback.encode(source)) == size


@pytest.mark.ac("RES-4.8")
@pytest.mark.prompt_injection
def test_fixed_instructions_equal_versioned_spec():
    spec = (
        Path(__file__).resolve().parents[3]
        / "workflow/specs/ai/observation-feedback.md"
    ).read_text(encoding="utf-8")
    quote = (
        spec.split("Version `observation-feedback-3`", 1)[1]
        .split("\n\n", 1)[1]
        .split("\n\n", 1)[0]
    )
    assert quote == "> " + feedback.INSTRUCTIONS
    assert feedback.INSTRUCTIONS_VERSION == "observation-feedback-3"


@pytest.mark.ac("RES-4.3", "RES-4.8")
@pytest.mark.parametrize("count", [0, 1, 5])
def test_valid_question_counts_and_cleaning(count):
    raw = " \u2800Which\u200b step?\r\nDetails\x00 "
    assert (
        feedback.parse(json.dumps({"questions": [raw] * count}))
        == ["Which step?\nDetails"] * count
    )


@pytest.mark.ac("RES-4.8")
@pytest.mark.parametrize("size", [299, 300, 301])
def test_cleaned_question_length_boundary(size):
    reply = json.dumps({"questions": [" \u200b" + "x" * size + "\u3164 "]})
    if size > 300:
        with pytest.raises(feedback.InvalidReply):
            feedback.parse(reply)
    else:
        assert feedback.parse(reply) == ["x" * size]


@pytest.mark.ac("RES-4.8")
@pytest.mark.parametrize("size", [19999, 20000, 20001])
def test_raw_reply_size_boundary(size):
    reply = '{"questions": []}'
    reply += " " * (size - len(reply))
    if size > 20000:
        with pytest.raises(feedback.InvalidReply):
            feedback.parse(reply)
    else:
        assert feedback.parse(reply) == []


@pytest.mark.ac("RES-4.8")
@pytest.mark.parametrize(
    "reply",
    [
        "not json",
        '```json\n{"questions": []}\n```',
        '{"questions": []} {}',
        '{"questions": [], "questions": []}',
        '{"questions": [], "outcome": "pass"}',
        "[]",
        "null",
        "{}",
        '{"questions": null}',
        '{"questions": "Question?"}',
        '{"questions": ["Valid?", null]}',
        '{"questions": [true]}',
        '{"questions": [1]}',
        '{"questions": [NaN]}',
        '{"questions": [Infinity]}',
        '{"questions": [-Infinity]}',
        '{"questions": [1e9999]}',
        '{"questions": [{"q": "x", "q": "y"}]}',
        '{"questions": ["\\ud800"]}',
        '{"questions": ["\\udfff"]}',
        json.dumps({"questions": ["Question?"] * 6}),
        json.dumps({"questions": ["Valid?", ""]}),
        json.dumps({"questions": ["\u200c\u200d\u2800\u202a"]}),
        '{"questions": [' + "9" * 5000 + "]}",
        '{"questions": ' + "[" * 2000 + "]" * 2000 + "}",
    ],
)
@pytest.mark.prompt_injection
def test_invalid_reply_is_rejected_whole(reply):
    with pytest.raises(feedback.InvalidReply):
        feedback.parse(reply)


@pytest.mark.ac("RES-4.8")
def test_parser_recursion_failure_is_fixed_invalid_reply(monkeypatch):
    def too_deep(*args, **kwargs):
        raise RecursionError("Synthetic private detail")

    monkeypatch.setattr(feedback.json, "loads", too_deep)
    with pytest.raises(feedback.InvalidReply) as caught:
        feedback.parse('{"questions": []}')
    assert str(caught.value) == "json"


@pytest.mark.ac("RES-4.8")
@pytest.mark.prompt_injection
def test_schema_valid_untrusted_text_stays_text_without_interpretation():
    payload = bytes.fromhex(
        "3c7363726970743e69676e6f726520696e737472756374696f6e733c2f7363726970743e20"
        "68747470733a2f2f6578616d706c652e696e76616c69642f"
    ).decode()
    assert feedback.parse(json.dumps({"questions": [payload]})) == [payload]
