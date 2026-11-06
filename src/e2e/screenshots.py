"""Regenerate the User Guide screenshots in ``docs/images/`` from the real app.

This drives one synthetic journey through Django's live server with the browser
harness: create a demo workspace, add a tester and show password management,
prepare and publish its sample round as the coordinator, record a Pass and a
Fail (with observation feedback) as its two initial testers, then review results,
request a retest and view **My results**. The AI
gateway is mocked, as in ``test_drafting.py`` and ``test_feedback.py``, so no
provider is called. The demo passwords shown are random and exist only in the
throwaway test database.

The file name does not match ``test_*.py``, so the normal ``pytest`` run skips
it. To refresh the images, with the test database available, run::

    pytest src/e2e/screenshots.py

then review every changed PNG before committing it.

To refresh only the account-management images, select::

    pytest src/e2e/screenshots.py::test_account_management_screenshots
"""

import json
from pathlib import Path
from unittest import mock

from playwright.sync_api import expect

from ai.gateway import Success
from e2e.sessions import separate_context, sign_in

IMAGES = Path(__file__).resolve().parents[2] / "docs" / "images"
VIEWPORT = {"width": 1280, "height": 800}
BUILD, RETEST_BUILD = "1.4.0-beta", "1.4.1-beta"

DRAFTS = [
    {
        "title": "Add a task with the Enter key",
        "steps": "1. Sign in to the example to-do app as user A.\n"
        '2. Enter "Buy milk" as a task title.\n'
        "3. Press Enter instead of choosing Add.",
        "expected_result": '"Buy milk" appears at the top of user A\'s task list.',
        "criteria": ["C1"],
    },
    {
        "title": "Shortest task title",
        "steps": "1. Sign in as user A.\n"
        "2. Enter a task title of exactly 1 character.\n"
        "3. Choose Add.",
        "expected_result": "The task is added at the top of the list with its "
        "1-character title.",
        "criteria": ["C1", "C2"],
    },
]
QUESTIONS = [
    "Which browser and version did you use?",
    "Did the task appear further down the list, or not at all?",
    "Was any message shown after you chose Add?",
]
FAILURE = "The task was added, but it appeared at the bottom of the list."


def shot(page, name, locator=None):
    """Save one full-page PNG, or just ``locator`` when it frames the step better."""
    path = IMAGES / f"{name}.png"
    if locator is None:
        page.screenshot(path=path, full_page=True)
    else:
        locator.screenshot(path=path)


def new_session(page, live_server, credentials):
    """Sign one demo account in from its own browser context at the fixed size."""
    context = separate_context(page, live_server)
    session = context.new_page()
    session.set_viewport_size(VIEWPORT)
    sign_in(session, credentials, "username")
    return session


def demo_workspace(page, *, capture=True):
    """Create a demo workspace from the start page and read its credentials."""
    page.goto("/")
    if capture:
        shot(page, "start-page")
    page.get_by_role("button", name="Create a demo workspace", exact=True).click()
    expect(
        page.get_by_role("heading", name="Your demo workspace", exact=True)
    ).to_be_visible()
    if capture:
        shot(page, "demo-workspace")
    rows = page.get_by_role("row").filter(has=page.get_by_role("cell"))
    expect(rows).to_have_count(3)
    accounts = []
    for index in range(3):
        cells = rows.nth(index).get_by_role("cell")
        accounts.append(
            {
                "username": cells.nth(1).inner_text(),
                "password": cells.nth(2).inner_text(),
            }
        )
    return accounts


