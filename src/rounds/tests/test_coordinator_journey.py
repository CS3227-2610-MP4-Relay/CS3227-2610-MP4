"""ACC-1.1, ACC-2.1, RND-1 to 3, 5 and 6: one coordinator journey over HTTP.

Every action is submitted through the form its page renders, with Django's
CSRF checks on. Browser rendering of create, add and publish is covered by
`src/e2e/`; the plan records how the two divide the work.
"""

import html as html_text
import re
from html.parser import HTMLParser

import pytest
from django.test import Client

from accounts.tests.test_demo_views import ROW, SAVE

from .conftest import page
from .test_sample_round import HOME_ITEM

pytestmark = pytest.mark.django_db

PUBLISHED = '<p role="status">Round published.</p>'
CLOSED = '<p role="status">Round closed.</p>'
WARNING = "<p>Closing makes this round read-only. It cannot be reopened.</p>"
FSI, PDI = chr(0x2068), chr(0x2069)
DRAFT_CONTROLS = (
    "Edit round</a>",
    "Add acceptance criterion",
    "Add test case",
    "Edit criterion",
    "Delete criterion",
    "Edit test case",
    "Delete test case",
    "Publish round",
    "Build label",
)


class _Forms(HTMLParser):
    """A page's forms (action, default fields, labels, buttons) and links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms, self.links = [], []
        self._form = self._text = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self._text = ("a", attrs.get("href"), [])
        elif tag == "form":
            self._form = {"action": attrs.get("action", ""), "fields": []}
            self._form.update(controls={}, labels={}, buttons=[])
            self.forms.append(self._form)
        elif self._form is None:
            return
        elif tag == "input":
            name, value = attrs.get("name"), attrs.get("value", "")
            self._form["controls"][attrs.get("id")] = (name, value)
            if attrs.get("type") != "checkbox" or "checked" in attrs:
                self._form["fields"].append((name, value))
        elif tag == "textarea":
            self._form["controls"][attrs.get("id")] = (attrs.get("name"), "")
            self._text = ("textarea", attrs.get("name"), [])
        elif tag in ("label", "button"):
            self._text = (tag, attrs.get("for"), [])

    def handle_data(self, data):
        if self._text is not None:
            self._text[2].append(data)

    def handle_endtag(self, tag):
        if self._text is None or tag != self._text[0]:
            if tag == "form":
                self._form = None
            return
        kind, key, parts = self._text
        text = "".join(parts)
        self._text = None
        if kind == "a":
            self.links.append((key, text.strip()))
        elif kind == "textarea":
            self._form["fields"].append((key, text.removeprefix("\n")))
        elif kind == "label":
            self._form["labels"][text.strip()] = key
        else:
            self._form["buttons"].append(text.strip())


def parsed(html):
    """The forms and links of one page."""
    parser = _Forms()
    parser.feed(html)
    return parser


def forms(html, button):
    """Every form on `html` with a `button` button, in page order."""
    found = [each for each in parsed(html).forms if button in each["buttons"]]
    assert found, f"no {button!r} form"
    return found


def form(html, button):
    """The one form on `html` with a `button` button."""
    found = forms(html, button)
    assert len(found) == 1, f"expected one {button!r} form, found {len(found)}"
    return found[0]


def links(html, text):
    """The hrefs of every link on `html` whose text is `text`, in page order."""
    found = [href for href, label in parsed(html).links if label == text]
    assert found, f"no {text!r} link"
    return found


def submit(client, shown, url, fill=None, check=()):
    """POST `shown` as a browser would from `url`: its token, defaults and inputs.

    `fill` maps visible labels to values; `check` names checkbox labels to tick.
    """
    data = {}
    for name, value in shown["fields"]:
        data.setdefault(name, []).append(value)
    assert "csrfmiddlewaretoken" in data, "form has no CSRF token"
    for label, value in (fill or {}).items():
        assert label in shown["labels"], f"no field labelled {label!r}"
        data[shown["controls"][shown["labels"][label]][0]] = [value]
    for label in check:
        assert label in shown["labels"], f"no checkbox labelled {label!r}"
        name, value = shown["controls"][shown["labels"][label]]
        data.setdefault(name, []).append(value)
    return client.post(shown["action"] or url, data)


def assert_redirect(response, url):
    """A successful action redirects to exactly `url`, uncached."""
    assert response.status_code == 302
    assert response["Location"] == url
    assert "no-store" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def assert_conflict(response, state, attempted):
    """A state refusal: the 409 page, uncached, without the attempted text."""
    assert response.status_code == 409
    heading = f"<h1>This action is not available while the round is {state}.</h1>"
    assert heading in page(response)
    assert attempted not in page(response)
    assert "no-store" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def assert_in_order(html, *parts):
    """Each of `parts` appears in `html` after the one before it."""
    position = 0
    for part in parts:
        found = html.find(part, position)
        assert found != -1, f"missing {part!r} after position {position}"
        position = found + len(part)


def assert_titled(html, title, attempted):
    """The round page keeps `title` in its heading and page title, not `attempted`."""
    assert f'<h1><span dir="auto">{title}</span></h1>' in html
    assert f"<title>{FSI}{title}{PDI}</title>" in html
    assert attempted not in html


def stable(html):
    """A page without its per-render CSRF tokens and one-off status messages."""
    html = re.sub(r'name="csrfmiddlewaretoken" value="[^"]*"', "", html)
    return re.sub(r'<p role="status">.*?</p>\n?', "", html)


def section(html, heading):
    """A case's or build's `<h3>` section, up to the next heading."""
    start = f'<h3><span dir="auto">{heading}</span></h3>'
    assert html.count(start) == 1, f"expected one section {heading!r}"
    rest = html[html.index(start) :]
    end = re.search(r"<h[23]>", rest[len(start) :])
    return rest if end is None else rest[: len(start) + end.start()]


def text_of(markup):
    """Isolated-lines markup as plain text, one line per `<br>`."""
    return html_text.unescape(re.sub(r"<[^>]+>", "", markup.replace("<br>", "\n")))


def current_build(html, title):
    """The current-build label shown under a case, or None."""
    found = re.search(
        r"<h4>Current build</h4>\s*<p>(.*?)</p>", section(html, title), re.DOTALL
    )
    return None if found is None else text_of(found.group(1))


def case_fields(html, title):
    """A case's stored fields and links, without its current build."""
    return section(html, title).split("<h4>Current build</h4>")[0]


