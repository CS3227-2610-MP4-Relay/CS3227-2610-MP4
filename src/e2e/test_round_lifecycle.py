"""Browser journey from a prepared Draft round through edits, retests and close.

Creating, adding and publishing are covered by `test_rounds.py`; this journey
starts from a Draft round created before Playwright and checks the stored
round after Playwright stops.
"""

import pytest
from playwright.sync_api import expect

from accounts.models import Workspace
from rounds.models import Case, Criterion, Round

TITLE, REVISED_TITLE = "Synthetic checkout round", "Synthetic checkout revised"
FIRST, SECOND = "Synthetic payment is accepted.", "Synthetic receipt is shown."
REVISED_FIRST = "Synthetic payment is accepted and recorded."
FIRST_CASE, SECOND_CASE = "Synthetic pay with a card", "Synthetic view the receipt"
EXPECTED, REVISED_EXPECTED = "Synthetic order completes.", "Synthetic order recorded."
BUILDS = ("Synthetic build 1.0", "Synthetic build 1.1", "Synthetic build 1.2")
IGNORED = "Synthetic ignored"
WARNING = "Closing makes this round read-only. It cannot be reopened."


@pytest.fixture
def browser_accounts(browser_accounts):
    """Create a Draft round before Playwright, check what it stored afterwards."""
    accounts = browser_accounts
    workspace = Workspace.objects.get(name=accounts["workspace"])
    round_ = Round.objects.create(workspace=workspace, title=TITLE)
    first, second = (
        Criterion.objects.create(round=round_, text=text) for text in (FIRST, SECOND)
    )
    for title, expected, linked in (
        (FIRST_CASE, EXPECTED, (first, second)),
        (SECOND_CASE, "Synthetic receipt is visible.", (second,)),
    ):
        case = Case.objects.create(
            round=round_,
            title=title,
            steps="Synthetic steps.",
            expected_result=expected,
        )
        case.criteria.add(*linked)
    original_criteria = list(round_.criteria.values())
    original_cases = list(round_.cases.values())
    original_links = [list(case.links.values()) for case in round_.cases.all()]
    yield accounts
    # The page fixture depends on this fixture, so its event loop has stopped.
    if accounts.get("recovered_retest"):
        round_.refresh_from_db()
        assert (round_.state, round_.title, round_.closed_at) == (
            Round.State.OPEN,
            TITLE,
            None,
        )
        assert list(round_.criteria.values()) == original_criteria
        assert list(round_.cases.values()) == original_cases
        assert [
            list(case.links.values()) for case in round_.cases.all()
        ] == original_links
        builds = list(round_.builds.all())
        assert [build.label for build in builds] == list(BUILDS[:2])
        assert [list(build.cases.values_list("pk", flat=True)) for build in builds] == [
            [case["id"] for case in original_cases],
            [original_cases[1]["id"]],
        ]
    if accounts.get("closed"):
        round_.refresh_from_db()
        assert (round_.state, round_.title) == (Round.State.CLOSED, REVISED_TITLE)
        assert [c.text for c in round_.criteria.all()] == [REVISED_FIRST, SECOND]
        cases = list(round_.cases.all())
        assert [(c.title, c.expected_result) for c in cases] == [
            (FIRST_CASE, REVISED_EXPECTED),
            (SECOND_CASE, "Synthetic receipt is visible."),
        ]
        assert [list(c.criteria.all()) for c in cases] == [[first, second], [second]]
        coverage = [
            (build.label, [case.title for case in build.cases.order_by("id")])
            for build in round_.builds.all()
        ]
        assert coverage == [
            (BUILDS[0], [FIRST_CASE, SECOND_CASE]),
            (BUILDS[1], [FIRST_CASE]),
            (BUILDS[2], [FIRST_CASE]),
        ]


