"""Rule 5: round text refuses text-direction controls, and only those.

Each round text field is reached through every route that submits it. Characters
and accepted texts are spread pairwise over those field routes rather than
combined exhaustively. Non-ASCII characters are written as escapes.
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import pytest
from django.db import transaction
from django.utils.html import escape

from rounds import services
from rounds.models import Build, Case, CaseCriterion, Criterion, Round

from .conftest import IMG_TAG, MARKUP, NEW, SCRIPT_TAG, edit, locked, page, snapshot

pytestmark = pytest.mark.django_db

DIRECTION = "Hidden text-direction characters are not allowed."
NULL_MESSAGE = "Null characters are not allowed."

# The text-direction controls, the 9 characters rule 5 refuses.
CONTROLS = [
    "\u202a",  # LEFT-TO-RIGHT EMBEDDING
    "\u202b",  # RIGHT-TO-LEFT EMBEDDING
    "\u202c",  # POP DIRECTIONAL FORMATTING
    "\u202d",  # LEFT-TO-RIGHT OVERRIDE
    "\u202e",  # RIGHT-TO-LEFT OVERRIDE
    "\u2066",  # LEFT-TO-RIGHT ISOLATE
    "\u2067",  # RIGHT-TO-LEFT ISOLATE
    "\u2068",  # FIRST STRONG ISOLATE
    "\u2069",  # POP DIRECTIONAL ISOLATE
]

# Text that stays allowed, including other format characters: ZWJ, ZWNJ and the
# direction marks that pasted Hebrew and Arabic text often carries.
ACCEPTED = {
    "lrm": "Synthetic\u200e 2.0",
    "rlm-hebrew": "\u05e9\u05dc\u05d5\u05dd\u200f 2",
    "alm-arabic": "\u0645\u0631\u062d\u0628\u0627\u061c 3",
    "zwj-emoji": "\U0001f469\u200d\U0001f4bb Synthetic",
    "zwnj-persian": "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",
    "hebrew": "\u05e9\u05dc\u05d5\u05dd 2",
    "arabic": "\u0645\u0631\u062d\u0628\u0627",
    "accented": "Caf\u00e9 r\u00e9sume\u0301 \u00c5ngstr\u00f6m",
    "cjk": "\u6e2c\u8a66\u7528\u4f8b",
    "curly-quotes": "\u201cSynthetic\u201d \u2018text\u2019",
}


@dataclass(frozen=True)
class FieldRoute:
    """One round text field reached through one route."""

    id: str
    criterion: str
    field: str
    limit: int
    route: str
    following: str


FIELD_ROUTES = [
    FieldRoute("round-title-create", "RND-1.3", "title", 120, "create", "<button"),
    FieldRoute("round-title-retitle", "RND-1.3", "title", 120, "retitle", "<button"),
    FieldRoute("criterion-new", "RND-2.4", "text", 500, "criterion-new", "<button"),
    FieldRoute("criterion-edit", "RND-2.4", "text", 500, "criterion-edit", "<button"),
    FieldRoute("case-title-new", "RND-2.4", "title", 120, "case-new", 'name="steps"'),
    FieldRoute("case-title-edit", "RND-2.4", "title", 120, "case-edit", 'name="steps"'),
    FieldRoute(
        "steps-new", "RND-2.4", "steps", 2000, "case-new", 'name="expected_result"'
    ),
    FieldRoute(
        "steps-edit", "RND-2.4", "steps", 2000, "case-edit", 'name="expected_result"'
    ),
    FieldRoute(
        "expected-new", "RND-2.4", "expected_result", 1000, "case-new", "<legend>"
    ),
    FieldRoute(
        "expected-edit", "RND-2.4", "expected_result", 1000, "case-edit", "<legend>"
    ),
    FieldRoute(
        "label-publish", "RND-3.2", "label", 100, "publish", "Publish round</button>"
    ),
    FieldRoute(
        "label-retest", "RND-5.2", "label", 100, "retest", "Request retest</button>"
    ),
]
BY_ID = {item.id: item for item in FIELD_ROUTES}


def prepared(make_round, item):
    """The round, the record to edit if any, and a linked criterion."""
    state = Round.State.DRAFT
    round_ = make_round("Synthetic round")
    linked = Criterion.objects.create(round=round_, text="Synthetic link")
    case = Case.objects.create(
        round=round_,
        title="Synthetic old case",
        steps="Synthetic old steps",
        expected_result="Synthetic old result",
    )
    CaseCriterion.objects.create(case=case, criterion=linked)
    if item.route == "retest":
        with transaction.atomic():
            services.publish(locked(round_), "Synthetic 1.0")
        state = Round.State.OPEN
    round_.refresh_from_db()
    assert round_.state == state
    return round_, linked, case


def post(client, item, round_, linked, case, value):
    """Submit `value` in the field, with every other field valid."""
    base = f"/coordinator/rounds/{round_.pk}/"
    if item.route == "create":
        return client.post(NEW, {"title": value})
    if item.route == "retitle":
        return client.post(edit(round_.pk), {"title": value})
    if item.route == "criterion-new":
        return client.post(f"{base}criteria/new/", {"text": value})
    if item.route == "criterion-edit":
        return client.post(f"{base}criteria/{linked.pk}/edit/", {"text": value})
    if item.route == "publish":
        return client.post(f"{base}publish/", {"label": value})
    if item.route == "retest":
        return client.post(f"{base}retest/", {"cases": [case.pk], "label": value})
    data = {
        "title": "Synthetic case",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": [linked.pk],
        item.field: value,
    }
    if item.route == "case-new":
        return client.post(f"{base}cases/new/", data)
    return client.post(f"{base}cases/{case.pk}/edit/", data)


def saved(item, round_, linked, case):
    """The value the route stored in the field."""
    if item.route == "create":
        return Round.objects.order_by("-id").first().title
    if item.route == "retitle":
        return Round.objects.get(pk=round_.pk).title
    if item.route == "criterion-new":
        return Criterion.objects.order_by("-id").first().text
    if item.route == "criterion-edit":
        return Criterion.objects.get(pk=linked.pk).text
    if item.route in ("publish", "retest"):
        return Build.objects.filter(round=round_).order_by("-id").first().label
    if item.route == "case-new":
        return getattr(Case.objects.order_by("-id").first(), item.field)
    return getattr(Case.objects.get(pk=case.pk), item.field)


def message_next_to(html, item, message):
    """The message appears once, after the field's input, before `following`."""
    assert html.count(message) == 1
    start = html.index(f'name="{item.field}"')
    assert start < html.index(message) < html.index(item.following, start)


