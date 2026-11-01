"""Browser journeys through the coordinator's round preparation forms."""

import pytest
from playwright.sync_api import expect


def sign_in_coordinator(page, accounts):
    """Open the coordinator home through the real sign-in form."""
    page.goto("/sign-in/")
    page.get_by_label("Username", exact=True).fill(accounts["coordinator"])
    page.get_by_label("Password", exact=True).fill(accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()


def create_draft_round(page, title):
    """Submit a round title from the coordinator home."""
    page.get_by_role("link", name="New round", exact=True).click()
    page.get_by_label("Title", exact=True).fill(title)
    page.get_by_role("button", name="Create round", exact=True).click()


@pytest.mark.ac("RND-1.1", "RND-2.1", "RND-2.2", "RND-3.1")
def test_coordinator_prepares_and_publishes_linked_case(page, browser_accounts):
    title = "Synthetic browser round"
    criterion = "The synthetic confirmation is visible."
    case_title = "Check synthetic confirmation"
    steps = "Open the synthetic page and select Confirm."
    expected = "The synthetic confirmation appears."
    build = "Synthetic build 1.0"

    sign_in_coordinator(page, browser_accounts)
    create_draft_round(page, title)
    expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
    expect(page.get_by_text("State: Draft", exact=True)).to_be_visible()
    expect(page.get_by_text("No acceptance criteria yet.", exact=True)).to_be_visible()
    expect(page.get_by_text("No test cases yet.", exact=True)).to_be_visible()
    page.get_by_role("link", name="Coordinator home", exact=True).last.click()
    page.get_by_role("link", name=title, exact=True).click()

    page.get_by_role("link", name="Add acceptance criterion", exact=True).click()
    page.get_by_label("Text", exact=True).fill(criterion)
    page.get_by_role("button", name="Add acceptance criterion", exact=True).click()
    expect(page.get_by_text(criterion, exact=True)).to_be_visible()

    page.get_by_role("link", name="Add test case", exact=True).click()
    page.get_by_label("Title", exact=True).fill(case_title)
    page.get_by_label("Steps", exact=True).fill(steps)
    page.get_by_label("Expected result", exact=True).fill(expected)
    page.get_by_role("checkbox", name=criterion, exact=True).check()
    page.get_by_role("button", name="Add test case", exact=True).click()
    page.reload()
    expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=case_title, exact=True)).to_be_visible()
    expect(page.get_by_text(steps, exact=True)).to_be_visible()
    expect(page.get_by_text(expected, exact=True)).to_be_visible()
    # The criterion appears in its list and again in the case's saved links.
    expect(page.get_by_text(criterion, exact=True)).to_have_count(2)

    page.get_by_label("Build label", exact=True).fill(build)
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Round published.")
    page.reload()
    expect(page.get_by_text("State: Open", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=case_title, exact=True)).to_be_visible()
    expect(page.get_by_text(criterion, exact=True)).to_have_count(2)
    expect(page.get_by_text("Current build", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Builds", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=build, exact=True)).to_be_visible()
    # The label appears as the case's current build and in the build list.
    expect(page.get_by_text(build, exact=True)).to_have_count(2)
    for link in (
        "Edit round",
        "Add acceptance criterion",
        "Edit criterion",
        "Add test case",
        "Edit test case",
    ):
        expect(page.get_by_role("link", name=link, exact=True)).to_have_count(0)
    for button in ("Delete criterion", "Delete test case", "Publish round"):
        expect(page.get_by_role("button", name=button, exact=True)).to_have_count(0)


@pytest.mark.ac("RND-2.6")
def test_case_without_link_is_refused_without_saving(page, browser_accounts):
    sign_in_coordinator(page, browser_accounts)
    create_draft_round(page, "Synthetic unlinked case round")
    criterion = "The synthetic response appears."
    page.get_by_role("link", name="Add acceptance criterion", exact=True).click()
    page.get_by_label("Text", exact=True).fill(criterion)
    page.get_by_role("button", name="Add acceptance criterion", exact=True).click()
    page.get_by_role("link", name="Add test case", exact=True).click()
    values = {
        "Title": "Synthetic unlinked case",
        "Steps": "Select the synthetic confirmation.",
        "Expected result": "The synthetic response appears.",
    }
    for label, value in values.items():
        page.get_by_label(label, exact=True).fill(value)
    expect(page.get_by_role("checkbox", name=criterion, exact=True)).not_to_be_checked()
    page.get_by_role("button", name="Add test case", exact=True).click()
    expect(
        page.get_by_text("Link at least one acceptance criterion.", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name="New test case", exact=True)
    ).to_be_visible()
    for label, value in values.items():
        expect(page.get_by_label(label, exact=True)).to_have_value(value)
    expect(page.get_by_role("checkbox", name=criterion, exact=True)).not_to_be_checked()

    page.get_by_role("link", name="Back to round", exact=True).last.click()
    page.reload()
    expect(page.get_by_text("State: Draft", exact=True)).to_be_visible()
    expect(page.get_by_text(criterion, exact=True)).to_be_visible()
    expect(page.get_by_text("No test cases yet.", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name=values["Title"], exact=True)).to_have_count(
        0
    )
    expect(page.get_by_role("heading", name="Builds", exact=True)).to_have_count(0)


@pytest.mark.ac("RND-3.3")
def test_empty_round_publish_is_refused_without_creating_build(page, browser_accounts):
    sign_in_coordinator(page, browser_accounts)
    create_draft_round(page, "Synthetic empty publish round")
    round_url = page.url
    label = "Synthetic refused build 1.0"
    page.get_by_label("Build label", exact=True).fill(label)
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(
        page.get_by_text("Add at least one test case before publishing.", exact=True)
    ).to_be_visible()
    expect(page.get_by_label("Build label", exact=True)).to_have_value(label)
    expect(page.get_by_role("status")).to_have_count(0)

    page.goto(round_url)
    page.reload()
    expect(page.get_by_text("State: Draft", exact=True)).to_be_visible()
    expect(page.get_by_text("No test cases yet.", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Builds", exact=True)).to_have_count(0)
    expect(page.get_by_role("heading", name=label, exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Publish round", exact=True)).to_be_visible()


@pytest.mark.ac("RND-8.4")
def test_drafting_page_keeps_manual_workflow_when_unavailable(page, browser_accounts):
    """Test settings disable live calls; manual drafting remains available."""
    sign_in_coordinator(page, browser_accounts)
    create_draft_round(page, "Synthetic drafting browser round")
    criterion = "The synthetic drafting criterion is visible."
    page.get_by_role("link", name="Add acceptance criterion", exact=True).click()
    page.get_by_label("Text", exact=True).fill(criterion)
    page.get_by_role("button", name="Add acceptance criterion", exact=True).click()
    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    expect(
        page.get_by_text(
            "Select 1 to 5 acceptance criteria. The selected criteria are sent to "
            "the SoC AI service to suggest test cases. Suggestions are not saved; "
            "review each one before adding it.",
            exact=True,
        )
    ).to_be_visible()
    page.get_by_role("checkbox", name=criterion, exact=True).check()
    page.get_by_role("button", name="Draft test cases", exact=True).click()
    expect(
        page.get_by_text(
            "Drafting is unavailable right now. You can still add test cases yourself.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.get_by_role("checkbox", name=criterion, exact=True)).to_be_checked()
    page.get_by_role("link", name="Add test case", exact=True).click()
    expect(
        page.get_by_role("heading", name="New test case", exact=True)
    ).to_be_visible()