def sign_in_coordinator(page, accounts):
    """Open the coordinator home through the real sign-in form."""
    page.goto("/sign-in/")
    page.get_by_label("Username", exact=True).fill(accounts["coordinator"])
    page.get_by_label("Password", exact=True).fill(accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()


def refused(tab, state, button=None):
    """A stale tab's `button` POST, if given, gets 409 and the conflict page."""
    if button is not None:
        with tab.expect_response(lambda r: r.request.method == "POST") as response:
            tab.get_by_role("button", name=button, exact=True).click()
        assert response.value.status == 409
    expect(
        tab.get_by_role(
            "heading",
            name=f"This action is not available while the round is {state}.",
            exact=True,
        )
    ).to_be_visible()


def stale_tab(page, heading, link=None):
    """Open the current page in another tab, optionally following one link."""
    tab = page.context.new_page()
    tab.goto(page.url)
    if link is not None:
        tab.get_by_role("link", name=link, exact=True).first.click()
    expect(tab.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    return tab


def save(page, label, value):
    """Replace one field of the open edit form and save it."""
    page.get_by_label(label, exact=True).fill(value)
    page.get_by_role("button", name="Save", exact=True).click()


def request_retest(page, label):
    """Retest only the first case on a new build through the retest form."""
    page.get_by_role("link", name="Request a retest", exact=True).click()
    expect(
        page.get_by_role("heading", name="Request a retest", exact=True)
    ).to_be_visible()
    cases = page.get_by_role("group", name="Test cases to retest")
    expect(cases.get_by_role("checkbox")).to_have_count(2)
    for title in (FIRST_CASE, SECOND_CASE):
        expect(cases.get_by_role("checkbox", name=title)).not_to_be_checked()
    cases.get_by_role("checkbox", name=FIRST_CASE, exact=True).check()
    page.get_by_label("Build label", exact=True).fill(label)
    page.get_by_role("button", name="Request retest", exact=True).click()
    expect(page.get_by_role("status")).to_have_text(
        f"Retest requested for 1 test case on build {label}."
    )
    page.reload()


def expect_builds(page, *current):
    """Builds up to the first case's are listed; each case's section shows its own."""
    for label in BUILDS[: BUILDS.index(current[0]) + 1]:
        expect(page.get_by_role("heading", name=label, exact=True)).to_be_visible()
    for title, label in zip((FIRST_CASE, SECOND_CASE), current, strict=True):
        case = page.get_by_role("heading", name=title, exact=True)
        own = (
            "xpath=following-sibling::span[contains(@class,'record-meta')]"
            "//span[@dir='auto']"
        )
        expect(case.locator(own)).to_have_text(label)


@pytest.mark.ac("RND-1.2", "RND-5.1", "RND-5.5", "RND-6.1", "RND-6.2", "RND-6.3")
def test_coordinator_edits_retests_twice_and_closes_round(page, browser_accounts):
    sign_in_coordinator(page, browser_accounts)
    page.get_by_role("link", name=TITLE, exact=True).click()
    round_url = page.url

    # RND-1.2: retitle the round; edit a criterion and a case (RND-2.3
    # editing observed, not marked).
    page.get_by_role("link", name="Edit round", exact=True).click()
    expect(page.get_by_label("Title", exact=True)).to_have_value(TITLE)
    edit_tab = stale_tab(page, "Edit round")
    save(page, "Title", REVISED_TITLE)
    expect(page.get_by_role("heading", name=REVISED_TITLE, exact=True)).to_be_visible()
    page.get_by_role("link", name="Edit criterion", exact=True).first.click()
    expect(page.get_by_label("Text", exact=True)).to_have_value(FIRST)
    save(page, "Text", REVISED_FIRST)
    page.get_by_role("link", name="Edit test case", exact=True).first.click()
    expect(page.get_by_label("Title", exact=True)).to_have_value(FIRST_CASE)
    save(page, "Expected result", REVISED_EXPECTED)
    expect(page.get_by_text(REVISED_EXPECTED, exact=True)).to_be_visible()
    # The revised criterion is listed and linked from the first case only.
    expect(page.get_by_text(REVISED_FIRST, exact=True)).to_have_count(2)
    expect(page.get_by_text(SECOND, exact=True)).to_have_count(3)
    expect(page.get_by_text(FIRST, exact=True)).to_have_count(0)
    page.get_by_role("link", name="Coordinator home", exact=True).last.click()
    expect(
        page.get_by_role("listitem").filter(
            has=page.get_by_role("link", name=REVISED_TITLE, exact=True)
        )
    ).to_have_text(f"{REVISED_TITLE} (Draft)")
    expect(page.get_by_role("link", name=TITLE, exact=True)).to_have_count(0)
    page.get_by_role("link", name=REVISED_TITLE, exact=True).click()

    # Publishing opens the round; a Draft tab's publish is then refused (part
    # of RND-3.6, not marked).
    draft_tab = stale_tab(page, REVISED_TITLE)
    page.get_by_label("Build label", exact=True).fill(BUILDS[0])
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Round published.")
    expect(page.get_by_text("State: Open", exact=True)).to_be_visible()
    draft_tab.get_by_label("Build label", exact=True).fill(IGNORED)
    refused(draft_tab, "Open", "Publish round")

    # RND-5.1 and RND-5.5: retest one case twice; the other keeps its build.
    request_retest(page, BUILDS[1])
    expect_builds(page, BUILDS[1], BUILDS[0])
    request_retest(page, BUILDS[2])
    expect_builds(page, BUILDS[2], BUILDS[0])

    # RND-6.1 and RND-6.2: closing keeps the content and removes every control.
    expect(page.get_by_text(WARNING, exact=True)).to_be_visible()
    open_tab = stale_tab(page, REVISED_TITLE)
    retest_tab = stale_tab(page, "Request a retest", "Request a retest")
    page.get_by_role("button", name="Close round", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Round closed.")
    page.reload()
    expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=REVISED_TITLE, exact=True)).to_be_visible()
    expect(page.get_by_text(REVISED_FIRST, exact=True)).to_have_count(2)
    for title in (FIRST_CASE, SECOND_CASE):
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
    expect_builds(page, BUILDS[2], BUILDS[0])
    expect(page.get_by_text(WARNING, exact=True)).to_have_count(0)
    expect(page.get_by_role("button")).to_have_count(0)
    for link in ("Edit round", "Request a retest", "Add test case"):
        expect(page.get_by_role("link", name=link, exact=True)).to_have_count(0)

    # RND-6.3: closing again is refused, as are retests and retitling (part of
    # RND-1.7, not marked), and the round stays Closed.
    refused(open_tab, "Closed", "Close round")
    retest_tab.get_by_role("checkbox", name=FIRST_CASE, exact=True).check()
    retest_tab.get_by_label("Build label", exact=True).fill(IGNORED)
    refused(retest_tab, "Closed", "Request retest")
    edit_tab.get_by_label("Title", exact=True).fill(IGNORED)
    refused(edit_tab, "Closed", "Save")
    assert page.goto(edit_tab.url).status == 409
    refused(page, "Closed")
    page.goto(round_url)
    expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=REVISED_TITLE, exact=True)).to_be_visible()
    expect(page.get_by_text(IGNORED)).to_have_count(0)
    browser_accounts["closed"] = True


