"""Real-form result journeys, with private browser sessions and preserved rows."""

import re

import pytest
from playwright.sync_api import expect

from accounts.models import User
from rounds.models import Result


@pytest.fixture
def browser_accounts(browser_accounts):
    """Create another tester before Playwright, check rows after it has stopped."""
    accounts = browser_accounts
    owner = User.objects.get(username=accounts["tester"])
    other = User.objects.create_user(
        "tester2-browser1",
        accounts["password"],
        workspace=owner.workspace,
        role="tester",
    )
    accounts["tester2"] = other.username
    yield accounts
    # The page fixture depends on this fixture, so its event loop has stopped.
    expected = accounts.get("expected_results")
    if expected is not None:
        assert Result.objects.count() == len(expected)
        for fields in expected:
            assert Result.objects.filter(**fields).count() == 1


def sign_in(page, accounts, role):
    """Authenticate through the real form in this page's own browser context."""
    page.goto("/sign-in/")
    page.get_by_label("Username", exact=True).fill(accounts[role])
    page.get_by_label("Password", exact=True).fill(accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()


def context(page, live_server):
    """Create an isolated session with the existing harness's bounded waits."""
    separate = page.context.browser.new_context(base_url=live_server.url)
    separate.set_default_timeout(5000)
    separate.set_default_navigation_timeout(10000)
    return separate


def publish(coordinator, accounts):
    """Prepare two linked cases and publish them through coordinator forms."""
    sign_in(coordinator, accounts, "coordinator")
    coordinator.get_by_role("link", name="New round", exact=True).click()
    coordinator.get_by_label("Title", exact=True).fill("Synthetic result round")
    coordinator.get_by_role("button", name="Create round", exact=True).click()
    round_url = coordinator.url
    coordinator.get_by_role("link", name="Add acceptance criterion", exact=True).click()
    coordinator.get_by_label("Text", exact=True).fill("Synthetic criterion")
    coordinator.get_by_role(
        "button", name="Add acceptance criterion", exact=True
    ).click()
    for title in ("Synthetic selected case", "Synthetic unselected case"):
        coordinator.get_by_role("link", name="Add test case", exact=True).click()
        coordinator.get_by_label("Title", exact=True).fill(title)
        coordinator.get_by_label("Steps", exact=True).fill("Synthetic steps")
        coordinator.get_by_label("Expected result", exact=True).fill(
            "Synthetic expected"
        )
        coordinator.get_by_role(
            "checkbox", name="Synthetic criterion", exact=True
        ).check()
        coordinator.get_by_role("button", name="Add test case", exact=True).click()
    coordinator.get_by_label("Build label", exact=True).fill("Synthetic original")
    coordinator.get_by_role("button", name="Publish round", exact=True).click()
    expect(coordinator.get_by_text("State: Open", exact=True)).to_be_visible()
    return round_url


def open_round(page, accounts, role="tester"):
    """Follow the available round rather than constructing an entry URL."""
    sign_in(page, accounts, role)
    page.get_by_role("link", name="Synthetic result round", exact=True).click()
    expect(page.get_by_role("link", name="Record result", exact=True)).to_have_count(2)


@pytest.mark.ac("RES-1.5", "RES-2.1", "RES-2.2", "RES-2.3", "RES-2.5", "RES-2.8")
def test_private_draft_validation_reload_and_immutable_submission(
    browser_accounts, page, live_server
):
    coordinator_context = context(page, live_server)
    other_context = context(page, live_server)
    dialogs = []

    def dismiss(dialog):
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", dismiss)
    try:
        coordinator = coordinator_context.new_page()
        publish(coordinator, browser_accounts)
        open_round(page, browser_accounts)
        page.get_by_role("link", name="Record result", exact=True).first.click()
        entry_url = page.url
        expect(page).to_have_title("Record result")
        page.get_by_label("Outcome", exact=True).select_option("fail")
        for button in ("Save draft", "Submit"):
            page.get_by_role("button", name=button, exact=True).click()
            expect(
                page.get_by_text("Enter an observation for Fail.", exact=True)
            ).to_be_visible()
            expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")

        # Red-team markup remains escaped in source and is decoded only in tests.
        observation = (
            "Synthetic \x3cscript\x3ealert(1)\x3c/script\x3e\nSynthetic second line"
        )
        page.get_by_label("Observation", exact=True).fill(observation)
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label("Observation", exact=True)).to_have_value(observation)
        page.goto("/tester/")
        page.get_by_role("button", name="Sign out", exact=True).click()
        sign_in(page, browser_accounts, "tester")
        page.goto(entry_url)
        expect(page.get_by_label("Observation", exact=True)).to_have_value(observation)
        expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")

        other = other_context.new_page()
        open_round(other, browser_accounts, "tester2")
        other.get_by_role("link", name="Record result", exact=True).first.click()
        expect(other.get_by_label("Observation", exact=True)).to_have_value("")
        expect(other.get_by_label("Outcome", exact=True)).to_have_value("")
        expect(other.get_by_text("Status: Draft", exact=True)).to_have_count(0)
        other.get_by_label("Outcome", exact=True).select_option("pass")
        other.get_by_label("Observation", exact=True).fill(
            "Synthetic other private draft"
        )
        other.get_by_role("button", name="Save draft", exact=True).click()

        page.reload()
        expect(page.get_by_label("Observation", exact=True)).to_have_value(observation)
        page.get_by_role("button", name="Submit", exact=True).click()
        expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
        expect(page.get_by_text("Fail", exact=True)).to_be_visible()
        expect(page.locator("main form, main input, main button")).to_have_count(0)
        expect(page.locator("main script")).to_have_count(0)
        for line in observation.splitlines():
            text = page.get_by_text(line, exact=True)
            expect(text).to_be_visible()
            expect(text).to_have_attribute("dir", "auto")
            expect(text).to_have_css("unicode-bidi", "isolate")
        expect(page.locator("main p br")).to_have_count(1)
        page.reload()
        expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
        other.reload()
        expect(other.get_by_text("Status: Draft", exact=True)).to_be_visible()
        expect(other.get_by_label("Observation", exact=True)).to_have_value(
            "Synthetic other private draft"
        )
        assert dialogs == []
        browser_accounts["expected_results"] = [
            {
                "tester__username": browser_accounts["tester"],
                "outcome": "fail",
                "observation": observation,
                "submitted_at__isnull": False,
            },
            {
                "tester__username": browser_accounts["tester2"],
                "outcome": "pass",
                "observation": "Synthetic other private draft",
                "submitted_at__isnull": True,
            },
        ]
    finally:
        other_context.close()
        coordinator_context.close()