def build_coverage(html, label):
    """The case titles listed under one build."""
    return re.findall(r'<li><span dir="auto">([^<]+)</span></li>', section(html, label))


def criteria_content(html):
    """The acceptance-criteria section."""
    assert_in_order(html, "<h2>Acceptance criteria</h2>", "<h2>Test cases</h2>")
    return html.split("<h2>Acceptance criteria</h2>")[1].split("<h2>Test cases</h2>")[0]


@pytest.mark.ac(
    "ACC-2.1",
    "ACC-1.1",
    "RND-1.1",
    "RND-1.2",
    "RND-2.1",
    "RND-2.2",
    "RND-3.1",
    "RND-5.1",
    "RND-5.5",
    "RND-6.1",
    "RND-6.2",
    "RND-6.3",
)
def test_a_coordinator_drives_a_round_from_demo_to_closed():
    client = Client(enforce_csrf_checks=True)

    # ACC-2.1: the start page creates a workspace whose credentials are shown
    # once, without signing the visitor in.
    start = page(client.get("/"))
    created = submit(client, form(start, "Create a demo workspace"), "/")
    assert created.status_code == 200
    assert "no-store" in created["Cache-Control"]
    assert "_auth_user_id" not in client.session
    shown = page(created)
    for text in (
        "<title>Your demo workspace</title>",
        "<h1>Your demo workspace</h1>",
        "<tr><th>Role</th><th>Username</th><th>Password</th></tr>",
        SAVE,
        '<a href="/sign-in/">Sign in</a>',
    ):
        assert text in shown
    rows = ROW.findall(shown)
    assert [role for role, _, _ in rows] == [
        "Test Coordinator",
        "Beta Tester",
        "Beta Tester",
    ]
    name = re.search(r"<p>Workspace: ([^<]*)</p>", shown).group(1)

    # ACC-1.1: the coordinator's credentials sign in to the Coordinator home.
    _, username, password = rows[0]
    sign_in = page(client.get("/sign-in/?next=/tester/"))
    signed_in = submit(
        client,
        form(sign_in, "Sign in"),
        "/sign-in/",
        {"Username": username, "Password": password},
    )
    assert_redirect(signed_in, "/coordinator/")
    home = page(client.get("/coordinator/"))
    assert "<title>Coordinator home</title>" in home
    assert f"<p>Workspace: {name}</p>" in home
    assert f"<p>Username: {username}</p>" in home
    # The sample round is observed only; RND-7 has its own tests.
    sample = re.findall(HOME_ITEM, home)
    assert [item[1:] for item in sample] == [("Sample round", "Draft")]

    # RND-1.1: create a Draft round through the form and list it on the home.
    new_url = links(home, "New round")[0]
    new = page(client.get(new_url))
    assert "<h1>New round</h1>" in new
    title = "Synthetic checkout round"
    made = submit(client, form(new, "Create round"), new_url, {"Title": title})
    assert made.status_code == 302
    url = made["Location"]
    draft = page(client.get(url))
    assert_titled(draft, title, "Synthetic ignored")
    for text in (
        "<p>State: Draft</p>",
        "Edit round</a>",
        "No acceptance criteria yet.",
        "No test cases yet.",
    ):
        assert text in draft
    home = page(client.get("/coordinator/"))
    assert re.findall(HOME_ITEM, home) == [(url, title, "Draft"), sample[0]]

    # RND-2.1: add two criteria and see both in creation order.
    first, second = "Synthetic payment is accepted.", "Synthetic receipt is shown."
    for text in (first, second):
        add_url = links(page(client.get(url)), "Add acceptance criterion")[0]
        adding = page(client.get(add_url))
        add = form(adding, "Add acceptance criterion")
        assert_redirect(submit(client, add, add_url, {"Text": text}), url)
    draft = page(client.get(url))
    assert_in_order(
        draft, "<h2>Acceptance criteria</h2>", first, second, "<h2>Test cases</h2>"
    )
    assert draft.count("Edit criterion</a>") == 2

    # RND-2.2: add two cases linked to criteria; the first links to both.
    cases = (
        {
            "Title": "Synthetic pay with a card",
            "Steps": "Synthetic open the checkout and pay.",
            "Expected result": "Synthetic order completes.",
        },
        {
            "Title": "Synthetic view the receipt",
            "Steps": "Synthetic open the completed order.",
            "Expected result": "Synthetic receipt is visible.",
        },
    )
    first_case, second_case = (case["Title"] for case in cases)
    for case, linked in zip(cases, ((first, second), (second,)), strict=True):
        case_url = links(page(client.get(url)), "Add test case")[0]
        adding = page(client.get(case_url))
        assert "<h1>New test case</h1>" in adding
        assert "<legend>Linked acceptance criteria</legend>" in adding
        assert_in_order(adding, first, second)
        add = form(adding, "Add test case")
        assert_redirect(submit(client, add, case_url, case, linked), url)
    draft = page(client.get(url))
    for case in cases:
        for value in case.values():
            assert value in section(draft, case["Title"])
    assert_in_order(section(draft, first_case), "Linked acceptance criteria", first)
    assert second in section(draft, first_case)
    assert second in section(draft, second_case)
    assert first not in section(draft, second_case)
    # Forms kept for the refusal checks after publishing and closing.
    stale_publish = form(draft, "Publish round")
    stale_case_delete = forms(draft, "Delete test case")[1]
    stale_criterion_delete = forms(draft, "Delete criterion")[1]

    # RND-1.2: retitle the round; then edit a criterion and a case (RND-2.3
    # editing observed, not marked).
    edit_url = links(draft, "Edit round")[0]
    editing = page(client.get(edit_url))
    assert f'value="{title}"' in editing
    stale_edit = form(editing, "Save")
    revised_title = "Synthetic checkout round revised"
    revised = submit(client, stale_edit, edit_url, {"Title": revised_title})
    assert_redirect(revised, url)
    criterion_url = links(draft, "Edit criterion")[0]
    editing = page(client.get(criterion_url))
    assert first in editing
    stale_criterion_edit = form(editing, "Save")
    revised_first = "Synthetic payment is accepted and recorded."
    revised = submit(
        client, stale_criterion_edit, criterion_url, {"Text": revised_first}
    )
    assert_redirect(revised, url)
    case_url = links(draft, "Edit test case")[0]
    editing = page(client.get(case_url))
    assert cases[0]["Title"] in editing and cases[0]["Steps"] in editing
    stale_case_edit = form(editing, "Save")
    revised_expected = "Synthetic order completes and is recorded."
    revised = submit(
        client, stale_case_edit, case_url, {"Expected result": revised_expected}
    )
    assert_redirect(revised, url)
    draft = page(client.get(url))
    assert_titled(draft, revised_title, "Synthetic ignored")
    assert revised_first in draft and revised_expected in draft
    assert first not in draft and cases[0]["Expected result"] not in draft
    # Each case keeps its links, the first now showing the revised text.
    assert revised_first in section(draft, first_case)
    assert second in section(draft, first_case)
    assert revised_first not in section(draft, second_case)
    assert second in section(draft, second_case)
    home = page(client.get("/coordinator/"))
    assert (url, revised_title, "Draft") in re.findall(HOME_ITEM, home)

    # RND-3.1: the publish form follows the test cases; publishing opens them.
    assert_in_order(
        draft,
        "<h2>Test cases</h2>",
        f'<h3><span dir="auto">{second_case}</span></h3>',
        "Delete test case</button></form>",
        '<label for="id_label">Build label</label>',
        "Publish round</button>",
    )
    build_label = "Synthetic build 1.0"
    published = submit(
        client, form(draft, "Publish round"), url, {"Build label": build_label}
    )
    assert_redirect(published, url)
    opened = page(client.get(url))
    assert opened.count(PUBLISHED) == 1
    assert_in_order(opened, "</h1>", PUBLISHED, "<p>State: Open</p>")
    for control in DRAFT_CONTROLS:
        assert control not in opened, control
    assert current_build(opened, first_case) == build_label
    assert current_build(opened, second_case) == build_label
    assert build_coverage(opened, build_label) == [first_case, second_case]
    published_criteria = criteria_content(opened)
    published_cases = {
        title: case_fields(opened, title) for title in (first_case, second_case)
    }

    # An Open round refuses retitling and publishing (part of RND-1.7 and
    # RND-3.6, not marked here) and stays unchanged.
    attempted = "Synthetic ignored"
    assert_conflict(client.get(edit_url), "Open", attempted)
    refused = submit(client, stale_edit, edit_url, {"Title": attempted})
    assert_conflict(refused, "Open", attempted)
    refused = submit(client, stale_publish, url, {"Build label": attempted})
    assert_conflict(refused, "Open", attempted)
    unchanged = page(client.get(url))
    assert_titled(unchanged, revised_title, attempted)
    assert stable(unchanged) == stable(opened)

    # RND-5.1 and RND-5.5: retest one case; the other keeps its current build.
    retest_url = links(opened, "Request a retest")[0]
    retest = client.get(retest_url)
    assert retest.status_code == 200
    retesting = page(retest)
    assert "<title>Request a retest</title>" in retesting
    assert "<h1>Request a retest</h1>" in retesting
    assert "<legend>Test cases to retest</legend>" in retesting
    stale_retest = form(retesting, "Request retest")
    assert retesting.count('type="checkbox"') == 2 and "checked" not in retesting
    assert first_case in stale_retest["labels"]
    assert second_case in stale_retest["labels"]
    assert "Build label" in stale_retest["labels"]
    retest_label = "Synthetic build 1.1"
    retested = submit(
        client, stale_retest, retest_url, {"Build label": retest_label}, [first_case]
    )
    assert_redirect(retested, url)
    opened = page(client.get(url))
    shown = (
        '<p role="status">Retest requested for 1 test case on build '
        f'<span dir="auto">{retest_label}</span>.</p>'
    )
    assert opened.count(shown) == 1
    assert_in_order(opened, "</h1>", shown, "<p>State: Open</p>")
    assert current_build(opened, first_case) == retest_label
    assert current_build(opened, second_case) == build_label
    assert build_coverage(opened, build_label) == [first_case, second_case]
    assert build_coverage(opened, retest_label) == [first_case]
    assert_in_order(opened, "<h2>Builds</h2>", build_label, retest_label)
    assert criteria_content(opened) == published_criteria
    assert case_fields(opened, first_case) == published_cases[first_case]
    assert case_fields(opened, second_case) == published_cases[second_case]

    # RND-5.5: retest the same case again; both earlier builds stay listed.
    second_label = "Synthetic build 1.2"
    retesting = page(client.get(retest_url))
    retest_form = form(retesting, "Request retest")
    retested = submit(
        client, retest_form, retest_url, {"Build label": second_label}, [first_case]
    )
    assert_redirect(retested, url)
    opened = page(client.get(url))
    assert current_build(opened, first_case) == second_label
    assert current_build(opened, second_case) == build_label
    assert build_coverage(opened, build_label) == [first_case, second_case]
    assert build_coverage(opened, retest_label) == [first_case]
    assert build_coverage(opened, second_label) == [first_case]
    assert_in_order(opened, "<h2>Builds</h2>", build_label, retest_label, second_label)
    assert criteria_content(opened) == published_criteria
    assert case_fields(opened, first_case) == published_cases[first_case]
    assert case_fields(opened, second_case) == published_cases[second_case]

    # RND-6.1 and RND-6.2: the warning sits immediately before the close button;
    # closing keeps the round's content and removes every control.
    close = '<form method="post" action="' + f'{url}close/">'
    assert f"{WARNING}\n{close}" in opened
    stale_close = form(opened, "Close round")
    assert_redirect(submit(client, stale_close, url), url)
    closed = page(client.get(url))
    assert closed.count(CLOSED) == 1
    assert_in_order(closed, "</h1>", CLOSED, "<p>State: Closed</p>")
    assert criteria_content(closed) == published_criteria
    assert case_fields(closed, first_case) == published_cases[first_case]
    assert case_fields(closed, second_case) == published_cases[second_case]
    assert build_coverage(closed, second_label) == [first_case]
    for control in (*DRAFT_CONTROLS, WARNING, "Close round", "Request a retest"):
        assert control not in closed, control
    assert "<form" not in closed

    # RND-6.3: a Closed round refuses closing again and every other change
    # (retitling, publishing and record changes are part of RND-1.7, RND-2.8 and
    # RND-3.6, not marked here), and stays unchanged.
    assert_conflict(client.get(edit_url), "Closed", attempted)
    assert_conflict(client.get(retest_url), "Closed", attempted)
    for refused in (
        submit(client, stale_edit, edit_url, {"Title": attempted}),
        submit(client, stale_publish, url, {"Build label": attempted}),
        submit(client, stale_close, url),
        submit(
            client, stale_retest, retest_url, {"Build label": attempted}, [first_case]
        ),
        submit(client, stale_criterion_edit, criterion_url, {"Text": attempted}),
        submit(client, stale_case_edit, case_url, {"Title": attempted}),
        submit(client, stale_criterion_delete, url),
        submit(client, stale_case_delete, url),
    ):
        assert_conflict(refused, "Closed", attempted)
    unchanged = page(client.get(url))
    assert "<p>State: Closed</p>" in unchanged
    assert_titled(unchanged, revised_title, attempted)
    assert stable(unchanged) == stable(closed)
    assert current_build(unchanged, first_case) == second_label
    assert current_build(unchanged, second_case) == build_label
    assert build_coverage(unchanged, build_label) == [first_case, second_case]
    assert build_coverage(unchanged, retest_label) == [first_case]
    assert build_coverage(unchanged, second_label) == [first_case]
