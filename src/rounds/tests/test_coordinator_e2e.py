"""RND-1 to 3, 5 to 7: one Test Coordinator journey through the real routes."""

import re

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

CREDENTIAL = re.compile(r"<tr><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td></tr>")
ROUND_LINK = re.compile(
    r'<li><a href="([^"]+)"><span dir="auto">([^<]+)</span></a> \(([^)]+)\)</li>'
)
SAVE = "Save these passwords now. They will not be shown again."
PUBLISHED = '<p role="status">Round published.</p>'
CLOSED = '<p role="status">Round closed.</p>'
WARNING = "Closing makes this round read-only. It cannot be reopened."


def page(response):
    """The response body as text."""
    return response.content.decode()


def credentials(response):
    """The demo page's role, username and password rows."""
    return CREDENTIAL.findall(page(response))


def workspace_name(html):
    """The workspace name shown on a demo page or role home."""
    return re.search(r"<p>Workspace: ([^<]*)</p>", html).group(1)


def home_rounds(response):
    """Each linked round on the Coordinator home with its state."""
    return ROUND_LINK.findall(page(response))


def assert_redirect(response, url):
    """A successful action redirects to exactly `url`."""
    assert response.status_code == 302
    assert response["Location"] == url


def assert_conflict(response, state):
    """A state refusal is the 409 page with its exact heading."""
    assert response.status_code == 409
    heading = f"<h1>This action is not available while the round is {state}.</h1>"
    assert heading in page(response)


def current_build(html, title):
    """The current-build label under a case title, or None."""
    heading = f'<h3><span dir="auto">{title}</span></h3>'
    start = html.index(heading) + len(heading)
    following = html.find("<h3>", start)
    section = html[start : following if following != -1 else len(html)]
    marker = section.find("<h4>Current build</h4>")
    if marker == -1:
        return None
    return re.search(r'<p><span dir="auto">([^<]+)</span></p>', section[marker:]).group(
        1
    )


def build_coverage(html, label):
    """The case titles listed under one build's coverage block."""
    heading = f'<h3><span dir="auto">{label}</span></h3>'
    start = html.index(heading)
    following = html.find("<h3>", start + len(heading))
    block = html[start : following if following != -1 else len(html)]
    return re.findall(r'<li><span dir="auto">([^<]+)</span></li>', block)


