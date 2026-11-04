"""Saved-observation feedback followed by explicit manual editing (RES-4)."""

import json
from pathlib import Path
from tempfile import gettempdir
from unittest import mock

import pytest
from django.db import transaction
from playwright.sync_api import expect

from accounts.models import User
from ai.gateway import Failed, Success
from e2e.pending import assert_pending_submit
from e2e.presentation import assert_layout
from e2e.sessions import separate_context, sign_in
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


def save_draft(page, accounts, outcome, observation, *, save=True):
    """Fill result entry and optionally save before testing feedback navigation."""
    sign_in(page, accounts, "tester")
    page.get_by_role("link", name="Synthetic feedback round", exact=True).click()
    page.get_by_role("link", name="Record result", exact=True).click()
    page.get_by_label("Outcome", exact=True).select_option(outcome)
    page.get_by_label("Observation", exact=True).fill(observation)
    if save:
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()


@pytest.mark.ac("RES-4.9", "PLT-4.4")
@pytest.mark.parametrize("width", [320, 1440])
def test_feedback_before_first_draft_validates_then_saves_without_ai(
    page, browser_accounts, width
):
    page.set_viewport_size({"width": width, "height": 900})
    save_draft(page, browser_accounts, "fail", "", save=False)
    action = page.get_by_role("button", name="Observation feedback", exact=True)
    expect(action).to_be_visible()
    expect(
        page.get_by_text(
            "Observation feedback saves your draft and opens the AI feedback page. "
            "Choose an outcome first; Fail also needs an observation.",
            exact=True,
        )
    ).to_be_visible()
    assert_layout(page, width)
    page.screenshot(
        path=str(Path(gettempdir()) / f"relay-feedback-entry-{width}.png"),
        full_page=True,
    )
    with mock.patch("ai.feedback_views.gateway.complete") as complete:
        action.click()
        expect(
            page.get_by_text("Enter an observation for Fail.", exact=True)
        ).to_be_visible()
        expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
        page.get_by_label("Observation", exact=True).fill(ORIGINAL)
        action.click()
        expect(
            page.get_by_role("heading", name="Observation feedback", exact=True)
        ).to_be_visible()
        expect(page.get_by_text(ORIGINAL, exact=True)).to_be_visible()
        complete.assert_not_called()
    browser_accounts["expected"] = ("fail", ORIGINAL, False)


@pytest.mark.ac("PLT-4.12", "RES-4.2")
def test_feedback_pending_request_and_history_reset(page, browser_accounts):
    save_draft(page, browser_accounts, "fail", ORIGINAL)
    page.get_by_role("button", name="Observation feedback", exact=True).click()
    assert_pending_submit(
        page,
        "ai.feedback_views.gateway.complete",
        "Suggest missing details",
        "Suggesting missing details…",
        Success(json.dumps({"questions": [QUESTION]})),
        "Questions to consider",
    )
    browser_accounts["expected"] = ("fail", ORIGINAL, False)


@pytest.mark.ac("PLT-4.12", "RES-4.2", "RES-4.9")
def test_feedback_without_javascript(page, browser_accounts, live_server):
    context = page.context.browser.new_context(
        base_url=live_server.url, java_script_enabled=False
    )
    try:
        plain = context.new_page()
        save_draft(plain, browser_accounts, "fail", ORIGINAL, save=False)
        with mock.patch(
            "ai.feedback_views.gateway.complete",
            return_value=Success(json.dumps({"questions": [QUESTION]})),
        ) as complete:
            plain.get_by_role("button", name="Observation feedback", exact=True).click()
            expect(plain.get_by_text(ORIGINAL, exact=True)).to_be_visible()
            complete.assert_not_called()
            plain.get_by_role(
                "button", name="Suggest missing details", exact=True
            ).click()
            expect(plain.get_by_text(QUESTION, exact=True)).to_be_visible()
            expect(
                plain.get_by_role("button", name="Suggest missing details", exact=True)
            ).to_be_enabled()
            complete.assert_called_once()
        browser_accounts["expected"] = ("fail", ORIGINAL, False)
    finally:
        context.close()


