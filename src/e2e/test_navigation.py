"""Native responsive contents and record disclosure journeys."""

from pathlib import Path
from tempfile import gettempdir

import pytest
from django.db import transaction
from django.utils import timezone
from playwright.sync_api import expect

from accounts.models import User
from e2e.presentation import assert_action_link_states, assert_layout, contrast
from e2e.sessions import sign_in
from rounds import services
from rounds.models import Case, Criterion, Result, Round


@pytest.fixture
def browser_accounts(browser_accounts, request):
    """Create multiple authorized records before starting Chromium."""
    accounts = browser_accounts
    history = (
        getattr(getattr(request.node, "callspec", None), "params", {}).get("kind")
        == "history"
    )
    tester = User.objects.get(username=accounts["tester"])
    round_ = Round.objects.create(
        workspace=tester.workspace, title="Synthetic navigation"
    )
    criterion = Criterion.objects.create(
        round=round_, text="Synthetic navigation criterion"
    )
    cases = []
    for index in range(2):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {index} " + "Long" * 20,
            steps="Synthetic steps " + "Long" * 70,
            expected_result=(
                "Synthetic \x3cb\x3eexpected\x3c/b\x3e \u05e9\u05dc\u05d5\u05dd"
            ),
        )
        case.criteria.add(criterion)
        cases.append(case)
    with transaction.atomic():
        build = services.publish(
            Round.objects.select_for_update().get(pk=round_.pk), "Synthetic build"
        )
    for index, case in enumerate(cases):
        Result.objects.create(
            tester=tester,
            case=case,
            build=build,
            outcome="pass",
            observation=("No observation." if index else "")
            if history
            else f"Synthetic observation {index}",
            submitted_at=timezone.now() if index == 0 else None,
        )
    accounts["round"] = round_.get_absolute_url()
    accounts["tester_round"] = f"/tester/rounds/{round_.pk}/"
    accounts["history"] = accounts["tester_round"] + "results/"
    accounts["results"] = accounts["round"] + "results/"
    empty = Round.objects.create(workspace=tester.workspace, title="Synthetic empty")
    accounts["empty"] = empty.get_absolute_url()
    return accounts


