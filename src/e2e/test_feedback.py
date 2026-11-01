"""Saved-observation feedback followed by explicit manual editing (RES-4)."""

import json
from unittest import mock

import pytest
from django.db import transaction
from playwright.sync_api import expect

from accounts.models import User
from ai.gateway import Failed, Success
from rounds import services
from rounds.models import Case, Criterion, Result, Round

ORIGINAL = "Synthetic failure after opening the page"
EDITED = "Synthetic failure in browser version 123 after opening the page"
QUESTION = "Which browser version did you use?"


@pytest.fixture
def browser_accounts(browser_accounts):
    """Prepare frozen context before Playwright; verify saved rows after it stops."""
    accounts = browser_accounts
    owner = User.objects.get(username=accounts["tester"])
    peer = User.objects.create_user(
        "tester2-feedback-browser",
        accounts["password"],
        workspace=owner.workspace,
        role="tester",
    )
    accounts["peer"] = peer.username
    round_ = Round.objects.create(
        workspace=owner.workspace, title="Synthetic feedback round"
    )
    criterion = Criterion.objects.create(round=round_, text="Synthetic page opens")
    case = Case.objects.create(
        round=round_,
        title="Synthetic opening case",
        steps="Open the page.",
        expected_result="The page opens.",
    )
    case.criteria.add(criterion)
    with transaction.atomic():
        build = services.publish(
            Round.objects.select_for_update().get(pk=round_.pk), "Synthetic original"
        )
    accounts["entry"] = (
        f"/tester/rounds/{round_.pk}/cases/{case.pk}/builds/{build.pk}/result/"
    )
    yield accounts
    if "expected" in accounts:
        assert Result.objects.count() == 1
        saved = Result.objects.get(tester=owner, case=case, build=build)
        assert (
            saved.outcome,
            saved.observation,
            saved.submitted_at is not None,
        ) == accounts["expected"]
        case.refresh_from_db()
        round_.refresh_from_db()
        assert round_.state == Round.State.OPEN
        assert (case.title, case.steps, case.expected_result) == (
            "Synthetic opening case",
            "Open the page.",
            "The page opens.",
        )
        assert list(case.criteria.values_list("text", flat=True)) == [criterion.text]
        assert round_.builds.count() == 1


def save_draft(page, sign_in, outcome, observation):
    """Save through result entry and follow the eligible feedback link."""
    sign_in(page, "tester")
    page.get_by_role("link", name="Synthetic feedback round", exact=True).click()
    page.get_by_role("link", name="Record result", exact=True).click()
    page.get_by_label("Outcome", exact=True).select_option(outcome)
    page.get_by_label("Observation", exact=True).fill(observation)
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()


@pytest.mark.ac("RES-4.1", "RES-4.2", "RES-4.4", "RES-4.5")
def test_feedback_preserves_saved_fields_until_manual_edit_and_is_private(
    page,
    browser_accounts,
    live_server,
    sign_in,
):
    accounts = browser_accounts
    save_draft(page, sign_in, "fail", ORIGINAL)
    page.get_by_label("Observation", exact=True).fill("Synthetic unsaved edit")
    reply = Success(json.dumps({"questions": [QUESTION]}))
    with mock.patch(
        "ai.feedback_views.gateway.complete", return_value=reply
    ) as complete:
        page.get_by_role("link", name="Observation feedback", exact=True).click()
        expect(
            page.get_by_role("heading", name="Observation feedback", exact=True)
        ).to_be_visible()
        complete.assert_not_called()
        expect(page.get_by_text(ORIGINAL, exact=True)).to_be_visible()
        expect(page.get_by_text("Synthetic unsaved edit", exact=True)).to_have_count(0)
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
        expect(
            page.get_by_role("heading", name="Questions to consider", exact=True)
        ).to_be_visible()
        expect(page.get_by_text(QUESTION, exact=True)).to_be_visible()
        expect(page.get_by_text(ORIGINAL, exact=True)).to_be_visible()
        complete.assert_called_once()
        assert json.loads(complete.call_args.args[2])["observation"] == ORIGINAL
        feedback_url = page.url
        # A GET discards transient questions without another request to the model.
        page.goto(feedback_url)
        expect(page.get_by_text(QUESTION, exact=True)).to_have_count(0)
        complete.assert_called_once()

    peer_context = page.context.browser.new_context(base_url=live_server.url)
    peer_context.set_default_timeout(5000)
    peer_context.set_default_navigation_timeout(10000)
    try:
        peer = peer_context.new_page()
        sign_in(peer, "peer")
        peer.goto(accounts["entry"])
        expect(peer.get_by_label("Observation", exact=True)).to_have_value("")
        expect(
            peer.get_by_role("link", name="Observation feedback", exact=True)
        ).to_have_count(0)
        denied = peer.goto(feedback_url)
        assert denied.status == 409
        expect(
            peer.get_by_role(
                "heading", name="Save a draft before requesting feedback.", exact=True
            )
        ).to_be_visible()
        expect(peer.get_by_text(ORIGINAL, exact=True)).to_have_count(0)
    finally:
        peer_context.close()

    page.get_by_role("link", name="Back to result", exact=True).click()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(ORIGINAL)
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
    page.get_by_label("Observation", exact=True).fill(EDITED)
    page.get_by_role("button", name="Save draft", exact=True).click()
    page.reload()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(EDITED)
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
    accounts["expected"] = ("fail", EDITED, False)


@pytest.mark.ac("RES-4.2", "RES-4.3", "RES-4.4")
def test_unavailable_feedback_keeps_manual_result_submission_usable(
    page, browser_accounts, sign_in
):
    accounts = browser_accounts
    save_draft(page, sign_in, "pass", "")
    page.get_by_role("link", name="Observation feedback", exact=True).click()
    expect(page.get_by_text("No observation.", exact=True)).to_be_visible()
    with mock.patch(
        "ai.feedback_views.gateway.complete", return_value=Failed("timeout")
    ) as complete:
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
        expect(
            page.get_by_text(
                "Feedback is unavailable right now. "
                "You can still edit your result yourself.",
                exact=True,
            )
        ).to_be_visible()
        complete.assert_called_once()
    expect(
        page.get_by_role("button", name="Suggest missing details", exact=True)
    ).to_be_visible()
    page.get_by_role("link", name="Back to result", exact=True).click()
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("pass")
    expect(page.get_by_label("Observation", exact=True)).to_have_value("")
    page.get_by_label("Outcome", exact=True).select_option("fail")
    page.get_by_label("Observation", exact=True).fill(EDITED)
    page.get_by_role("button", name="Submit", exact=True).click()
    expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
    expect(page.get_by_text(EDITED, exact=True)).to_be_visible()
    expect(
        page.get_by_role("link", name="Observation feedback", exact=True)
    ).to_have_count(0)
    accounts["expected"] = ("fail", EDITED, True)