@pytest.mark.ac("RES-1.5", "RES-2.1", "RES-2.4", "RES-2.5")
def test_selected_retest_and_close_refuse_stale_forms_preserving_results(
    browser_accounts, page, live_server
):
    coordinator_context = context(page, live_server)
    try:
        coordinator = coordinator_context.new_page()
        round_url = publish(coordinator, browser_accounts)
        open_round(page, browser_accounts)
        detail_url = page.url
        entries = page.get_by_role("link", name="Record result", exact=True)
        original_url = entries.first.get_attribute("href")
        untouched_url = entries.nth(1).get_attribute("href")
        for location, observation in (
            (original_url, "Synthetic earlier draft"),
            (untouched_url, "Synthetic unchanged draft"),
        ):
            page.goto(location)
            page.get_by_label("Outcome", exact=True).select_option("pass")
            page.get_by_label("Observation", exact=True).fill(observation)
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()
        page.goto(original_url)
        page.get_by_label("Observation", exact=True).fill(
            "Synthetic refused stale edit"
        )

        coordinator.get_by_role("link", name="Request a retest", exact=True).click()
        coordinator.get_by_role(
            "checkbox", name="Synthetic selected case", exact=True
        ).check()
        coordinator.get_by_label("Build label", exact=True).fill("Synthetic next")
        coordinator.get_by_role("button", name="Request retest", exact=True).click()
        expect(coordinator).to_have_url(round_url)
        with page.expect_response(
            lambda response: (
                response.url.endswith(original_url)
                and response.request.method == "POST"
            )
        ) as refused:
            page.get_by_role("button", name="Submit", exact=True).click()
        assert refused.value.status == 409
        expect(
            page.get_by_role(
                "heading",
                name=(
                    "This build is no longer current. "
                    "Reload the round to record a result."
                ),
                exact=True,
            )
        ).to_be_visible()
        page.goto(untouched_url)
        expect(page.get_by_label("Observation", exact=True)).to_have_value(
            "Synthetic unchanged draft"
        )
        page.goto(detail_url)
        page.get_by_role("link", name="Record result", exact=True).first.click()
        expect(page.get_by_text("Synthetic next", exact=True)).to_be_visible()
        expect(page.get_by_label("Observation", exact=True)).to_have_value("")
        expect(page.get_by_label("Outcome", exact=True)).to_have_value("")
        page.get_by_label("Outcome", exact=True).select_option("pass")
        page.get_by_label("Observation", exact=True).fill("Synthetic current draft")
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()
        current_url = page.url
        page.get_by_label("Observation", exact=True).fill(
            "Synthetic refused closed edit"
        )
        coordinator.get_by_role("button", name="Close round", exact=True).click()
        expect(coordinator.get_by_text("State: Closed", exact=True)).to_be_visible()
        with page.expect_response(
            lambda response: (
                response.url == current_url and response.request.method == "POST"
            )
        ) as refused:
            page.get_by_role("button", name="Submit", exact=True).click()
        assert refused.value.status == 409
        expect(
            page.get_by_role(
                "heading",
                name="This action is not available while the round is Closed.",
                exact=True,
            )
        ).to_be_visible()
        page.goto(detail_url)
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        expect(
            page.get_by_role("link", name="Record result", exact=True)
        ).to_have_count(0)
        expect(page.locator("main form, main input, main button")).to_have_count(0)
        browser_accounts["expected_results"] = [
            {
                "case__title": "Synthetic selected case",
                "build__label": "Synthetic original",
                "observation": "Synthetic earlier draft",
                "submitted_at__isnull": True,
            },
            {
                "case__title": "Synthetic unselected case",
                "build__label": "Synthetic original",
                "observation": "Synthetic unchanged draft",
                "submitted_at__isnull": True,
            },
            {
                "case__title": "Synthetic selected case",
                "build__label": "Synthetic next",
                "observation": "Synthetic current draft",
                "submitted_at__isnull": True,
            },
        ]
    finally:
        coordinator_context.close()