@pytest.mark.ac(
    "ACC-2.1",
    "ACC-2.2",
    "RND-1.1",
    "RND-1.2",
    "RND-1.7",
    "RND-2.1",
    "RND-2.2",
    "RND-2.3",
    "RND-2.8",
    "RND-3.1",
    "RND-3.4",
    "RND-3.6",
    "RND-5.1",
    "RND-5.5",
    "RND-5.8",
    "RND-6.1",
    "RND-6.2",
    "RND-6.3",
    "RND-6.5",
    "RND-7.1",
)
def test_a_coordinator_drives_a_round_from_demo_to_closed():
    client = Client()

    # ACC-2.1 and ACC-2.2: the start page creates a workspace whose displayed
    # coordinator credentials sign in and show that workspace's own home.
    start = client.get("/")
    assert '<form method="post" action="/demo/">' in page(start)
    assert "Create a demo workspace</button>" in page(start)
    created = client.post("/demo/")
    assert created.status_code == 200
    assert "no-store" in created["Cache-Control"]
    html = page(created)
    for text in (
        "<title>Your demo workspace</title>",
        "<h1>Your demo workspace</h1>",
        "<tr><th>Role</th><th>Username</th><th>Password</th></tr>",
        SAVE,
        '<a href="/sign-in/">Sign in</a>',
    ):
        assert text in html
    rows = credentials(created)
    assert [role for role, _, _ in rows] == [
        "Test Coordinator",
        "Beta Tester",
        "Beta Tester",
    ]
    _, username, password = rows[0]
    signed_in = client.post("/sign-in/", {"username": username, "password": password})
    assert_redirect(signed_in, "/coordinator/")
    home = client.get("/coordinator/")
    assert home.status_code == 200
    home_html = page(home)
    assert "<title>Coordinator home</title>" in home_html
    name = workspace_name(html)
    assert (
        f"<p>Workspace: {name}</p>" in home_html
        and f"<p>Username: {username}</p>" in home_html
    )

    # RND-7.1 is observed only as the sample round the new workspace supplies.
    rounds = home_rounds(home)
    assert len(rounds) == 1
    assert rounds[0][1:] == ("Sample round", "Draft")

    # RND-1.1: create a Draft round through the form and list it on the home.
    new = client.get("/coordinator/rounds/new/")
    assert "<h1>New round</h1>" in page(new)
    assert '<label for="id_title">Title</label>' in page(new)
    assert "Create round</button>" in page(new)
    title = "Synthetic checkout round"
    made = client.post("/coordinator/rounds/new/", {"title": title})
    assert made.status_code == 302
    url = made["Location"]
    draft_html = page(client.get(url))
    assert f'<h1><span dir="auto">{title}</span></h1>' in draft_html
    assert "<p>State: Draft</p>" in draft_html
    assert "Edit round</a>" in draft_html
    assert "No acceptance criteria yet." in draft_html
    assert "No test cases yet." in draft_html
    assert home_rounds(client.get("/coordinator/")) == [
        (url, title, "Draft"),
        rounds[0],
    ]

    # RND-2.1: add two criteria and see both in creation order.
    first = "Synthetic payment is accepted."
    second = "Synthetic receipt is shown."
    for text in (first, second):
        assert_redirect(client.post(f"{url}criteria/new/", {"text": text}), url)
    draft_html = page(client.get(url))
    assert draft_html.index("<h2>Acceptance criteria</h2>") < draft_html.index(first)
    assert draft_html.index(first) < draft_html.index(second)
    assert draft_html.index(second) < draft_html.index("<h2>Test cases</h2>")
    assert draft_html.count("Edit criterion</a>") == 2
    criterion_ids = re.findall(
        rf'action="{re.escape(url)}criteria/(\d+)/delete/"', draft_html
    )
    assert len(criterion_ids) == 2

    # RND-2.2: add two cases linked to the criteria; the first links to both.
    case_form = page(client.get(f"{url}cases/new/"))
    assert "<h1>New test case</h1>" in case_form
    assert "<legend>Linked acceptance criteria</legend>" in case_form
    assert case_form.index(first) < case_form.index(second)
    cases = (
        {
            "title": "Synthetic pay with a card",
            "steps": "Synthetic open the checkout and pay.",
            "expected_result": "Synthetic order completes.",
            "criteria": criterion_ids,
        },
        {
            "title": "Synthetic view the receipt",
            "steps": "Synthetic open the completed order.",
            "expected_result": "Synthetic receipt is visible.",
            "criteria": [criterion_ids[1]],
        },
    )
    for data in cases:
        assert_redirect(client.post(f"{url}cases/new/", data), url)
    draft_html = page(client.get(url))
    first_case, second_case = (data["title"] for data in cases)
    case_ids = re.findall(rf'action="{re.escape(url)}cases/(\d+)/delete/"', draft_html)
    assert len(case_ids) == 2
    for data in cases:
        assert f'<h3><span dir="auto">{data["title"]}</span></h3>' in draft_html
        assert data["steps"] in draft_html and data["expected_result"] in draft_html
    linked = draft_html[draft_html.index("<h2>Test cases</h2>") :]
    first_section = linked[
        : linked.index(f'<h3><span dir="auto">{second_case}</span></h3>')
    ]
    assert first in first_section and second in first_section
    second_section = linked[
        linked.index(f'<h3><span dir="auto">{second_case}</span></h3>') :
    ]
    assert second in second_section and first not in second_section

    # RND-1.2 and RND-2.3: retitle the round, then edit a criterion and a case.
    edit_page = page(client.get(f"{url}edit/"))
    assert f'value="{title}"' in edit_page
    revised_title = "Synthetic checkout round revised"
    assert_redirect(client.post(f"{url}edit/", {"title": revised_title}), url)
    criterion_url = f"{url}criteria/{criterion_ids[0]}/edit/"
    criterion_page = page(client.get(criterion_url))
    assert 'name="text"' in criterion_page and first in criterion_page
    revised_first = "Synthetic payment is accepted and recorded."
    assert_redirect(client.post(criterion_url, {"text": revised_first}), url)
    case_url = f"{url}cases/{case_ids[0]}/edit/"
    case_page = page(client.get(case_url))
    assert cases[0]["title"] in case_page and cases[0]["steps"] in case_page
    revised_expected = "Synthetic order completes and is recorded."
    edited = dict(cases[0], expected_result=revised_expected)
    assert_redirect(client.post(case_url, edited), url)
    draft_html = page(client.get(url))
    assert f'<h1><span dir="auto">{revised_title}</span></h1>' in draft_html
    assert revised_first in draft_html and revised_expected in draft_html
    assert first not in draft_html and cases[0]["expected_result"] not in draft_html
    assert second in draft_html and second_case in draft_html
    assert (url, revised_title, "Draft") in home_rounds(client.get("/coordinator/"))

    # RND-3.1 and RND-3.4: publishing opens every case on the first build.
    assert '<label for="id_label">Build label</label>' in draft_html
    assert "Publish round</button>" in draft_html
    build_label = "Synthetic build 1.0"
    assert_redirect(client.post(f"{url}publish/", {"label": build_label}), url)
    opened = page(client.get(url))
    assert opened.count(PUBLISHED) == 1
    assert (
        opened.index("</h1>")
        < opened.index(PUBLISHED)
        < opened.index("<p>State: Open</p>")
    )
    assert "<p>State: Open</p>" in opened
    for control in (
        "Edit round</a>",
        "Add acceptance criterion",
        "Add test case",
        "Edit criterion",
        "Delete criterion",
        "Edit test case",
        "Delete test case",
        "Publish round",
        "Build label",
    ):
        assert control not in opened, control
    assert current_build(opened, first_case) == build_label
    assert current_build(opened, second_case) == build_label
    assert build_coverage(opened, build_label) == [first_case, second_case]
    assert "Request a retest</a>" in opened
    assert WARNING in opened and "Close round</button>" in opened

    # RND-3.6, RND-1.7 and RND-2.8: an Open round refuses edits and publishing.
    assert_conflict(client.get(f"{url}edit/"), "Open")
    assert_conflict(client.post(f"{url}edit/", {"title": "Synthetic ignored"}), "Open")
    assert_conflict(
        client.post(f"{url}publish/", {"label": "Synthetic ignored"}), "Open"
    )

    # RND-5.1 and RND-5.5: retest one case; the other keeps its current build.
    retest = client.get(f"{url}retest/")
    assert retest.status_code == 200
    retest_html = page(retest)
    assert "<title>Request a retest</title>" in retest_html
    assert "<h1>Request a retest</h1>" in retest_html
    assert "<legend>Test cases to retest</legend>" in retest_html
    assert retest_html.count('type="checkbox"') == 2 and "checked" not in retest_html
    assert "Request retest</button>" in retest_html
    retest_label = "Synthetic build 1.1"
    assert_redirect(
        client.post(f"{url}retest/", {"cases": [case_ids[0]], "label": retest_label}),
        url,
    )
    opened = page(client.get(url))
    retest_message = (
        "Retest requested for 1 test case on build "
        f'<span dir="auto">{retest_label}</span>.'
    )
    shown = f'<p role="status">{retest_message}</p>'
    assert opened.count(shown) == 1
    assert (
        opened.index("</h1>") < opened.index(shown) < opened.index("<p>State: Open</p>")
    )
    assert current_build(opened, first_case) == retest_label
    assert current_build(opened, second_case) == build_label
    assert build_coverage(opened, build_label) == [first_case, second_case]
    assert build_coverage(opened, retest_label) == [first_case]
    builds = opened[opened.index("<h2>Builds</h2>") :]
    assert builds.index(build_label) < builds.index(retest_label)
    assert revised_first in opened and first not in opened

    # RND-6.1 and RND-6.2: closing keeps the round's content and removes controls.
    assert_redirect(client.post(f"{url}close/"), url)
    closed = page(client.get(url))
    assert closed.count(CLOSED) == 1
    assert (
        closed.index("</h1>")
        < closed.index(CLOSED)
        < closed.index("<p>State: Closed</p>")
    )
    assert "<p>State: Closed</p>" in closed
    assert revised_first in closed and second in closed
    assert first_case in closed and second_case in closed
    assert build_label in closed and retest_label in closed
    for control in (
        "Edit round</a>",
        "Add acceptance criterion",
        "Add test case",
        "Edit criterion",
        "Delete criterion",
        "Edit test case",
        "Delete test case",
        "Publish round",
        "Build label",
        WARNING,
        "Close round</button>",
        "Request a retest</a>",
        "<form",
    ):
        assert control not in closed, control

    # RND-6.3, RND-6.5, RND-2.8, RND-3.6 and RND-5.8: a Closed round is read-only.
    closed_actions = (
        ("get", f"{url}edit/", {}),
        ("post", f"{url}edit/", {"title": "Synthetic ignored"}),
        ("post", f"{url}publish/", {"label": "Synthetic ignored"}),
        ("get", f"{url}retest/", {}),
        (
            "post",
            f"{url}retest/",
            {"cases": [case_ids[0]], "label": "Synthetic ignored"},
        ),
        (
            "post",
            f"{url}criteria/{criterion_ids[0]}/edit/",
            {"text": "Synthetic ignored"},
        ),
        ("post", f"{url}cases/{case_ids[0]}/edit/", {"title": "Synthetic ignored"}),
        ("post", f"{url}criteria/{criterion_ids[1]}/delete/", {}),
        ("post", f"{url}cases/{case_ids[1]}/delete/", {}),
    )
    for method, target, data in closed_actions:
        assert_conflict(getattr(client, method)(target, data), "Closed")
    unchanged = page(client.get(url))
    assert "<p>State: Closed</p>" in unchanged
    assert revised_first in unchanged and second in unchanged
    assert current_build(unchanged, first_case) == retest_label
    assert current_build(unchanged, second_case) == build_label
