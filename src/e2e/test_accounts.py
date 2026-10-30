"""Browser journeys through the existing role-based account forms."""

import re

import pytest
from playwright.sync_api import expect


def submit_sign_in(page, username, password):
    """Submit credentials through the visible sign-in form."""
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()


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
    submit_sign_in(page, username, browser_accounts["password"])
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


@pytest.mark.ac("ACC-1.2")
def test_wrong_password_keeps_visitor_signed_out(page, browser_accounts, live_server):
    page.goto("/sign-in/")
    submit_sign_in(page, browser_accounts["coordinator"], "IncorrectSynthetic16")
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.get_by_role("alert")).to_have_text("Username or password is incorrect.")
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_have_count(0)

    page.goto("/coordinator/")
    expect(page).to_have_url(f"{live_server.url}/sign-in/")
    expect(page.locator("body")).not_to_contain_text(browser_accounts["coordinator"])
    expect(page.locator("body")).not_to_contain_text(browser_accounts["workspace"])


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize(
    ("role", "home", "other_home", "heading"),
    [
        ("coordinator", "/coordinator/", "/tester/", "Coordinator home"),
        ("tester", "/tester/", "/coordinator/", "Tester home"),
    ],
)
def test_wrong_role_navigation_preserves_own_session(
    page, browser_accounts, live_server, role, home, other_home, heading
):
    page.goto("/sign-in/")
    submit_sign_in(page, browser_accounts[role], browser_accounts["password"])
    expect(page).to_have_url(f"{live_server.url}{home}")

    denied = page.goto(other_home)
    assert denied.status == 403
    expect(page).to_have_url(f"{live_server.url}{other_home}")
    expect(
        page.get_by_role(
            "heading", name="You do not have access to this page.", exact=True
        )
    ).to_be_visible()
    expect(page.locator("body")).not_to_contain_text(browser_accounts["workspace"])
    for account_role in ("coordinator", "tester"):
        expect(page.locator("body")).not_to_contain_text(browser_accounts[account_role])

    page.goto(home)
    expect(page).to_have_url(f"{live_server.url}{home}")
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    expect(
        page.get_by_text(f"Username: {browser_accounts[role]}", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text(f"Workspace: {browser_accounts['workspace']}", exact=True)
    ).to_be_visible()


@pytest.mark.ac("ACC-2.1", "ACC-1.1")
def test_demo_workspace_credentials_sign_in_to_coordinator_home(page, live_server):
    page.goto("/")
    page.get_by_role("button", name="Create a demo workspace", exact=True).click()
    expect(page).to_have_title("Your demo workspace")
    expect(
        page.get_by_role("heading", name="Your demo workspace", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("columnheader")).to_have_text(
        ["Role", "Username", "Password"]
    )
    rows = page.get_by_role("row").filter(has=page.get_by_role("cell"))
    expect(rows).to_have_count(3)
    for row, role in enumerate(("Test Coordinator", "Beta Tester", "Beta Tester")):
        expect(rows.nth(row).get_by_role("cell").first).to_have_text(role)
    expect(
        page.get_by_text(
            "Save these passwords now. They will not be shown again.", exact=True
        )
    ).to_be_visible()
    workspace = page.get_by_text(re.compile(r"^Workspace: .+$")).inner_text()
    cells = rows.first.get_by_role("cell")
    username, password = cells.nth(1).inner_text(), cells.nth(2).inner_text()

    # The visitor stays signed out: another tab is sent to sign in.
    other = page.context.new_page()
    other.goto("/coordinator/")
    expect(other).to_have_url(re.compile(rf"^{live_server.url}/sign-in/"))
    other.close()

    page.get_by_role("link", name="Sign in", exact=True).click()
    submit_sign_in(page, username, password)
    expect(page).to_have_url(f"{live_server.url}/coordinator/")
    expect(
        page.get_by_role("heading", name="Coordinator home", exact=True)
    ).to_be_visible()
    expect(page.get_by_text(workspace, exact=True)).to_be_visible()
    expect(page.get_by_text(f"Username: {username}", exact=True)).to_be_visible()
    # The sample round is observed only; RND-7 has its own tests.
    expect(page.get_by_role("listitem")).to_have_text(["Sample round (Draft)"])