@pytest.mark.ac(
    "PLT-4.4",
    "PLT-4.5",
    "PLT-4.6",
    "PLT-4.7",
    "PLT-4.8",
    "PLT-4.9",
    "PLT-4.11",
    "PLT-4.13",
)
@pytest.mark.parametrize("width", [320, 1440])
@pytest.mark.parametrize("kind", ["round", "results", "tester_round", "history"])
def test_contents_reveal_records_and_keyboard_defaults(
    page, browser_accounts, width, kind
):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(
        page,
        browser_accounts,
        "tester" if kind.startswith(("tester", "history")) else "coordinator",
    )
    page.goto(browser_accounts[kind])
    navigation = page.get_by_role("navigation", name="Page navigation", exact=True)
    home = "Tester home" if kind in ("tester_round", "history") else "Coordinator home"
    for link in navigation.get_by_role("link").all():
        label = link.inner_text()
        expect(page.get_by_role("link", name=label, exact=True)).to_have_count(
            2 if label != home or kind in ("round", "tester_round") else 1
        )
        assert_action_link_states(page, link)
    final_label = home if kind in ("round", "tester_round") else "Back to round"
    final_return = page.locator("main a").last
    expect(final_return).to_have_text(final_label)
    assert_action_link_states(page, final_return)
    records = page.locator("details.record")
    expect(records).to_have_count(2)
    assert records.evaluate_all("els => els.map(el => el.open)") == [True, False]
    summaries = records.locator("summary")
    headers = (
        page.locator(".history-record > header") if kind == "history" else summaries
    )
    expect(headers.nth(1).get_by_role("heading")).to_contain_text("Synthetic case 1")
    expect(headers.nth(1)).to_contain_text("Synthetic build")
    if kind == "history":
        expect(headers.nth(1)).to_contain_text("Status: Draft")
        expect(headers.nth(1)).to_contain_text("Pass")
        expect(summaries.first).to_have_text("Hide details", use_inner_text=True)
        expect(summaries.nth(1)).to_have_text("Show details", use_inner_text=True)
        assert records.first.locator("summary + .record-body").count() == 1
        assert (
            summaries.first.bounding_box()["y"]
            >= headers.first.bounding_box()["y"]
            + headers.first.bounding_box()["height"]
        )
        body = records.first.locator(".record-body")
        assert abs(body.bounding_box()["x"] - summaries.first.bounding_box()["x"]) <= 2
        expect(page.locator("main form, main button")).to_have_count(0)
        assert (
            body.locator("em").evaluate("el => getComputedStyle(el).fontStyle")
            == "italic"
        )
        title = headers.first.get_by_role("heading")
        label = headers.first.get_by_text("Test case", exact=True)
        assert (
            label.bounding_box()["y"] + label.bounding_box()["height"]
            <= title.bounding_box()["y"]
        )
        title_size = title.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
        for subordinate in [
            label,
            *headers.first.locator(".record-meta").all(),
            *records.first.locator(".record-body h3").all(),
        ]:
            assert (
                subordinate.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
                < title_size
            )
    if kind == "results":
        expect(summaries.first).to_contain_text("Pass")
        expect(summaries.nth(1)).to_contain_text("No results for this build yet.")
        assert "Synthetic observation 1" not in "".join(
            page.locator(".record-body").all_text_contents()
        )
    if width < 1024:
        mobile = page.locator("details.mobile-contents")
        expect(mobile).not_to_have_attribute("open", "")
        mobile.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(mobile).to_have_attribute("open", "")
    contents = page.get_by_role("navigation", name="Contents", exact=True)
    expect(contents).to_be_visible()
    if kind in ("round", "tester_round"):
        parent = contents.get_by_role("link", name="Test cases", exact=True).locator(
            ".."
        )
        nested = parent.locator("ul")
        expect(nested.locator("li > a")).to_have_count(2)
        assert nested.evaluate("el => getComputedStyle(el).listStyleType") == "disc"
        assert (
            nested.locator("a").first.bounding_box()["x"]
            > parent.locator(":scope > a").bounding_box()["x"]
        )
    links = contents.locator('a[href^="#"]')
    targets = [link.get_attribute("href") for link in links.all()]
    assert len(targets) == len(set(targets))
    for target in targets:
        expect(page.locator(target)).to_have_count(1)
    selected = contents.get_by_role("link", name="Synthetic case 1", exact=False)
    fragment = selected.get_attribute("href")
    selected.click()
    expect(records.nth(1)).to_have_attribute("open", "")
    expect(page.locator(fragment)).to_be_in_viewport()
    page.get_by_role("navigation", name="Page navigation").get_by_role(
        "link"
    ).first.click()
    page.goto(browser_accounts[kind] + fragment)
    expect(records.nth(1)).to_have_attribute("open", "")
    expect(page.locator(fragment)).to_be_in_viewport()
    page.goto(browser_accounts[kind])
    summaries.nth(1).focus()
    page.keyboard.press("Enter")
    expect(records.nth(1)).to_have_attribute("open", "")
    expect(records.first).to_have_attribute("open", "")
    if kind == "history":
        expect(summaries.nth(1)).to_have_text("Hide details", use_inner_text=True)
        authored = records.nth(1).locator(".record-body p").first
        expect(authored).to_have_text("No observation.")
        assert authored.evaluate("el => getComputedStyle(el).fontStyle") == "normal"
    page.keyboard.press("Space")
    expect(records.nth(1)).not_to_have_attribute("open", "")
    page.keyboard.press("Space")
    expect(records.nth(1)).to_have_attribute("open", "")
    assert (
        summaries.nth(1).evaluate("el => getComputedStyle(el).outlineStyle") != "none"
    )
    outline = summaries.nth(1).evaluate("el => getComputedStyle(el).outlineColor")
    assert contrast([outline, "rgb(255, 255, 255)"]) >= 3
    page.reload()
    assert records.evaluate_all("els => els.map(el => el.open)") == [True, False]
    assert_layout(page, width)
    page.screenshot(
        path=str(Path(gettempdir()) / f"relay-117-{kind}-{width}.png"), full_page=True
    )
    if kind == "history":
        page.locator(".history-record").first.screenshot(
            path=str(Path(gettempdir()) / f"relay-history-card-{width}.png")
        )
    summaries.nth(1).click()
    assert_layout(page, width)
    expect(page.locator("main b, main script")).to_have_count(0)
    if kind != "history":
        expect(records.nth(1).locator("span[dir=auto]").first).to_be_visible()


@pytest.mark.ac("PLT-4.4", "PLT-4.8", "PLT-4.9")
def test_contents_breakpoint_and_empty_sections(page, browser_accounts):
    sign_in(page, browser_accounts, "coordinator")
    page.goto(browser_accounts["empty"])
    for width in (1023, 1024):
        page.set_viewport_size({"width": width, "height": 900})
        expect(
            page.locator(".desktop-contents")
        ).to_be_visible() if width == 1024 else expect(
            page.locator(".mobile-contents")
        ).to_be_visible()
        if width == 1023:
            page.locator(".mobile-contents > summary").click()
        navigation = page.get_by_role("navigation", name="Contents", exact=True)
        expect(navigation.get_by_role("link")).to_have_count(2)
        expect(page.get_by_text("No test cases yet.", exact=True)).to_be_visible()
        expect(page.locator("details.record")).to_have_count(0)
        assert_layout(page, width)
