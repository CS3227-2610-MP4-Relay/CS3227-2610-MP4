"""Chromium fixtures for synthetic journeys against Django's loopback live server."""

import warnings

import pytest
from django.test import override_settings
from playwright.sync_api import Error, sync_playwright

from accounts.models import User, Workspace


@pytest.fixture(scope="session")
def live_server(request, tmp_path_factory):
    """Give Django's test file handlers valid prefixes and empty temporary roots."""
    assets = str(tmp_path_factory.mktemp("browser-assets"))
    with override_settings(
        STATIC_URL="/static/",
        MEDIA_URL="/media/",
        STATIC_ROOT=assets,
        MEDIA_ROOT=assets,
    ):
        yield request.getfixturevalue("live_server")


@pytest.fixture
def browser_accounts(transactional_db):
    """Commit synthetic accounts before Playwright starts its event loop."""
    workspace = Workspace.objects.create(name="Demo workspace browser1")
    accounts = {"workspace": workspace.name, "password": "SyntheticBrowser16"}
    for role in ("coordinator", "tester"):
        user = User.objects.create_user(
            f"{role}-browser1",
            accounts["password"],
            workspace=workspace,
            role=role,
        )
        accounts[role] = user.username
    return accounts


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Make the test outcome available before the browser fixture tears down."""
    report = yield
    if report.when == "call":
        item.browser_test_failed = report.failed
    return report


def save_failure(page, context, directory):
    """Keep synthetic failure diagnostics without masking the original failure."""
    try:
        page.screenshot(path=directory / "browser-failure.png", timeout=5000)
    except Error:
        warnings.warn("Could not save browser failure screenshot.", stacklevel=2)
    try:
        context.tracing.stop(path=directory / "browser-trace.zip")
    except Error:
        warnings.warn("Could not save browser failure trace.", stacklevel=2)


@pytest.fixture
def page(browser_accounts, live_server, tmp_path, request):
    """Yield a fresh Chromium page; stop its loop before database teardown."""
    with (
        override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False),
        sync_playwright() as playwright,
    ):
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(base_url=live_server.url)
            try:
                context.set_default_timeout(5000)
                context.set_default_navigation_timeout(10000)
                context.tracing.start(screenshots=True, snapshots=True, sources=False)
                browser_page = context.new_page()
                yield browser_page
                if getattr(request.node, "browser_test_failed", False):
                    save_failure(browser_page, context, tmp_path)
                else:
                    context.tracing.stop()
            finally:
                context.close()
        finally:
            browser.close()