@pytest.mark.ac("RES-3.1", "RES-3.2", "RES-3.3", "RES-3.4", "RES-3.5")
def test_private_history_preserves_drafts_submissions_after_retest_and_close(
    browser_accounts, page, live_server
):
    coordinator_context = context(page, live_server)
    other_context = context(page, live_server)
    try:
        coordinator = coordinator_context.new_page()
        publish(coordinator, browser_accounts)
        open_round(page, browser_accounts)
        page.get_by_role("link", name="My results", exact=True).click()
        expect(page).to_have_title("My results")
        expect(
            page.get_by_role("heading", name="My results", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("No results yet.", exact=True)).to_be_visible()
        page.get_by_role("link", name="Back to round", exact=True).click()

        for index, button, observation in (
            (0, "Save draft", "Synthetic original private draft"),
            (1, "Submit", "Synthetic original submission"),
        ):
            page.get_by_role("link", name="Record result", exact=True).nth(
                index
            ).click()
            page.get_by_label("Outcome", exact=True).select_option("pass")
            page.get_by_label("Observation", exact=True).fill(observation)
            page.get_by_role("button", name=button, exact=True).click()
            page.get_by_role("link", name="Back to round", exact=True).click()
        page.get_by_role("link", name="My results", exact=True).click()
        history_url = page.url

        def check_history(expected):
            """Assert each row's original context and status through visible text."""
            rows = page.locator("main section")
            expect(rows).to_have_count(len(expected))
            for index, (case, build, observation, status) in enumerate(expected):
                row = rows.nth(index)
                for text in (
                    case,
                    build,
                    observation,
                    f"Status: {status}",
                    "Synthetic criterion",
                    "Pass",
                ):
                    expect(row.get_by_text(text, exact=True)).to_be_visible()
                expect(
                    row.get_by_role("heading", name="Build", exact=True)
                ).to_be_visible()
                expect(
                    row.get_by_role(
                        "heading", name="Linked acceptance criteria", exact=True
                    )
                ).to_be_visible()
                if status == "Submitted":
                    expect(
                        row.get_by_text(
                            re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$")
                        )
                    ).to_be_visible()
                else:
                    expect(
                        row.get_by_role("heading", name="Submitted at", exact=True)
                    ).to_have_count(0)
            expect(page.locator("main form, main input, main button")).to_have_count(0)
            expect(
                page.get_by_role("link", name="Record result", exact=True)
            ).to_have_count(0)

        original_rows = [
            (
                "Synthetic selected case",
                "Synthetic original",
                "Synthetic original private draft",
                "Draft",
            ),
            (
                "Synthetic unselected case",
                "Synthetic original",
                "Synthetic original submission",
                "Submitted",
            ),
        ]
        check_history(original_rows)
        page.reload()
        check_history(original_rows)

        other = other_context.new_page()
        open_round(other, browser_accounts, "tester2")
        other.get_by_role("link", name="My results", exact=True).click()
        expect(other.get_by_text("No results yet.", exact=True)).to_be_visible()
        expect(other.locator("main section")).to_have_count(0)
        other.get_by_role("link", name="Back to round", exact=True).click()
        other.get_by_role("link", name="Record result", exact=True).first.click()
        other.get_by_label("Outcome", exact=True).select_option("pass")
        other.get_by_label("Observation", exact=True).fill(
            "Synthetic second tester secret"
        )
        other.get_by_role("button", name="Save draft", exact=True).click()
        other.get_by_role("link", name="Back to round", exact=True).click()
        other.get_by_role("link", name="My results", exact=True).click()
        expect(other.locator("main section")).to_have_count(1)
        expect(
            other.get_by_text("Synthetic second tester secret", exact=True)
        ).to_be_visible()

        coordinator.get_by_role("link", name="Request a retest", exact=True).click()
        coordinator.get_by_role(
            "checkbox", name="Synthetic selected case", exact=True
        ).check()
        coordinator.get_by_label("Build label", exact=True).fill("Synthetic next")
        coordinator.get_by_role("button", name="Request retest", exact=True).click()
        page.reload()
        check_history(original_rows)
        page.get_by_role("link", name="Back to round", exact=True).click()
        page.get_by_role("link", name="Record result", exact=True).first.click()
        page.get_by_label("Outcome", exact=True).select_option("pass")
        page.get_by_label("Observation", exact=True).fill("Synthetic next submission")
        page.get_by_role("button", name="Submit", exact=True).click()
        page.get_by_role("link", name="Back to round", exact=True).click()
        page.get_by_role("link", name="My results", exact=True).click()
        expected = [
            (
                "Synthetic selected case",
                "Synthetic next",
                "Synthetic next submission",
                "Submitted",
            )
        ] + original_rows
        check_history(expected)
        expect(
            page.get_by_text("Synthetic second tester secret", exact=True)
        ).to_have_count(0)

        coordinator.get_by_role("button", name="Close round", exact=True).click()
        expect(coordinator.get_by_text("State: Closed", exact=True)).to_be_visible()
        page.get_by_role("link", name="Back to round", exact=True).click()
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        page.get_by_role("link", name="My results", exact=True).click()
        expect(page).to_have_url(history_url)
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        check_history(expected)
        other.reload()
        expect(other.locator("main section")).to_have_count(1)
        expect(
            other.get_by_text("Synthetic second tester secret", exact=True)
        ).to_be_visible()
        for _, _, observation, _ in expected:
            expect(other.get_by_text(observation, exact=True)).to_have_count(0)
        browser_accounts["expected_results"] = [
            {
                "tester__username": browser_accounts["tester"],
                "case__title": case,
                "build__label": build,
                "observation": observation,
                "submitted_at__isnull": status == "Draft",
            }
            for case, build, observation, status in expected
        ] + [
            {
                "tester__username": browser_accounts["tester2"],
                "observation": "Synthetic second tester secret",
                "submitted_at__isnull": True,
            }
        ]
    finally:
        other_context.close()
        coordinator_context.close()
