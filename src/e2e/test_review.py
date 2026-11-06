"""RND-4: the coordinator reviews submitted results from the round page."""

import re

import pytest
from playwright.sync_api import expect

from e2e.disclosures import expand_records, result_links
from e2e.sessions import second_tester_accounts, separate_context, sign_in

ROUND = "Synthetic review round"
RETESTED, STEADY = "Synthetic retested case", "Synthetic steady case"
FIRST, SECOND = "Synthetic first build", "Synthetic second build"
FAILURE = "Synthetic first failure"
DRAFT = "Synthetic private draft"
PENDING = (
    "Saved drafts are still pending for current builds. "
    "Closing will prevent their submission."
)
SUBMITTED_AT = re.compile(r"^Submitted at: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$")


@pytest.fixture
def browser_accounts(browser_accounts):
    """Add a second tester before Playwright; check rows after it has stopped."""
    yield from second_tester_accounts(browser_accounts)


def publish(page, accounts):
    """Create a round with two linked cases and publish it on FIRST."""
    sign_in(page, accounts, "coordinator")
    page.get_by_role("link", name="New round", exact=True).click()
    page.get_by_label("Title", exact=True).fill(ROUND)
    page.get_by_role("button", name="Create round", exact=True).click()
    page.get_by_role("link", name="Add acceptance criterion", exact=True).click()
    page.get_by_label("Text", exact=True).fill("Synthetic review criterion")
    page.get_by_role("button", name="Add acceptance criterion", exact=True).click()
    for title in (RETESTED, STEADY):
        page.get_by_role("link", name="Add test case", exact=True).click()
        page.get_by_label("Title", exact=True).fill(title)
        page.get_by_label("Steps", exact=True).fill("Synthetic steps")
        page.get_by_label("Expected result", exact=True).fill("Synthetic expected")
        page.get_by_role(
            "checkbox", name="Synthetic review criterion", exact=True
        ).check()
        page.get_by_role("button", name="Add test case", exact=True).click()
    page.get_by_label("Build label", exact=True).fill(FIRST)
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(page.get_by_text("State: Open", exact=True)).to_be_visible()


def record(page, index, outcome, observation, button):
    """Record a result for the round's `index`th case through its real form."""
    result_links(page).nth(index).click()
    page.get_by_label("Outcome", exact=True).select_option(outcome)
    page.get_by_label("Observation", exact=True).fill(observation)
    page.get_by_role("button", name=button, exact=True).click()
    status = "Submitted" if button == "Submit" else "Draft"
    expect(page.get_by_text(f"Status: {status}", exact=True)).to_be_visible()
    page.get_by_role("link", name="Back to round", exact=True).last.click()


def record_as(page, accounts, role, *results):
    sign_in(page, accounts, role)
    page.get_by_role("link", name=ROUND, exact=True).click()
    for result in results:
        record(page, *result)


def open_results(page, state):
    """Follow the round page's link and check the results page's frame."""
    expect(page.get_by_text(f"State: {state}", exact=True)).to_be_visible()
    page.get_by_role("link", name="Review results", exact=True).click()
    expand_records(page)
    expect(page).to_have_title(f"Results: \u2068{ROUND}\u2069")
    expect(
        page.get_by_role("heading", name=f"Results: {ROUND}", exact=True)
    ).to_be_visible()
    expect(page.get_by_text(f"State: {state}", exact=True)).to_be_visible()
    expect(page.get_by_text(DRAFT)).to_have_count(0)
    expect(page.locator("main form, main input, main button")).to_have_count(0)


def under(page, label):
    """The result list directly after each heading named `label`."""
    return page.locator(f'main h3:text-is("{label}") + ul')


def expect_retested(page, accounts):
    """The retested case: no current results, the earlier result listed."""
    expect(
        page.get_by_text("No results for this build yet.", exact=True)
    ).to_be_visible()
    earlier = under(page, "Earlier builds")
    expect(earlier).to_have_count(1)
    for line in (
        f"Build: {FIRST}",
        f"Tester: {accounts['tester']}",
        "Outcome: Fail",
        f"Observation: {FAILURE}",
    ):
        expect(earlier.get_by_text(line, exact=True)).to_be_visible()
    current = under(page, "Results for this build")
    expect(current).to_have_count(1)
    expect(
        current.get_by_text("Observation: No observation.", exact=True)
    ).to_be_visible()
    expect(current.get_by_text(FAILURE)).to_have_count(0)
    expect(page.get_by_text(SUBMITTED_AT)).to_have_count(2)


