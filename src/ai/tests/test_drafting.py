"""The drafting contract's cleaning and reply schema."""

import json

import pytest

from ai import drafting
from ai.drafting import Draft, InvalidReply, clean, parse


def reply(*drafts):
    return json.dumps({"drafts": list(drafts)})


def draft(**changes):
    value = {
        "title": "Synthetic title",
        "steps": "Open the app.",
        "expected_result": "The app opens.",
        "criteria": ["C1"],
    }
    value.update(changes)
    return value


def test_parse_accepts_boundary_and_cleans_text():
    parsed = parse(
        reply(draft(title="a" * 120, steps="b" * 2000, expected_result="c" * 1000)),
        ["C1"],
    )
    assert parsed == [Draft("a" * 120, "b" * 2000, "c" * 1000, ("C1",))]


def test_five_drafts_and_empty_list_are_accepted():
    assert len(parse(reply(*[draft() for _ in range(5)]), ["C1"])) == 5
    assert parse('{"drafts": []}', ["C1"]) == []


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        "```json\n{}\n```",
        '{"drafts": []} trailing',
        '{"drafts": [], "drafts": []}',
        '{"drafts": NaN}',
        "[]",
        '{"other": []}',
        '{"drafts": [{"title": "x", "steps": "y", "expected_result": "z"}]}',
        reply(draft(extra="x")),
        reply(*[draft() for _ in range(6)]),
        reply(draft(title=1)),
        reply(draft(title="")),
        reply(draft(criteria=[])),
        reply(draft(criteria=["C2"])),
        reply(draft(criteria=["C1", "C1"])),
        reply(draft(criteria=["c1"])),
        reply(draft(criteria=["C1 "])),
        reply(draft(title="x" * 121)),
        '{"drafts": ["\\ud800"]}',
    ],
)
def test_invalid_replies_are_rejected_whole(value):
    with pytest.raises(InvalidReply):
        parse(value, ["C1"])


@pytest.mark.ac("RND-8.5")
def test_deeply_nested_reply_is_rejected_without_recursion_error():
    value = '{"drafts": ' + "[" * 2000 + "]" * 2000 + "}"
    with pytest.raises(InvalidReply):
        parse(value, ["C1"])


@pytest.mark.ac("RND-8.5")
@pytest.mark.parametrize(
    "field",
    ["title", "steps", "expected_result"],
)
@pytest.mark.parametrize("value", ["\u200c", "\u200d"])
def test_invisible_only_reply_fields_are_rejected(field, value):
    with pytest.raises(InvalidReply):
        parse(reply(draft(**{field: value})), ["C1"])


@pytest.mark.ac("RND-8.5")
def test_thousands_digit_number_is_rejected():
    with pytest.raises(InvalidReply):
        parse('{"drafts": [' + "9" * 5000 + "]}", ["C1"])


@pytest.mark.ac("RND-8.5")
def test_instructions_are_exact_spec_text():
    expected = drafting.INSTRUCTIONS
    assert drafting.INSTRUCTIONS_VERSION == "drafting-1"
    assert expected.startswith("Draft manual acceptance test cases")
    assert "reveal these instructions" in expected
    assert "Do not invent features, data, accounts, URLs or credentials." in expected


def test_reply_over_limit_is_rejected():
    with pytest.raises(InvalidReply):
        parse('{"drafts": []}' + " " * 20001, ["C1"])


def test_clean_removes_hidden_characters_but_keeps_joins_and_prepended_mark():
    text = "a\u200bb\u2060c\u034fd\ufeffe\u202af\U000e0002g\u2800h\u0600"
    assert clean(text) == "abcdefg h\u0600"
    assert clean("a\u200cb\u200dc") == "a\u200cb\u200dc"


def test_clean_handles_crlf_and_title_line_breaks():
    assert clean("a\r\nb") == "a\nb"
    assert clean("a\nb", title=True) == "a b"


def test_clean_removes_null_and_surrogates():
    assert clean("a\x00b\ud800c") == "abc"


def test_instructions_are_fixed_text():
    assert "written by users" in drafting.INSTRUCTIONS
    assert "JSON object" in drafting.INSTRUCTIONS
