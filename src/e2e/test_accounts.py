"""Browser journeys through the existing role-based account forms."""

import pytest
from playwright.sync_api import expect


@pytest.mark.ac("ACC-1.1", "ACC-1.3", "ACC-1.5")
@pytest.mark.parametrize(
    ("role", "home", "heading"),
    [
        ("coordinator", "/coordinator/", "Coordinator home"),
        ("tester", "/tester/", "Tester home"),
    ],
)
def test_role_sign_in_sign_out_and_protected_revisit(
    page, browser_accounts, live_server, role, home, heading
):
    page.goto(home)
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()

    username = browser_accounts[role]
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(browser_accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page).to_have_url(f"{live_server.url}{home}")
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    expect(page.get_by_text(f"Username: {username}", exact=True)).to_be_visible()
    expect(
        page.get_by_text(f"Workspace: {browser_accounts['workspace']}", exact=True)
    ).to_be_visible()
    old_session = next(
        cookie for cookie in page.context.cookies() if cookie["name"] == "sessionid"
    )

    page.get_by_role("button", name="Sign out", exact=True).click()
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.get_by_role("status")).to_have_text("You have signed out.")
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_have_count(0)
    expect(page.locator("body")).not_to_contain_text(username)
    expect(page.locator("body")).not_to_contain_text(browser_accounts["workspace"])

    page.goto(home)
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()

    page.context.add_cookies([old_session])
    page.goto(home)
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()
    expect(page.locator("body")).not_to_contain_text(username)
    expect(page.locator("body")).not_to_contain_text(browser_accounts["workspace"])