@pytest.mark.ac("RND-4.1", "RND-4.2", "RND-4.3", "RND-4.4", "RND-6.6")
def test_coordinator_reviews_results_through_retest_and_close(
    page, browser_accounts, live_server
):
    tester = separate_context(page, live_server).new_page()
    other = separate_context(page, live_server).new_page()
    try:
        publish(page, browser_accounts)
        round_url = page.url
        expect(page.get_by_text(PENDING, exact=True)).to_have_count(0)
        record_as(
            tester,
            browser_accounts,
            "tester",
            (0, "fail", FAILURE, "Submit"),
            (1, "pass", "", "Submit"),
        )
        record_as(other, browser_accounts, "tester2", (0, "pass", DRAFT, "Save draft"))

        page.reload()
        expect(page.get_by_text(PENDING, exact=True)).to_be_visible()
        open_results(page, "Open")
        current = under(page, "Results for this build")
        expect(current).to_have_count(2)
        first = current.nth(0)
        for line in (
            f"Tester: {browser_accounts['tester']}",
            "Outcome: Fail",
            f"Observation: {FAILURE}",
        ):
            expect(first.get_by_text(line, exact=True)).to_be_visible()
        expect(
            current.nth(1).get_by_text("Observation: No observation.", exact=True)
        ).to_be_visible()
        expect(page.get_by_text(SUBMITTED_AT)).to_have_count(2)
        expect(
            page.get_by_text(f"Tester: {browser_accounts['tester2']}")
        ).to_have_count(0)
        expect(page.get_by_role("heading", name="Earlier builds")).to_have_count(0)
        expect(page.get_by_text("No results for this build yet.")).to_have_count(0)

        page.get_by_role("link", name="Back to round", exact=True).last.click()
        expect(page).to_have_url(round_url)
        page.get_by_role("link", name="Request a retest", exact=True).click()
        page.get_by_role("checkbox", name=RETESTED, exact=True).check()
        page.get_by_label("Build label", exact=True).fill(SECOND)
        page.get_by_role("button", name="Request retest", exact=True).click()
        expect(page.get_by_text(PENDING, exact=True)).to_have_count(0)
        open_results(page, "Open")
        expect(page.get_by_text(SECOND, exact=True)).to_be_visible()
        expect_retested(page, browser_accounts)

        page.get_by_role("link", name="Back to round", exact=True).last.click()
        page.get_by_role("button", name="Close round", exact=True).click()
        expect(page.get_by_text("Round closed.", exact=True)).to_be_visible()
        open_results(page, "Closed")
        expect_retested(page, browser_accounts)
        browser_accounts["expected_results"] = [
            {"observation": FAILURE, "submitted_at__isnull": False},
            {"observation": "", "submitted_at__isnull": False},
            {"observation": DRAFT, "submitted_at__isnull": True},
        ]
    finally:
        other.context.close()
        tester.context.close()


@pytest.mark.ac("RND-6.6", "RND-6.2")
def test_close_with_pending_draft_warns_without_exposing_or_blocking(
    page, browser_accounts, live_server
):
    tester = separate_context(page, live_server).new_page()
    try:
        publish(page, browser_accounts)
        record_as(tester, browser_accounts, "tester", (0, "pass", DRAFT, "Save draft"))
        page.reload()
        expect(page.get_by_text(PENDING, exact=True)).to_be_visible()
        expect(page.get_by_text(DRAFT, exact=True)).to_have_count(0)
        expect(page.locator("main")).not_to_contain_text(browser_accounts["tester"])
        expect(page.locator("p").filter(has_text=PENDING).locator("+ p")).to_have_text(
            "This reflects saved drafts at page load. "
            "Unsaved browser changes are unknown."
        )
        page.get_by_role("button", name="Close round", exact=True).click()
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        expect(page.get_by_text(PENDING, exact=True)).to_have_count(0)
        browser_accounts["expected_results"] = [
            {"observation": DRAFT, "submitted_at__isnull": True}
        ]
    finally:
        tester.context.close()
