"""Browser round trip from an AI draft to a saved test case (RND-8.2)."""

import json
from unittest import mock

import pytest
from playwright.sync_api import expect

from accounts.models import Workspace
from ai.gateway import Success
from e2e.pending import assert_pending_submit
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
    if accounts.get("multiple"):
        saved = list(round_.cases.order_by("id"))
        assert len(saved) == len(accounts["multiple"])
        for case, expected in zip(saved, accounts["multiple"], strict=True):
            assert (case.title, case.steps, case.expected_result) == (
                expected["title"],
                expected["steps"],
                expected["expected_result"],
            )
            assert list(case.criteria.all()) == [
                criteria[int(label[1:]) - 1] for label in expected["criteria"]
            ]
    elif accounts.get("submitted") or accounts.get("reviewed"):
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


def open_review(page, index=0):
    """Open one isolated review page in the current authenticated context."""
    with page.context.expect_page(timeout=5000) as opened:
        page.get_by_role("button", name="Use this draft", exact=True).nth(index).click()
    review = opened.value
    expect(
        review.get_by_role("heading", name="New test case", exact=True)
    ).to_be_visible()
    assert review.context == page.context and review != page
    assert review.evaluate("window.opener === null")
    return review


@pytest.mark.ac("RND-8.2")
def test_two_suggestions_are_reviewed_and_saved_from_one_response(
    page, browser_accounts
):
    accounts = browser_accounts
    sign_in_coordinator(page, accounts)
    page.goto(accounts["round_url"])
    open_drafting(page, accounts)
    drafts = [DRAFT, {**DRAFT, "title": "Synthetic second draft", "criteria": ["C1"]}]
    monitor = page.context.new_page()
    with mock.patch(
        "ai.views.gateway.complete",
        return_value=Success(json.dumps({"drafts": drafts})),
    ) as gateway:
        page.get_by_role("button", name="Draft test cases", exact=True).click()
        expect(
            page.get_by_text(
                "Opens in a new tab. Keep this suggestions tab open "
                "to review another draft.",
                exact=True,
            )
        ).to_be_visible()
        cancelled = open_review(page)
        cancelled.get_by_label("Title", exact=True).fill("Synthetic cancelled edit")
        cancelled.close()
        monitor.goto(accounts["round_url"])
        expect(monitor.get_by_text("No test cases yet.", exact=True)).to_be_visible()
        expected = []
        for index, draft in enumerate(drafts):
            review = open_review(page, index)
            for label, field in (
                ("Title", "title"),
                ("Steps", "steps"),
                ("Expected result", "expected_result"),
            ):
                expect(review.get_by_label(label, exact=True)).to_have_value(
                    draft[field]
                )
            edited = {
                **draft,
                "title": f"Synthetic reviewed case {index}",
                "steps": f"Synthetic reviewed steps {index}",
                "expected_result": f"Synthetic reviewed result {index}",
            }
            for label, field in (
                ("Title", "title"),
                ("Steps", "steps"),
                ("Expected result", "expected_result"),
            ):
                review.get_by_label(label, exact=True).fill(edited[field])
            monitor.reload()
            expect(monitor.locator("details.record")).to_have_count(index)
            review.get_by_role("button", name="Add test case", exact=True).click()
            expect(
                review.get_by_role("heading", name=edited["title"], exact=True)
            ).to_be_visible()
            review.close()
            monitor.reload()
            expect(monitor.locator("details.record")).to_have_count(index + 1)
            for original in drafts:
                expect(
                    page.get_by_role("heading", name=original["title"], exact=True)
                ).to_be_visible()
            expect(
                page.get_by_role("button", name="Use this draft", exact=True)
            ).to_have_count(2)
            expected.append(edited)
            gateway.assert_called_once()
        accounts["multiple"] = expected
    monitor.close()


@pytest.mark.ac("PLT-4.12", "RND-8.1")
def test_drafting_pending_request_and_history_reset(page, browser_accounts):
    accounts = browser_accounts
    sign_in_coordinator(page, accounts)
    page.goto(accounts["round_url"] + "cases/draft/")
    for criterion in accounts["criteria"]:
        page.get_by_role("checkbox", name=criterion, exact=True).check()
    assert_pending_submit(
        page,
        "ai.views.gateway.complete",
        "Draft test cases",
        "Drafting test cases…",
        Success(json.dumps({"drafts": [DRAFT]})),
        "Suggested test cases",
    )


@pytest.mark.ac("PLT-4.12", "RND-8.3")
def test_drafting_invalid_selection_restores_enabled_form(page, browser_accounts):
    sign_in_coordinator(page, browser_accounts)
    page.goto(browser_accounts["round_url"] + "cases/draft/")
    with mock.patch("ai.views.gateway.complete") as complete:
        page.get_by_role("button", name="Draft test cases", exact=True).click()
        expect(
            page.get_by_text("Select 1 to 5 acceptance criteria.", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Draft test cases", exact=True)
        ).to_be_enabled()
        expect(page.get_by_role("status")).to_be_empty()
        complete.assert_not_called()


@pytest.mark.ac("PLT-4.12", "RND-8.1", "RND-8.2")
def test_drafting_without_javascript(page, browser_accounts, live_server):
    context = page.context.browser.new_context(
        base_url=live_server.url, java_script_enabled=False
    )
    try:
        plain = context.new_page()
        sign_in_coordinator(plain, browser_accounts)
        plain.goto(browser_accounts["round_url"] + "cases/draft/")
        for criterion in browser_accounts["criteria"]:
            plain.get_by_role("checkbox", name=criterion, exact=True).check()
        with mock.patch(
            "ai.views.gateway.complete",
            return_value=Success(json.dumps({"drafts": [DRAFT]})),
        ) as complete:
            plain.get_by_role("button", name="Draft test cases", exact=True).click()
            expect(
                plain.get_by_role("heading", name=DRAFT["title"], exact=True)
            ).to_be_visible()
            expect(
                plain.get_by_role("button", name="Draft test cases", exact=True)
            ).to_be_enabled()
            complete.assert_called_once()
            review = open_review(plain)
            review.get_by_role("button", name="Add test case", exact=True).click()
            expect(
                review.get_by_role("heading", name=DRAFT["title"], exact=True)
            ).to_be_visible()
            expect(
                plain.get_by_role("heading", name=DRAFT["title"], exact=True)
            ).to_be_visible()
            complete.assert_called_once()
            browser_accounts["submitted"] = True
    finally:
        context.close()


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
    page = open_review(page)
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
            page = open_review(page)
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