def at(position, char, text="Synthetic text"):
    """`text` with `char` at its start, middle or end."""
    if position == "start":
        return char + text
    if position == "end":
        return text + char
    return text[:9] + char + text[9:]


def refused_cases():
    """Each character on two or three field routes, two per field route."""
    positions = ["start", "middle", "end"]
    for n, item in enumerate(FIELD_ROUTES):
        for step, offset in enumerate((0, 5)):
            index = (n + offset) % len(CONTROLS)
            position = positions[(n + step) % len(positions)]
            yield pytest.param(
                item.id,
                index,
                position,
                id=f"{item.id}-U{ord(CONTROLS[index]):04X}-{position}",
                marks=pytest.mark.ac(item.criterion),
            )


def accepted_cases():
    """Each accepted text on two or three field routes, two per field route."""
    names = list(ACCEPTED)
    for n, item in enumerate(FIELD_ROUTES):
        for offset in (0, 3):
            name = names[(n + offset) % len(names)]
            yield pytest.param(
                item.id,
                name,
                id=f"{item.id}-{name}",
                marks=pytest.mark.ac(item.criterion),
            )


REFUSED = list(refused_cases())
ACCEPTED_CASES = list(accepted_cases())


def test_the_pairwise_cases_cover_every_character_and_text():
    refused = {CONTROLS[case.values[1]] for case in REFUSED}
    accepted = {case.values[1] for case in ACCEPTED_CASES}
    assert refused == set(CONTROLS) and accepted == set(ACCEPTED)


@pytest.mark.parametrize("route_id, index, position", REFUSED)
def test_a_direction_control_is_refused_next_to_the_field(
    coord_client, make_round, route_id, index, position
):
    item = BY_ID[route_id]
    round_, linked, case = prepared(make_round, item)
    before = snapshot()
    value = at(position, CONTROLS[index])
    response = post(coord_client, item, round_, linked, case, value)
    assert response.status_code == 200
    message_next_to(page(response), item, DIRECTION)
    assert snapshot() == before


