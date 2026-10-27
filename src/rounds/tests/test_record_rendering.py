"""RND-2.8: criterion and case text under the rendering rule for every round action."""

import pytest
from django.utils.html import escape

from rounds.models import Case, CaseCriterion, Criterion

from .conftest import IMG_TAG, MARKUP, SCRIPT_TAG, detail, page

pytestmark = [pytest.mark.django_db, pytest.mark.ac("RND-2.8")]

LF = chr(10)
# Right-to-left override, zero-width space and left-to-right isolate.
BIDI_AND_INVISIBLE = "abc" + chr(0x202E) + "def" + chr(0x200B) + "ghi" + chr(0x2066)


def setup(round_, text):
    """A criterion and a case linked to it, every field holding `text`."""
    item = Criterion.objects.create(round=round_, text=text)
    made = Case.objects.create(
        round=round_, title=text, steps=text, expected_result=text
    )
    CaseCriterion.objects.create(case=made, criterion=item)
    return item, made


def pages(client, round_, item, made):
    base = f"/coordinator/rounds/{round_.pk}"
    return {
        "round": page(client.get(detail(round_.pk))),
        "new case": page(client.get(f"{base}/cases/new/")),
        "edit criterion": page(client.get(f"{base}/criteria/{item.pk}/edit/")),
        "edit case": page(client.get(f"{base}/cases/{made.pk}/edit/")),
    }


def assert_no_raw_markup(html):
    assert SCRIPT_TAG not in html
    assert IMG_TAG not in html


def test_markup_is_escaped_in_content_and_form_values(coord_client, make_round):
    draft = make_round("Synthetic round")
    item, made = setup(draft, MARKUP)
    html = pages(coord_client, draft, item, made)
    isolated = f'<span dir="auto">{escape(MARKUP)}</span>'
    # Criterion text, case title, steps, expected result and the linked criterion.
    assert html["round"].count(isolated) == 5
    assert isolated in html["new case"]
    assert isolated in html["edit case"]
    assert f">\n{escape(MARKUP)}</textarea>" in html["edit criterion"]
    assert f'value="{escape(MARKUP)}"' in html["edit case"]
    assert html["edit case"].count(f">\n{escape(MARKUP)}</textarea>") == 2
    for text in html.values():
        assert_no_raw_markup(text)


@pytest.mark.parametrize("kind", ["criteria", "cases"])
def test_markup_in_a_refused_form_is_escaped(coord_client, make_round, kind):
    draft = make_round("Synthetic round")
    refused = MARKUP + "x" * 2000
    data = {"text": refused}
    if kind == "cases":
        data = {"title": refused, "steps": refused, "expected_result": refused}
    html = page(coord_client.post(f"/coordinator/rounds/{draft.pk}/{kind}/new/", data))
    assert escape(refused) in html
    assert_no_raw_markup(html)


def test_record_text_never_reaches_a_page_title(coord_client, make_round):
    draft = make_round("Synthetic round")
    item, made = setup(draft, MARKUP)
    html = pages(coord_client, draft, item, made)
    titles = {
        name: text.split("<title>", 1)[1].split("</title>", 1)[0]
        for name, text in html.items()
    }
    assert titles["new case"] == "New test case"
    assert titles["edit criterion"] == "Edit acceptance criterion"
    assert titles["edit case"] == "Edit test case"
    assert "script" not in titles["round"]


def test_line_breaks_become_one_isolated_element_per_line(coord_client, make_round):
    draft = make_round("Synthetic round")
    item, made = setup(draft, "first" + LF + "second")
    html = pages(coord_client, draft, item, made)
    lines = '<span dir="auto">first</span><br><span dir="auto">second</span>'
    assert html["round"].count(lines) == 5
    assert lines in html["new case"]


def test_bidi_and_zero_width_characters_stay_inside_their_element(
    coord_client, make_round
):
    draft = make_round("Synthetic round")
    item, made = setup(draft, BIDI_AND_INVISIBLE)
    html = pages(coord_client, draft, item, made)
    isolated = f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>'
    assert html["round"].count(isolated) == 5
    assert isolated in html["new case"]
    for character in (chr(0x202E), chr(0x200B), chr(0x2066)):
        assert html["round"].count(character) == 5
    for label in ("<h4>Steps</h4>", "<h4>Expected result</h4>", "Test cases"):
        assert label in html["round"]


def test_pages_do_not_reset_unicode_bidi(coord_client, make_round):
    draft = make_round("Synthetic round")
    item, made = setup(draft, BIDI_AND_INVISIBLE)
    for html in pages(coord_client, draft, item, made).values():
        assert "unicode-bidi" not in html
