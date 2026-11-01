"""The tester's read-only journey across publication, partial retest and closure."""

import pytest
from playwright.sync_api import expect


def assert_read_only(page):
    """The tester's detail offers navigation and no mutation controls."""
    expect(page.locator("main form, main input, main button")).to_have_count(0)
    expect(page.locator('main a[href^="/coordinator/"]')).to_have_count(0)
    expect(page.get_by_role("link", name="Tester home", exact=True)).to_be_visible()


def assert_steps(page, steps):
    """Each case preserves the visible step lines and their separating break."""
    for line in steps.splitlines():
        expect(page.get_by_text(line, exact=True)).to_have_count(2)
    paragraphs = page.locator("p").filter(
        has=page.get_by_text(steps.splitlines()[0], exact=True)
    )
    expect(paragraphs.locator("br")).to_have_count(2)


@pytest.mark.ac("RES-1.1", "RES-1.2", "RES-1.3", "RES-1.5", "RES-1.7", "RES-1.8")
def test_tester_reads_published_retested_and_closed_round(page, sign_in, live_server):
    # Red-team markup is escaped in source and decoded only inside this test.
    title = "Synthetic \x3cb\x3etester round\x3c/b\x3e \u05e9\u05dc\u05d5\u05dd"
    criterion = "Synthetic \x3cstrong\x3econfirmation\x3c/strong\x3e is visible."
    cases = ["Synthetic \x3cb\x3efirst case\x3c/b\x3e", "Synthetic second case"]
    steps = "Open the \x3cimg src=x onerror=alert(1)\x3e example.\nSelect Confirm."
    expected = "Synthetic \x3cem\x3econfirmation\x3c/em\x3e appears."
    original = "Synthetic build 1.0"
    retested = "Synthetic \x3cb\x3ebuild 2.0\x3c/b\x3e"
    dialogs = []

    def dismiss_dialog(dialog):
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", dismiss_dialog)
    sign_in(page, "tester")
    expect(page.get_by_role("heading", name="Tester home", exact=True)).to_be_visible()
    expect(page.get_by_text("No tests available.", exact=True)).to_be_visible()

    coordinator_context = page.context.browser.new_context(base_url=live_server.url)
    coordinator_context.set_default_timeout(5000)
    coordinator_context.set_default_navigation_timeout(10000)
    try:
        coordinator = coordinator_context.new_page()
        sign_in(coordinator, "coordinator")
        coordinator.get_by_role("link", name="New round", exact=True).click()
        coordinator.get_by_label("Title", exact=True).fill(title)
        coordinator.get_by_role("button", name="Create round", exact=True).click()
        round_url = coordinator.url
        coordinator.get_by_role(
            "link", name="Add acceptance criterion", exact=True
        ).click()
        coordinator.get_by_label("Text", exact=True).fill(criterion)
        coordinator.get_by_role(
            "button", name="Add acceptance criterion", exact=True
        ).click()
        for case in cases:
            coordinator.get_by_role("link", name="Add test case", exact=True).click()
            coordinator.get_by_label("Title", exact=True).fill(case)
            coordinator.get_by_label("Steps", exact=True).fill(steps)
            coordinator.get_by_label("Expected result", exact=True).fill(expected)
            coordinator.get_by_role("checkbox", name=criterion, exact=True).check()
            coordinator.get_by_role("button", name="Add test case", exact=True).click()
        page.reload()
        expect(page.get_by_text("No tests available.", exact=True)).to_be_visible()
        coordinator.get_by_label("Build label", exact=True).fill(original)
        coordinator.get_by_role("button", name="Publish round", exact=True).click()
        expect(coordinator.get_by_text("State: Open", exact=True)).to_be_visible()

        page.reload()
        available = page.get_by_role("link", name=title, exact=True)
        expect(available).to_be_visible()
        expect(page.get_by_role("listitem")).to_contain_text("(Open)")
        available.click()
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(page).to_have_title(f"\u2068{title}\u2069")
        expect(page.get_by_text("State: Open", exact=True)).to_be_visible()
        expect(page.locator("h3")).to_have_text(cases)
        assert_steps(page, steps)
        expect(page.get_by_text(expected, exact=True)).to_have_count(2)
        expect(page.get_by_text(criterion, exact=True)).to_have_count(2)
        expect(page.get_by_text(original, exact=True)).to_have_count(2)
        expect(
            page.locator("main img, main script, main b, main strong, main em")
        ).to_have_count(0)
        for span in page.locator("li > span").all():
            expect(span).to_have_attribute("dir", "auto")
            expect(span).to_have_css("unicode-bidi", "isolate")
        expect(page.locator("h1 span")).to_have_attribute("dir", "auto")
        expect(page.locator("h1 span")).to_have_css("unicode-bidi", "isolate")
        assert_read_only(page)

        coordinator.get_by_role("link", name="Request a retest", exact=True).click()
        coordinator.get_by_role("checkbox", name=cases[0], exact=True).check()
        expect(
            coordinator.get_by_role("checkbox", name=cases[1], exact=True)
        ).not_to_be_checked()
        coordinator.get_by_label("Build label", exact=True).fill(retested)
        coordinator.get_by_role("button", name="Request retest", exact=True).click()
        expect(coordinator).to_have_url(round_url)
        page.reload()
        expect(page.get_by_text(retested, exact=True)).to_have_count(1)
        expect(page.get_by_text(original, exact=True)).to_have_count(1)

        coordinator.get_by_role("button", name="Close round", exact=True).click()
        expect(coordinator.get_by_text("State: Closed", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        expect(page.get_by_text(retested, exact=True)).to_have_count(1)
        expect(page.get_by_text(original, exact=True)).to_have_count(1)
        expect(page.locator("h3")).to_have_text(cases)
        assert_steps(page, steps)
        assert_read_only(page)
        page.get_by_role("link", name="Tester home", exact=True).click()
        expect(page.get_by_role("listitem")).to_contain_text("(Closed)")
        page.get_by_role("link", name=title, exact=True).click()
        expect(page.get_by_text("State: Closed", exact=True)).to_be_visible()
        expect(page.locator("main img, main script, main b")).to_have_count(0)
        assert_read_only(page)
        assert dialogs == []
    finally:
        coordinator_context.close()