@pytest.mark.ac("RES-4.1", "RES-4.2", "RES-4.4", "RES-4.5", "RES-4.9")
def test_feedback_preserves_saved_fields_until_manual_edit_and_is_private(
    page,
    browser_accounts,
    live_server,
):
    accounts = browser_accounts
    save_draft(page, accounts, "fail", ORIGINAL)
    current = "Synthetic current edit"
    page.get_by_label("Observation", exact=True).fill(current)
    reply = Success(json.dumps({"questions": [QUESTION]}))
    with mock.patch(
        "ai.feedback_views.gateway.complete", return_value=reply
    ) as complete:
        page.get_by_role("button", name="Observation feedback", exact=True).click()
        expect(
            page.get_by_role("heading", name="Observation feedback", exact=True)
        ).to_be_visible()
        complete.assert_not_called()
        expect(page.get_by_text(current, exact=True)).to_be_visible()
        expect(page.get_by_text(ORIGINAL, exact=True)).to_have_count(0)
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
        expect(
            page.get_by_role("heading", name="Questions to consider", exact=True)
        ).to_be_visible()
        expect(page.get_by_text(QUESTION, exact=True)).to_be_visible()
        expect(page.get_by_text(current, exact=True)).to_be_visible()
        complete.assert_called_once()
        assert json.loads(complete.call_args.args[2])["observation"] == current
        feedback_url = page.url
        # A GET discards transient questions without another request to the model.
        page.goto(feedback_url)
        expect(page.get_by_text(QUESTION, exact=True)).to_have_count(0)
        complete.assert_called_once()

    peer_context = separate_context(page, live_server)
    try:
        peer = peer_context.new_page()
        sign_in(peer, accounts, "peer")
        peer.goto(accounts["entry"])
        expect(peer.get_by_label("Observation", exact=True)).to_have_value("")
        expect(
            peer.get_by_role("button", name="Observation feedback", exact=True)
        ).to_be_visible()
        denied = peer.goto(feedback_url)
        assert denied.status == 409
        expect(
            peer.get_by_role(
                "heading", name="Save a draft before requesting feedback.", exact=True
            )
        ).to_be_visible()
        expect(peer.get_by_text(current, exact=True)).to_have_count(0)
    finally:
        peer_context.close()

    page.get_by_role("link", name="Back to result", exact=True).last.click()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(current)
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
    page.get_by_label("Observation", exact=True).fill(EDITED)
    page.get_by_role("button", name="Save draft", exact=True).click()
    page.reload()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(EDITED)
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
    accounts["expected"] = ("fail", EDITED, False)


@pytest.mark.ac("RES-4.2", "RES-4.3", "RES-4.4")
def test_unavailable_feedback_keeps_manual_result_submission_usable(
    page, browser_accounts
):
    accounts = browser_accounts
    save_draft(page, accounts, "pass", "")
    page.get_by_role("button", name="Observation feedback", exact=True).click()
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
    page.get_by_role("link", name="Back to result", exact=True).last.click()
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("pass")
    expect(page.get_by_label("Observation", exact=True)).to_have_value("")
    page.get_by_label("Outcome", exact=True).select_option("fail")
    page.get_by_label("Observation", exact=True).fill(EDITED)
    page.get_by_role("button", name="Submit", exact=True).click()
    expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
    expect(page.get_by_text(EDITED, exact=True)).to_be_visible()
    expect(
        page.get_by_role("button", name="Observation feedback", exact=True)
    ).to_have_count(0)
    accounts["expected"] = ("fail", EDITED, True)


