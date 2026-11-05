"""Shared sign-in, browser sessions and synthetic accounts for browser journeys."""

from accounts.models import User
from rounds.models import Result

TIMEOUT = 5000
NAVIGATION_TIMEOUT = 10000


def bounded(context):
    """Apply the harness's bounded waits to a new browser context."""
    context.set_default_timeout(TIMEOUT)
    context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
    return context


def separate_context(page, live_server):
    """Create an isolated browser session with the harness's bounded waits."""
    return bounded(page.context.browser.new_context(base_url=live_server.url))


def sign_in(page, accounts, role):
    """Authenticate through the real sign-in form in this page's browser context."""
    page.goto("/sign-in/")
    page.get_by_label("Username", exact=True).fill(accounts[role])
    page.get_by_label("Password", exact=True).fill(accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()


def second_tester_accounts(accounts):
    """Add a second tester before Playwright; check rows after it has stopped.

    Yield from this in a module's ``browser_accounts`` override, which the page
    fixture depends on, so the row check runs after the browser event loop stops.
    """
    owner = User.objects.get(username=accounts["tester"])
    other = User.objects.create_user(
        "tester2-browser1",
        accounts["password"],
        workspace=owner.workspace,
        role="tester",
    )
    accounts["tester2"] = other.username
    yield accounts
    expected = accounts.get("expected_results")
    if expected is not None:
        assert Result.objects.count() == len(expected)
        for fields in expected:
            assert Result.objects.filter(**fields).count() == 1