def account_management(page):
    """Capture the coordinator's tester creation and password-management pages."""
    expect(
        page.get_by_role("heading", name="Coordinator home", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="Add Beta Tester", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("link", name="Beta Tester passwords", exact=True)
    ).to_be_visible()
    shot(page, "coordinator-home")
    page.get_by_role("button", name="Add Beta Tester", exact=True).click()
    expect(
        page.get_by_role("heading", name="Beta Tester added", exact=True)
    ).to_be_visible()
    shot(page, "beta-tester-added")
    page.get_by_role("link", name="Coordinator home", exact=True).click()
    page.get_by_role("link", name="Beta Tester passwords", exact=True).click()
    expect(
        page.get_by_role("heading", name="Beta Tester passwords", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("button", name="Reset password", exact=True)).to_have_count(
        3
    )
    shot(page, "beta-tester-passwords")
    page.get_by_role("link", name="Coordinator home", exact=True).click()


def prepare_and_publish(page):
    """As the coordinator, show the Draft round, its forms and AI drafting."""
    page.get_by_role("link", name="Sample round", exact=True).click()
    expect(page.get_by_text("State: Draft", exact=True)).to_be_visible()
    round_url = page.url
    shot(page, "draft-round")

    page.get_by_role("link", name="Add test case", exact=True).click()
    expect(
        page.get_by_role("heading", name="New test case", exact=True)
    ).to_be_visible()
    shot(page, "test-case-form")
    page.goto(round_url)

    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    criteria = page.get_by_role("checkbox")
    for index in range(2):
        criteria.nth(index).check()
    with mock.patch(
        "ai.views.gateway.complete",
        return_value=Success(json.dumps({"drafts": DRAFTS})),
    ):
        page.get_by_role("button", name="Draft test cases", exact=True).click()
        expect(
            page.get_by_role("heading", name=DRAFTS[0]["title"], exact=True)
        ).to_be_visible()
    shot(page, "ai-suggestions")
    page.goto(round_url)

    page.get_by_label("Build label", exact=True).fill(BUILD)
    page.get_by_role("button", name="Publish round", exact=True).click()
    expect(page.get_by_text("Round published.", exact=True)).to_be_visible()
    shot(page, "open-round")
    return round_url


def record_pass(session):
    """As the first tester, submit a Pass for the first case."""
    session.get_by_role("link", name="Sample round", exact=True).click()
    session.get_by_role("link", name="Record result", exact=True).first.click()
    session.get_by_label("Outcome", exact=True).select_option("pass")
    session.get_by_role("button", name="Submit", exact=True).click()
    expect(session.get_by_text("Status: Submitted", exact=True)).to_be_visible()


def record_fail_with_feedback(session):
    """As the second tester, save a Fail, ask for feedback, then submit."""
    expect(
        session.get_by_role("heading", name="Tester home", exact=True)
    ).to_be_visible()
    shot(session, "tester-home")
    session.get_by_role("link", name="Sample round", exact=True).click()
    expect(session.get_by_text("State: Open", exact=True)).to_be_visible()
    shot(session, "tester-round")
    session.get_by_role("link", name="Record result", exact=True).first.click()
    session.get_by_label("Outcome", exact=True).select_option("fail")
    session.get_by_label("Observation", exact=True).fill(FAILURE)
    session.get_by_role("button", name="Save draft", exact=True).click()
    expect(session.get_by_text("Status: Draft", exact=True)).to_be_visible()
    shot(session, "record-result")

    session.get_by_role("button", name="Observation feedback", exact=True).click()
    with mock.patch(
        "ai.feedback_views.gateway.complete",
        return_value=Success(json.dumps({"questions": QUESTIONS})),
    ):
        session.get_by_role(
            "button", name="Suggest missing details", exact=True
        ).click()
        expect(session.get_by_text(QUESTIONS[0], exact=True)).to_be_visible()
    shot(session, "observation-feedback")

    session.get_by_role("link", name="Back to result", exact=True).first.click()
    session.get_by_label("Observation", exact=True).fill(
        FAILURE + " Seen in Chromium 130; no message was shown."
    )
    session.get_by_role("button", name="Submit", exact=True).click()
    expect(session.get_by_text("Status: Submitted", exact=True)).to_be_visible()


def review_and_retest(page, round_url):
    """As the coordinator, review both results and request a retest."""
    page.goto(round_url)
    page.get_by_role("link", name="Review results", exact=True).click()
    expect(page.get_by_text("Outcome: Fail", exact=True)).to_be_visible()
    shot(page, "review-results")
    page.goto(round_url)
    page.get_by_role("link", name="Request a retest", exact=True).click()
    page.get_by_role("checkbox", name="Add a task", exact=True).check()
    label = page.get_by_label("Build label", exact=True)
    label.fill(RETEST_BUILD)
    label.blur()
    shot(page, "request-retest")
    page.get_by_role("button", name="Request retest", exact=True).click()
    expect(page.get_by_text("State: Open", exact=True)).to_be_visible()


def test_user_guide_screenshots(page, live_server):
    """Walk the coordinator and tester journey, saving each guide image."""
    IMAGES.mkdir(exist_ok=True)
    page.set_viewport_size(VIEWPORT)
    coordinator, first, second = demo_workspace(page)
    page.get_by_role("link", name="Sign in", exact=True).click()
    sign_in(page, coordinator, "username")
    account_management(page)
    round_url = prepare_and_publish(page)

    sessions = [new_session(page, live_server, tester) for tester in (first, second)]
    try:
        record_pass(sessions[0])
        record_fail_with_feedback(sessions[1])
        review_and_retest(page, round_url)
        tester = sessions[1]
        tester.goto("/tester/")
        tester.get_by_role("link", name="Sample round", exact=True).click()
        tester.get_by_role("link", name="My results", exact=True).click()
        expect(tester.get_by_text("Status: Submitted", exact=True)).to_be_visible()
        shot(tester, "my-results")
    finally:
        for session in sessions:
            session.context.close()


def test_account_management_screenshots(page):
    """Refresh only the guide images for adding testers and resetting passwords."""
    IMAGES.mkdir(exist_ok=True)
    page.set_viewport_size(VIEWPORT)
    coordinator, _, _ = demo_workspace(page, capture=False)
    sign_in(page, coordinator, "username")
    account_management(page)