@pytest.mark.ac("RES-4.2", "RES-4.3", "RES-4.4")
@pytest.mark.parametrize(
    ("questions", "message"),
    [
        (
            [],
            (
                "No missing details were suggested. "
                "You can still edit your result yourself."
            ),
        ),
        (
            [QUESTION, 7],
            (
                "Feedback is unavailable right now. "
                "You can still edit your result yourself."
            ),
        ),
    ],
    ids=["empty", "invalid-mixed-reply"],
)
def test_empty_or_invalid_feedback_keeps_saved_source_and_manual_editing(
    page, browser_accounts, questions, message
):
    accounts = browser_accounts
    save_draft(page, accounts, "fail", ORIGINAL)
    page.get_by_role("button", name="Observation feedback", exact=True).click()
    feedback_url = page.url
    with mock.patch(
        "ai.feedback_views.gateway.complete",
        return_value=Success(json.dumps({"questions": questions})),
    ) as complete:
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
        expect(page.get_by_text(message, exact=True)).to_be_visible()
        expect(page.get_by_text(QUESTION, exact=True)).to_have_count(0)
        expect(
            page.get_by_role("heading", name="Questions to consider", exact=True)
        ).to_have_count(0)
        expect(page.get_by_text(ORIGINAL, exact=True)).to_be_visible()
        expect(
            page.get_by_role("button", name="Suggest missing details", exact=True)
        ).to_be_visible()
        complete.assert_called_once()
        page.goto(feedback_url)
        expect(page.get_by_text(message, exact=True)).to_have_count(0)
        expect(page.get_by_text(QUESTION, exact=True)).to_have_count(0)
        complete.assert_called_once()
    page.get_by_role("link", name="Back to result", exact=True).last.click()
    expect(page.get_by_label("Outcome", exact=True)).to_have_value("fail")
    expect(page.get_by_label("Observation", exact=True)).to_have_value(ORIGINAL)
    page.get_by_label("Observation", exact=True).fill(EDITED)
    page.get_by_role("button", name="Save draft", exact=True).click()
    page.reload()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(EDITED)
    expect(page.get_by_text("Status: Draft", exact=True)).to_be_visible()
    accounts["expected"] = ("fail", EDITED, False)


@pytest.mark.ac("RES-2.1", "RES-2.5", "RES-4.5")
def test_stale_feedback_tab_after_submission_refuses_without_gateway_call(
    page, browser_accounts
):
    accounts = browser_accounts
    save_draft(page, accounts, "fail", ORIGINAL)
    page.get_by_role("button", name="Observation feedback", exact=True).click()
    feedback_url = page.url
    page.get_by_role("link", name="Back to result", exact=True).click()
    feedback = page.context.new_page()
    try:
        with mock.patch(
            "ai.feedback_views.gateway.complete",
            return_value=Success(json.dumps({"questions": [QUESTION]})),
        ) as complete:
            feedback.goto(feedback_url)
            expect(feedback.get_by_text(ORIGINAL, exact=True)).to_be_visible()
            page.get_by_role("button", name="Submit", exact=True).click()
            expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
            with feedback.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith(feedback_url)
                )
            ) as refused:
                feedback.get_by_role(
                    "button", name="Suggest missing details", exact=True
                ).click()
            assert refused.value.status == 409
            expect(
                feedback.get_by_role(
                    "heading",
                    name="This result has already been submitted.",
                    exact=True,
                )
            ).to_be_visible()
            expect(feedback.get_by_text(QUESTION, exact=True)).to_have_count(0)
            complete.assert_not_called()
        page.reload()
        expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
        expect(page.get_by_text(ORIGINAL, exact=True)).to_be_visible()
        expect(page.get_by_text("Fail", exact=True)).to_be_visible()
        expect(page.locator("main form")).to_have_count(0)
        expect(
            page.get_by_role("button", name="Observation feedback", exact=True)
        ).to_have_count(0)
        accounts["expected"] = ("fail", ORIGINAL, True)
    finally:
        feedback.close()
