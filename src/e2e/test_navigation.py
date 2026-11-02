"""Native responsive contents and record disclosure journeys."""

from pathlib import Path
from tempfile import gettempdir

import pytest
from django.db import transaction
from django.utils import timezone
from playwright.sync_api import expect

from accounts.models import User
from e2e.test_presentation import assert_layout, contrast, sign_in
from rounds import services
from rounds.models import Case, Criterion, Result, Round


@pytest.fixture
def browser_accounts(browser_accounts):
    """Create multiple authorized records before starting Chromium."""
    accounts = browser_accounts
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
            observation=f"Synthetic observation {index}",
            submitted_at=timezone.now() if index == 0 else None,
        )
    accounts["round"] = round_.get_absolute_url()
    accounts["tester_round"] = f"/tester/rounds/{round_.pk}/"
    accounts["history"] = accounts["tester_round"] + "results/"
    accounts["results"] = accounts["round"] + "results/"
    empty = Round.objects.create(workspace=tester.workspace, title="Synthetic empty")
    accounts["empty"] = empty.get_absolute_url()
    return accounts


@pytest.mark.ac("PLT-4.4", "PLT-4.5", "PLT-4.6", "PLT-4.8", "PLT-4.9")
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
    records = page.locator("details.record")
    expect(records).to_have_count(2)
    assert records.evaluate_all("els => els.map(el => el.open)") == [True, False]
    summaries = records.locator("summary")
    expect(summaries.nth(1).get_by_role("heading")).to_contain_text("Synthetic case 1")
    expect(summaries.nth(1)).to_contain_text("Synthetic build")
    if kind == "history":
        expect(summaries.nth(1)).to_contain_text("Status: Draft")
        expect(summaries.nth(1)).to_contain_text("Pass")
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