@pytest.mark.parametrize("route_id, name", ACCEPTED_CASES)
def test_other_unicode_text_is_accepted_and_saved_exactly(
    coord_client, make_round, route_id, name
):
    item = BY_ID[route_id]
    round_, linked, case = prepared(make_round, item)
    response = post(coord_client, item, round_, linked, case, ACCEPTED[name])
    assert response.status_code == 302
    assert saved(item, round_, linked, case) == ACCEPTED[name]


@pytest.mark.parametrize(
    "route_id, kind",
    [
        pytest.param(
            "round-title-create", "only-controls", marks=pytest.mark.ac("RND-1.3")
        ),
        pytest.param("steps-edit", "only-controls", marks=pytest.mark.ac("RND-2.4")),
        pytest.param("label-retest", "only-controls", marks=pytest.mark.ac("RND-5.2")),
        pytest.param("criterion-new", "too-long", marks=pytest.mark.ac("RND-2.4")),
        pytest.param("label-publish", "too-long", marks=pytest.mark.ac("RND-3.2")),
        pytest.param("round-title-retitle", "null", marks=pytest.mark.ac("RND-1.3")),
        pytest.param("expected-new", "null", marks=pytest.mark.ac("RND-2.4")),
        pytest.param("label-retest", "null", marks=pytest.mark.ac("RND-5.2")),
    ],
)
def test_the_other_checks_come_first_and_only_their_message_shows(
    coord_client, make_round, route_id, kind
):
    item = BY_ID[route_id]
    round_, linked, case = prepared(make_round, item)
    length = f"Enter 1 to {item.limit} characters."
    if kind == "only-controls":
        value, message = " \u202e\u2066 \u200f ", length
    elif kind == "too-long":
        value, message = "\u202e" + "a" * item.limit, length
    else:
        value, message = "Synthetic\u202e" + chr(0), NULL_MESSAGE
    before = snapshot()
    response = post(coord_client, item, round_, linked, case, value)
    assert response.status_code == 200
    html = page(response)
    message_next_to(html, item, message)
    assert DIRECTION not in html
    assert snapshot() == before


@pytest.mark.parametrize(
    "route_id",
    [
        pytest.param("round-title-create", marks=pytest.mark.ac("RND-1.7")),
        pytest.param("case-title-edit", marks=pytest.mark.ac("RND-2.8")),
        pytest.param("steps-new", marks=pytest.mark.ac("RND-2.8")),
        pytest.param("label-publish", marks=pytest.mark.ac("RND-3.6")),
        pytest.param("label-retest", marks=pytest.mark.ac("RND-5.8")),
    ],
)
def test_a_refused_value_is_shown_again_escaped_and_isolated(
    coord_client, make_round, route_id
):
    item = BY_ID[route_id]
    round_, linked, case = prepared(make_round, item)
    value = MARKUP + "\u202eSynthetic"
    response = post(coord_client, item, round_, linked, case, value)
    html = page(response)
    message_next_to(html, item, DIRECTION)
    assert SCRIPT_TAG not in html and IMG_TAG not in html
    start = html.index(f'name="{item.field}"')
    tag_start = html.rindex("<", 0, start)
    tag = html[tag_start : html.index(">", start) + 1]
    assert 'dir="auto"' in tag
    if tag.startswith("<textarea"):
        assert html[tag_start:].startswith(f"{tag}\n{escape(value)}</textarea>")
    else:
        assert f'value="{escape(value)}"' in tag
    # The control appears only inside the re-shown field.
    assert html.count("\u202e") == 1


# Code points next to the refused ranges, and the direction marks (R5). U+2029 is
# a paragraph separator: mid-text it is kept, and pages show it as a line break.
NEIGHBOURS = [
    0x061B, 0x061C, 0x061D, 0x200E, 0x200F, 0x2010, 0x2029, 0x202F,
    0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F,
]  # fmt: skip


def neighbour_cases():
    """Each neighbour once, round-robin over the field routes."""
    for n, code in enumerate(NEIGHBOURS):
        item = FIELD_ROUTES[n % len(FIELD_ROUTES)]
        yield pytest.param(
            item.id,
            code,
            id=f"{item.id}-U{code:04X}",
            marks=pytest.mark.ac(item.criterion),
        )


