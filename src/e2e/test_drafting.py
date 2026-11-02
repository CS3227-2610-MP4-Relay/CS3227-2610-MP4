"""Browser round trip from an AI draft to a saved test case (RND-8.2)."""

import json
from unittest import mock

import pytest
from playwright.sync_api import expect

from accounts.models import Workspace
from ai.gateway import Success
from e2e.test_rounds import sign_in_coordinator
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
    original_round = Round.objects.values().get(pk=round_.pk)
    original_criteria = list(round_.criteria.values())
    yield accounts
    # The page fixture depends on this fixture, so its event loop has stopped.
    assert Round.objects.values().get(pk=round_.pk) == original_round
    assert list(round_.criteria.values()) == original_criteria
    assert not round_.builds.exists()
    if accounts.get("submitted") or accounts.get("reviewed"):
        case = Case.objects.get()
        reviewed = accounts.get("reviewed", DRAFT)
        assert (case.title, case.steps, case.expected_result) == (
            reviewed["title"],
            reviewed["steps"],
            reviewed["expected_result"],
        )
        assert case.round_id == round_.pk
        assert list(case.criteria.all()) == [
            criteria[0 if accounts.get("reviewed") else 1]
        ]
    else:
        assert not round_.cases.exists()


def open_drafting(page, accounts):
    """Use round navigation and select both synthetic source criteria."""
    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    for text in accounts["criteria"]:
        page.get_by_role("checkbox", name=text, exact=True).check()


@pytest.mark.ac("RND-8.2")
def test_adopting_a_draft_and_submitting_unchanged_saves_it(page, browser_accounts):
    accounts = browser_accounts
    page.goto("/sign-in/")
    page.get_by_label("Username", exact=True).fill(accounts["coordinator"])
    page.get_by_label("Password", exact=True).fill(accounts["password"])
    page.get_by_role("button", name="Sign in", exact=True).click()
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


@pytest.mark.ac("RND-8.1", "RND-8.4", "RND-8.5")
@pytest.mark.parametrize("kind", ["empty", "invalid-mixed"])
def test_drafting_reply_without_usable_suggestions_keeps_manual_flow(
    page, browser_accounts, kind
):
    accounts = browser_accounts
    sign_in_coordinator(page, accounts)
    page.goto(accounts["round_url"])
    source = page.locator("#acceptance-criteria").text_content()
    open_drafting(page, accounts)
    drafts = [] if kind == "empty" else [DRAFT, {"title": "Synthetic invalid draft"}]
    message = (
        "No test cases were suggested for these criteria. "
        "You can still add test cases yourself."
        if kind == "empty"
        else "Drafting is unavailable right now. You can still add test cases yourself."
    )
    with mock.patch(
        "ai.views.gateway.complete",
        return_value=Success(json.dumps({"drafts": drafts})),
    ) as gateway:
        with page.expect_response(
            lambda response: response.request.method == "POST"
        ) as response:
            page.get_by_role("button", name="Draft test cases", exact=True).click()
        assert response.value.status == 200
        gateway.assert_called_once()
        expect(page.locator(".error")).to_have_text(message)
        for text in accounts["criteria"]:
            expect(page.get_by_role("checkbox", name=text, exact=True)).to_be_checked()
        expect(
            page.get_by_role("button", name="Use this draft", exact=True)
        ).to_have_count(0)
        expect(page.get_by_text(DRAFT["title"], exact=True)).to_have_count(0)
        expect(page.get_by_text(DRAFT["expected_result"], exact=True)).to_have_count(0)
        expect(page.get_by_text("Synthetic invalid draft", exact=True)).to_have_count(0)
        page.get_by_role("link", name="Add test case", exact=True).click()
        expect(
            page.get_by_role("heading", name="New test case", exact=True)
        ).to_be_visible()
        for label in ("Title", "Steps", "Expected result"):
            expect(page.get_by_label(label, exact=True)).to_have_value("")
        page.get_by_role("navigation", name="Page navigation").get_by_role(
            "link", name="Back to round", exact=True
        ).click()
        page.reload()
        expect(page.locator("#acceptance-criteria")).to_have_text(source)
        expect(page.get_by_text("No test cases yet.", exact=True)).to_be_visible()
        expect(page.get_by_text("State: Draft", exact=True)).to_be_visible()
        gateway.assert_called_once()


@pytest.mark.ac("RND-8.1", "RND-8.2")
def test_reviewed_draft_saves_only_after_explicit_add(page, browser_accounts):
    accounts = browser_accounts
    sign_in_coordinator(page, accounts)
    page.goto(accounts["round_url"])
    reviewed = {
        **DRAFT,
        "title": "Synthetic reviewed title",
        "expected_result": "The synthetic reviewed result is visible.",
    }
    with mock.patch(
        "ai.views.gateway.complete",
        return_value=Success(json.dumps({"drafts": [DRAFT]})),
    ) as gateway:
        for attempt in range(2):
            open_drafting(page, accounts)
            page.get_by_role("button", name="Draft test cases", exact=True).click()
            expect(
                page.get_by_role("heading", name=DRAFT["title"], exact=True)
            ).to_be_visible()
            page.get_by_role("button", name="Use this draft", exact=True).click()
            expect(
                page.get_by_text(
                    "Pre-filled from an AI draft. Review it before adding it.",
                    exact=True,
                )
            ).to_be_visible()
            for label, field in (
                ("Title", "title"),
                ("Steps", "steps"),
                ("Expected result", "expected_result"),
            ):
                expect(page.get_by_label(label, exact=True)).to_have_value(DRAFT[field])
            one, two = accounts["criteria"]
            expect(
                page.get_by_role("checkbox", name=one, exact=True)
            ).not_to_be_checked()
            expect(page.get_by_role("checkbox", name=two, exact=True)).to_be_checked()
            page.get_by_label("Title", exact=True).fill(reviewed["title"])
            page.get_by_label("Expected result", exact=True).fill(
                reviewed["expected_result"]
            )
            page.get_by_role("checkbox", name=one, exact=True).check()
            page.get_by_role("checkbox", name=two, exact=True).uncheck()
            if attempt == 0:
                page.get_by_role("navigation", name="Page navigation").get_by_role(
                    "link", name="Back to round", exact=True
                ).click()
                page.reload()
                expect(
                    page.get_by_text("No test cases yet.", exact=True)
                ).to_be_visible()
                expect(page.locator("details.record")).to_have_count(0)
            else:
                page.get_by_role("button", name="Add test case", exact=True).click()
                accounts["reviewed"] = reviewed
        assert gateway.call_count == 2
    page.reload()
    record = page.locator("details.record")
    expect(record).to_have_count(1)
    expect(
        record.get_by_role("heading", name=reviewed["title"], exact=True)
    ).to_be_visible()
    expect(
        record.locator(".record-body > p").first.locator("span[dir=auto]")
    ).to_have_text(reviewed["steps"].splitlines())
    expect(record.get_by_text(reviewed["expected_result"], exact=True)).to_be_visible()
    expect(record.locator(".record-body li")).to_have_text([one])
    expect(page.get_by_text(DRAFT["title"], exact=True)).to_have_count(0)
