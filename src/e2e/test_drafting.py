"""Browser round trip from an AI draft to a saved test case (RND-8.2)."""

import json
from unittest import mock

import pytest
from playwright.sync_api import expect

from accounts.models import Workspace
from ai.gateway import Success
from rounds.models import Case, Criterion, Round

DRAFT = {
    "title": "Synthetic adopted title",
    "steps": "1. Open \x3cb\x3ethe\x3c/b\x3e app.\n2. Press \x22Save \x26 close\x22.",
    "expected_result": "The item is saved if 1 \x3c 2.",
    "criteria": ["C2"],
}


@pytest.fixture
def browser_accounts(browser_accounts):
    """Create a draft round before Playwright, check its case after it stops."""
    accounts = browser_accounts
    workspace = Workspace.objects.get(name=accounts["workspace"])
    round_ = Round.objects.create(workspace=workspace, title="Synthetic AI round")
    texts = ["Synthetic criterion one", "Synthetic criterion two"]
    criteria = [Criterion.objects.create(round=round_, text=text) for text in texts]
    accounts["round_url"] = round_.get_absolute_url()
    accounts["criteria"] = texts
    yield accounts
    # The page fixture depends on this fixture, so its event loop has stopped.
    if accounts.get("submitted"):
        case = Case.objects.get()
        assert (case.title, case.steps, case.expected_result) == (
            DRAFT["title"],
            DRAFT["steps"],
            DRAFT["expected_result"],
        )
        assert list(case.criteria.all()) == [criteria[1]]


@pytest.mark.ac("RND-8.2")
def test_adopting_a_draft_and_submitting_unchanged_saves_it(
    page, browser_accounts, sign_in
):
    accounts = browser_accounts
    sign_in(page, "coordinator")
    page.goto(accounts["round_url"])
    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    for text in accounts["criteria"]:
        page.get_by_role("checkbox", name=text, exact=True).check()
    reply = Success(json.dumps({"drafts": [DRAFT]}))
    # The live server runs in this process, so the patch reaches its view.
    with mock.patch("ai.views.gateway.complete", return_value=reply):
        page.get_by_role("button", name="Draft test cases", exact=True).click()
        expect(page.get_by_role("heading", name=DRAFT["title"])).to_be_visible()
    page.get_by_role("button", name="Use this draft", exact=True).click()
    expect(page.get_by_role("heading", name="New test case")).to_be_visible()
    expect(page.get_by_label("Title", exact=True)).to_have_value(DRAFT["title"])
    expect(page.get_by_label("Steps", exact=True)).to_have_value(DRAFT["steps"])
    expect(page.get_by_label("Expected result", exact=True)).to_have_value(
        DRAFT["expected_result"]
    )
    one, two = accounts["criteria"]
    expect(page.get_by_role("checkbox", name=one, exact=True)).not_to_be_checked()
    expect(page.get_by_role("checkbox", name=two, exact=True)).to_be_checked()
    page.get_by_role("button", name="Add test case", exact=True).click()
    expect(page.get_by_role("heading", name=DRAFT["title"], exact=True)).to_be_visible()
    accounts["submitted"] = True