@pytest.mark.parametrize("route_id, code", list(neighbour_cases()))
def test_characters_next_to_the_refused_ranges_are_accepted(
    coord_client, make_round, route_id, code
):
    item = BY_ID[route_id]
    round_, linked, case = prepared(make_round, item)
    value = at("middle", chr(code))
    response = post(coord_client, item, round_, linked, case, value)
    assert response.status_code == 302
    assert saved(item, round_, linked, case) == value


@pytest.mark.ac("RND-3.2")
def test_a_publish_label_with_a_control_on_a_round_without_cases_gets_only_its_message(
    coord_client, make_round
):
    round_ = make_round("Synthetic empty round")
    before = snapshot()
    response = coord_client.post(
        f"/coordinator/rounds/{round_.pk}/publish/", {"label": "Synthetic\u202e 1.0"}
    )
    assert response.status_code == 200
    html = page(response)
    message_next_to(html, BY_ID["label-publish"], DIRECTION)
    assert "Add at least one test case before publishing." not in html
    assert snapshot() == before


@pytest.mark.ac("RND-5.2")
def test_a_retest_with_a_control_and_no_case_gets_both_messages(
    coord_client, make_round
):
    item = BY_ID["label-retest"]
    round_, _, _ = prepared(make_round, item)
    before = snapshot()
    response = coord_client.post(
        f"/coordinator/rounds/{round_.pk}/retest/", {"label": "Synthetic\u2066 1.1"}
    )
    assert response.status_code == 200
    html = page(response)
    message_next_to(html, item, DIRECTION)
    no_case = "Select at least one test case."
    assert html.count(no_case) == 1
    assert html.index("</fieldset>") < html.index(no_case) < html.index("Build label")
    assert snapshot() == before


@pytest.mark.ac("RND-2.4")
@pytest.mark.parametrize("route_id", ["case-title-new", "case-title-edit"])
def test_a_case_with_a_control_and_no_criterion_gets_both_messages(
    coord_client, make_round, route_id
):
    item = BY_ID[route_id]
    round_, _, case = prepared(make_round, item)
    route = (
        f"/coordinator/rounds/{round_.pk}/cases/new/"
        if item.route == "case-new"
        else f"/coordinator/rounds/{round_.pk}/cases/{case.pk}/edit/"
    )
    data = {
        "title": "Synthetic\u202d case",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
    }
    before = snapshot()
    response = coord_client.post(route, data)
    assert response.status_code == 200
    html = page(response)
    message_next_to(html, item, DIRECTION)
    no_link = "Link at least one acceptance criterion."
    assert html.count(no_link) == 1 and html.index("<legend>") < html.index(no_link)
    assert snapshot() == before


@pytest.mark.ac("RND-1.3")
def test_a_url_encoded_title_with_a_control_is_refused(coord_client):
    body = urlencode({"title": "Synthetic\u202e round"})
    response = coord_client.post(
        NEW, body, content_type="application/x-www-form-urlencoded"
    )
    assert response.status_code == 200
    message_next_to(page(response), BY_ID["round-title-create"], DIRECTION)
    assert not Round.objects.exists()


@pytest.mark.ac("RND-1.7")
def test_a_title_with_an_escaped_control_reference_is_stored_and_shown_literally(
    coord_client,
):
    title = "Synthetic &#x202E; round"
    response = coord_client.post(NEW, {"title": title})
    assert response.status_code == 302
    made = Round.objects.get()
    assert made.title == title
    html = page(coord_client.get(response["Location"]))
    assert '<span dir="auto">Synthetic &amp;#x202E; round</span>' in html
    assert "\u202e" not in html


@pytest.mark.ac("RND-2.8")
def test_direction_marks_in_a_criterion_stay_inside_its_element(
    coord_client, make_round
):
    round_ = make_round("Synthetic round")
    marks = ("\u200e", "\u200f", "\u061c")
    text = "Synthetic" + marks[0] + " 1" + marks[1] + " 2" + marks[2] + " 3"
    response = coord_client.post(
        f"/coordinator/rounds/{round_.pk}/criteria/new/", {"text": text}
    )
    assert response.status_code == 302
    html = page(coord_client.get(response["Location"]))
    isolated = f'<span dir="auto">{text}</span>'
    assert isolated in html
    outside = html.replace(isolated, "")
    for mark in marks:
        assert mark not in outside, hex(ord(mark))