@pytest.mark.ac("RND-5.1", "RND-5.2", "RND-5.3", "RND-5.5")
def test_coordinator_recovers_from_retest_refusals(page, browser_accounts):
    sign_in_coordinator(page, browser_accounts)
    page.get_by_role("link", name=TITLE, exact=True).click()
    page.get_by_label("Build label", exact=True).fill(BUILDS[0])
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Round published.")
    round_url = page.url
    page.reload()
    expect_builds(page, BUILDS[0], BUILDS[0])
    sections = page.locator("#acceptance-criteria, #test-cases, #builds")
    original_content = sections.all_text_contents()
    for label, selected, error in (
        (BUILDS[1], False, "Select at least one test case."),
        (BUILDS[0], True, "This build label is already used in this round."),
    ):
        page.get_by_role("link", name="Request a retest", exact=True).click()
        choices = page.get_by_role("group", name="Test cases to retest")
        expect(choices.get_by_role("checkbox")).to_have_count(2)
        expect(
            choices.get_by_role("checkbox", name=FIRST_CASE, exact=True)
        ).not_to_be_checked()
        second = choices.get_by_role("checkbox", name=SECOND_CASE, exact=True)
        expect(second).not_to_be_checked()
        if selected:
            second.check()
        page.get_by_label("Build label", exact=True).fill(label)
        with page.expect_response(
            lambda response: response.request.method == "POST"
        ) as refused:
            page.get_by_role("button", name="Request retest", exact=True).click()
        assert refused.value.status == 200
        expect(page.locator(".error")).to_have_text(error)
        expect(page.get_by_label("Build label", exact=True)).to_have_value(label)
        expect(second).to_be_checked(checked=selected)
        expect(
            choices.get_by_role("checkbox", name=FIRST_CASE, exact=True)
        ).not_to_be_checked()
        expect(page.get_by_role("status")).to_have_count(0)
        page.get_by_role("navigation", name="Page navigation").get_by_role(
            "link", name="Back to round", exact=True
        ).click()
        expect(page).to_have_url(round_url)
        page.reload()
        expect(page.get_by_text("State: Open", exact=True)).to_be_visible()
        expect(sections).to_have_text(original_content)
        expect_builds(page, BUILDS[0], BUILDS[0])
        expect(page.locator("#builds > h3")).to_have_text([BUILDS[0]])
    page.get_by_role("link", name="Request a retest", exact=True).click()
    page.get_by_role("checkbox", name=SECOND_CASE, exact=True).check()
    page.get_by_label("Build label", exact=True).fill(BUILDS[1])
    page.get_by_role("button", name="Request retest", exact=True).click()
    expect(page.get_by_role("status")).to_have_count(1)
    expect(page.get_by_role("status")).to_have_text(
        f"Retest requested for 1 test case on build {BUILDS[1]}."
    )
    page.reload()
    expect_builds(page, BUILDS[0], BUILDS[1])
    expect(page.locator("#builds > h3")).to_have_text(list(BUILDS[:2]))
    coverage = page.locator("#builds > ul")
    expect(coverage).to_have_count(2)
    expect(coverage.nth(0).locator("li")).to_have_text([FIRST_CASE, SECOND_CASE])
    expect(coverage.nth(1).locator("li")).to_have_text([SECOND_CASE])
    browser_accounts["recovered_retest"] = True
