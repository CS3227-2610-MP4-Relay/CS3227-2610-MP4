"""The drafting contract's cleaning and reply schema."""

import json
import re
from pathlib import Path

import pytest

from ai import drafting, gateway
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
        pytest.param(reply(draft(steps=["Open the app."])), id="array-steps"),
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
@pytest.mark.prompt_injection
@pytest.mark.ac("RND-8.5")
def test_invalid_replies_are_rejected_whole(value):
    with pytest.raises(InvalidReply):
        parse(value, ["C1"])


@pytest.mark.ac("RND-8.5")
@pytest.mark.parametrize("depth", [499, 2000])
def test_deeply_nested_reply_is_rejected_without_recursion_error(depth):
    value = '{"drafts": ' + "[" * depth + "]" * depth + "}"
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
@pytest.mark.prompt_injection
def test_instructions_are_exact_spec_text():
    spec_path = (
        Path(__file__).resolve().parents[3] / "workflow/specs/ai/test-drafting.md"
    )
    spec = spec_path.read_text(encoding="utf-8")
    marker = "Version `drafting-2` is the exact constant:"
    quoted = spec.split(marker, 1)[1].strip().split("\n\n", 1)[0]
    assert quoted.startswith("> ")
    assert quoted[2:] == drafting.INSTRUCTIONS
    assert drafting.INSTRUCTIONS_VERSION == "drafting-2"


@pytest.mark.ac("RND-8.1", "RND-8.5")
def test_prompt_supplies_a_parser_accepted_example():
    assert "Example shape: " in drafting.INSTRUCTIONS
    example, _ = json.JSONDecoder().raw_decode(
        drafting.INSTRUCTIONS.split("Example shape: ", 1)[1]
    )
    assert parse(json.dumps(example), ["C1"]) == [
        Draft(
            "Short title",
            "1. Perform the action.",
            "The stated result is visible.",
            ("C1",),
        )
    ]


@pytest.mark.ac("RND-8.4")
def test_prompt_supplies_a_parser_accepted_empty_reply():
    assert "return exactly " in drafting.INSTRUCTIONS
    empty, _ = json.JSONDecoder().raw_decode(
        drafting.INSTRUCTIONS.split("return exactly ", 1)[1]
    )
    assert empty == {"drafts": []}
    assert parse(json.dumps(empty), ["C1"]) == []


@pytest.mark.ac("RND-8.5")
def test_prompt_states_current_numeric_limits():
    assert len(drafting.INSTRUCTIONS) <= 2500
    for phrase, limit in (
        ("title of at most", drafting.TITLE_LIMIT),
        ("steps in one string of at most", drafting.STEPS_LIMIT),
        ("expected result of at most", drafting.EXPECTED_LIMIT),
        ("entire reply at most", drafting.REPLY_LIMIT),
    ):
        assert f"{phrase} {limit} characters" in drafting.INSTRUCTIONS
    assert f"an array of 0 to {drafting.MAX_DRAFTS} objects" in drafting.INSTRUCTIONS


@pytest.mark.ac("RND-8.5", "RND-8.6")
@pytest.mark.parametrize("character", ['"', "\\", "\n", "\t", "界"])
def test_prompt_leaves_room_for_maximum_encoded_selection(character):
    criteria = [
        {"label": f"C{index}", "text": clean(character * 500).strip()}
        for index in range(1, 6)
    ]
    data = json.dumps({"criteria": criteria}, ensure_ascii=False)
    assert len(drafting.INSTRUCTIONS) + len(data) <= gateway.INPUT_LIMIT


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


@pytest.mark.ac("RND-8.5")
@pytest.mark.parametrize(
    "label",
    [
        "C4",
        "C0",
        "c1",
        "C1 ",
        chr(0xFF23) + "1",
        "C" + chr(0xFF11),
        chr(0x0421) + "1",
        "17",
        "Synthetic criterion one",
    ],
    ids=[
        "above-count",
        "zero",
        "lower-case",
        "trailing-space",
        "full-width-letter",
        "full-width-digit",
        "cyrillic",
        "database-id",
        "criterion-text",
    ],
)
@pytest.mark.prompt_injection
def test_unauthorized_labels_are_refused(label):
    with pytest.raises(InvalidReply) as info:
        parse(reply(draft(criteria=["C1", label])), ["C1", "C2", "C3"])
    assert info.value.code == "label"


@pytest.mark.ac("RND-8.5")
@pytest.mark.parametrize(
    ("value", "code"),
    [
        ('{"drafts": ["\\ud800"]}', "surrogate"),
        ('{"drafts": NaN}', "json"),
        ('{"drafts": [' + "9" * 5000 + "]}", "json"),
        ('{"drafts": [], "drafts": []}', "repeated-key"),
        ('{"drafts": [{"title": "x", "title": "y"}]}', "repeated-key"),
    ],
    ids=["surrogate", "nan", "long-number", "repeated-key", "nested-repeated-key"],
)
def test_each_parse_guard_rejects_with_its_own_code(value, code):
    with pytest.raises(InvalidReply) as info:
        parse(value, ["C1"])
    assert info.value.code == code


@pytest.mark.ac("RND-8.5")
def test_a_recursion_error_while_parsing_is_an_invalid_reply(monkeypatch):
    # Python 3.14 parses the deepest nesting that fits 20,000 characters, so
    # force the error a lower recursion limit or another runtime would raise.
    def deep(*args, **kwargs):
        raise RecursionError

    monkeypatch.setattr(drafting.json, "loads", deep)
    with pytest.raises(InvalidReply) as info:
        parse('{"drafts": []}', ["C1"])
    assert info.value.code == "json"


def test_cleaning_table_equals_the_contract_ranges():
    spec = (
        Path(__file__).resolve().parents[3] / "workflow/specs/ai/test-drafting.md"
    ).read_text(encoding="utf-8")
    step = spec.split("3. removes every Default_Ignorable_Code_Point", 1)[1]
    step = step.split("The remaining format characters", 1)[0]
    listed = step.split("from this fixed table", 1)[1]
    ranges = {
        (int(start, 16), int(end or start, 16))
        for start, end in re.findall(r"U\+([0-9A-F]+)(?: to U\+([0-9A-F]+))?", listed)
    }
    assert ranges == set(drafting.IGNORABLE_RANGES)


@pytest.mark.ac("RND-8.6")
@pytest.mark.parametrize(
    "code",
    [
        0xE0080,
        0xE0041,
        0x2065,
        0x17B4,
        0x180B,
        0xFFF9,
        0x13430,
        0xFE00,
        0xFE0F,
        0xE0100,
    ],
    ids=hex,
)
def test_hidden_characters_are_removed(code):
    assert clean(f"a{chr(code)}b") == "ab"


@pytest.mark.ac("RND-8.6")
@pytest.mark.parametrize("code", [0x3164, 0x115F, 0x1160, 0xFFA0, 0x2800], ids=hex)
def test_each_blank_filler_becomes_a_space(code):
    assert clean(f"a{chr(code)}b") == "a b"
