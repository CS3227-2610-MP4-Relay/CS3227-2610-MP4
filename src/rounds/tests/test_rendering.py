"""RND-1.7: round titles under the rendering rule for every round action."""

import pytest
from django.utils.html import escape

from .conftest import NEW, detail, edit, page

pytestmark = [pytest.mark.django_db, pytest.mark.ac("RND-1.7")]

MARKUP = "<script>alert(1)</script>\"'><img src=x onerror=alert(2)>&amp;"
FSI, PDI = "\u2068", "\u2069"
BIDI_AND_INVISIBLE = "abc\u202edef\u200bghi\u2066jkl"


def title_tag(html):
    return html.split("<title>", 1)[1].split("</title>", 1)[0]


def assert_no_raw_markup(html):
    assert "<script>" not in html
    assert "<img" not in html


def test_markup_is_escaped_on_round_page_home_and_edit_form(coord_client, make_round):
    made = make_round(MARKUP)
    round_page = page(coord_client.get(detail(made.pk)))
    assert f'<h1><span dir="auto">{escape(MARKUP)}</span></h1>' in round_page
    assert title_tag(round_page) == FSI + escape(MARKUP) + PDI
    home = page(coord_client.get("/coordinator/"))
    assert f'<span dir="auto">{escape(MARKUP)}</span></a> (Draft)</li>' in home
    form = page(coord_client.get(edit(made.pk)))
    assert f'value="{escape(MARKUP)}"' in form
    for html in (round_page, home, form):
        assert_no_raw_markup(html)


@pytest.mark.parametrize("action", ["create", "retitle"])
def test_markup_in_a_refused_title_is_escaped_in_the_form(
    coord_client, make_round, action
):
    made = make_round()
    refused = MARKUP + "x" * 120
    url = NEW if action == "create" else edit(made.pk)
    html = page(coord_client.post(url, {"title": refused}))
    assert f'value="{escape(refused)}"' in html
    assert_no_raw_markup(html)


def test_page_title_drops_bidi_controls_and_isolates_the_title(
    coord_client, make_round
):
    made = make_round(
        "Synthetic \u202aa\u202bb\u202cc\u202dd\u202ee\u2066f\u2067g\u2068h\u2069i"
    )
    assert title_tag(page(coord_client.get(detail(made.pk)))) == (
        FSI + "Synthetic abcdefghi" + PDI
    )


def test_stray_pop_isolate_cannot_escape_the_page_title(coord_client, make_round):
    made = make_round("Synthetic \u2069\u202eReversed")
    title = title_tag(page(coord_client.get(detail(made.pk))))
    assert title == FSI + "Synthetic Reversed" + PDI
    assert title.count(FSI) == 1 and title.count(PDI) == 1


def test_line_breaks_are_kept_inside_the_isolated_element(coord_client, make_round):
    made = make_round("Line one\nLine two")
    round_page = page(coord_client.get(detail(made.pk)))
    lines = '<span dir="auto">Line one</span><br><span dir="auto">Line two</span>'
    assert f"<h1>{lines}</h1>" in round_page
    home = page(coord_client.get("/coordinator/"))
    assert f"{lines}</a> (Draft)</li>" in home


def test_bidi_and_zero_width_characters_stay_inside_the_title_element(
    coord_client, make_round
):
    made = make_round(BIDI_AND_INVISIBLE)
    round_page = page(coord_client.get(detail(made.pk)))
    heading = (
        f'<h1><span dir="auto">{BIDI_AND_INVISIBLE}</span></h1>\n<p>State: Draft</p>'
    )
    assert heading in round_page
    assert round_page.count("\u202e") == 1
    home = page(coord_client.get("/coordinator/"))
    assert f'<span dir="auto">{BIDI_AND_INVISIBLE}</span></a> (Draft)</li>' in home
    assert home.count("\u202e") == 1
    form = page(coord_client.get(edit(made.pk)))
    assert f'value="{BIDI_AND_INVISIBLE}" dir="auto"' in form
    assert form.count("\u202e") == 1


def test_pages_do_not_reset_unicode_bidi(coord_client, make_round):
    made = make_round()
    for url in (NEW, detail(made.pk), edit(made.pk), "/coordinator/"):
        assert "unicode-bidi" not in page(coord_client.get(url))


# Every separator str.splitlines() recognises, other than line feed and carriage return.
PARAGRAPH_SEPARATORS = [
    chr(code) for code in (0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029)
]
LINE_BREAKS = [chr(10), chr(13), chr(13) + chr(10), *PARAGRAPH_SEPARATORS]


@pytest.mark.parametrize(
    "separator", LINE_BREAKS, ids=lambda sep: "+".join(f"U{ord(c):04X}" for c in sep)
)
def test_each_line_is_isolated_in_its_own_element(coord_client, make_round, separator):
    rlo = chr(0x202E)
    made = make_round("x" + separator + rlo + "abc")
    lines = f'<span dir="auto">x</span><br><span dir="auto">{rlo}abc</span>'
    round_page = page(coord_client.get(detail(made.pk)))
    assert f"<h1>{lines}</h1>" + chr(10) + "<p>State: Draft</p>" in round_page
    assert title_tag(round_page) == FSI + "x abc" + PDI
    home = page(coord_client.get("/coordinator/"))
    assert f'<li><a href="{detail(made.pk)}">{lines}</a> (Draft)</li>' in home
    for html in (round_page, home):
        for raw in PARAGRAPH_SEPARATORS:
            assert raw not in html
