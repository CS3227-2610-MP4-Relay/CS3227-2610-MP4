"""Shared presentation at phone and desktop widths, using real existing pages."""

import json
from unittest import mock

import pytest
from django.db import transaction
from playwright.sync_api import expect

from accounts.models import User
from ai.gateway import Failed, Success
from e2e.presentation import (
    assert_action_link_states,
    assert_contrast,
    assert_layout,
    contrast,
)
from e2e.sessions import sign_in
from rounds import services
from rounds.models import Case, Criterion, Result, Round

LONG = "Synthetic" * 50
MARKUP = "\x3cb\x3eSynthetic text\x3c/b\x3e"


@pytest.fixture
def browser_accounts(browser_accounts):
    """Prepare long authored content before the synchronous browser starts."""
    accounts = browser_accounts
    tester = User.objects.get(username=accounts["tester"])
    draft = Round.objects.create(workspace=tester.workspace, title="Long" * 30)
    draft_criterion = Criterion.objects.create(round=draft, text=LONG)
    draft_case = Case.objects.create(
        round=draft, title="Synthetic draft case", steps=LONG, expected_result=MARKUP
    )
    draft_case.criteria.add(draft_criterion)
    accounts["draft"] = draft.get_absolute_url()
    open_round = Round.objects.create(
        workspace=tester.workspace, title="Synthetic presentation round"
    )
    criterion = Criterion.objects.create(round=open_round, text=LONG)
    case = Case.objects.create(
        round=open_round, title="Case" * 30, steps=LONG, expected_result=MARKUP
    )
    case.criteria.add(criterion)
    with transaction.atomic():
        build = services.publish(
            Round.objects.select_for_update().get(pk=open_round.pk), "Build" * 20
        )
    Result.objects.create(
        tester=tester, case=case, build=build, outcome="fail", observation=LONG
    )
    accounts["entry"] = (
        f"/tester/rounds/{open_round.pk}/cases/{case.pk}/builds/{build.pk}/result/"
    )
    accounts["open"] = open_round.get_absolute_url()
    accounts["history"] = f"/tester/rounds/{open_round.pk}/results/"
    return accounts


def assert_keyboard_focus(page, count):
    """Tab through native controls and check the visible focus treatment."""
    for _ in range(count):
        page.keyboard.press("Tab")
        focus = page.locator(":focus")
        expect(focus).to_be_visible()
        style = focus.evaluate("""el => {
          const s = getComputedStyle(el);
          return [s.outlineStyle, parseFloat(s.outlineWidth), s.outlineColor];
        }""")
        assert style[0] != "none" and style[1] >= 2
        assert contrast([style[2], "rgb(255, 255, 255)"]) >= 3
        box = focus.bounding_box()
        assert box["x"] - style[1] >= 0
        assert box["x"] + box["width"] + style[1] <= page.viewport_size["width"]


def background(locator):
    """Read rendered action emphasis without depending on class names."""
    return locator.evaluate("el => getComputedStyle(el).backgroundColor")


def assert_top_navigation(page, home, back=None):
    """Existing context is reachable before record details or editing forms."""
    navigation = page.get_by_role("navigation", name="Page navigation", exact=True)
    expect(navigation.get_by_role("link", name=home, exact=True)).to_be_visible()
    if back:
        expect(navigation.get_by_role("link", name=back, exact=True)).to_be_visible()
    assert navigation.evaluate(
        "el => el.getBoundingClientRect().bottom < "
        "document.querySelector('main h2, main form')?.getBoundingClientRect().top"
    )


def assert_short_navigation(page, home, back=None):
    """Short pages expose each existing destination once, before their content."""
    assert_top_navigation(page, home, back)
    navigation = page.get_by_role("navigation", name="Page navigation", exact=True)
    for link in navigation.get_by_role("link").all():
        destination = link.get_attribute("href")
        expect(page.locator(f'main a[href="{destination}"]')).to_have_count(1)
        assert_action_link_states(page, link)


def assert_compact_label(control):
    """Bound native text-label growth by its actual rendered line count."""
    metrics = control.evaluate("""el => {
      const range = document.createRange(); range.selectNodeContents(el);
      const rects = [...range.getClientRects()].filter(r => r.width > 0);
      const box = el.getBoundingClientRect(), style = getComputedStyle(el);
      return {lines: new Set(rects.map(r => r.top.toFixed(2))).size,
        height: box.height, width: box.width, font: parseFloat(style.fontSize),
        line: parseFloat(style.lineHeight), contained: rects.every(r =>
          r.left >= box.left - .5 && r.right <= box.right + .5 &&
          r.top >= box.top - .5 && r.bottom <= box.bottom + .5)};
    }""")
    assert metrics["lines"] >= 1 and metrics["font"] >= 16
    assert metrics["width"] >= 24 and metrics["contained"]
    assert max(38, metrics["lines"] * metrics["line"]) <= metrics["height"]
    assert metrics["height"] <= 42 + (metrics["lines"] - 1) * metrics["line"]
    return metrics["lines"]


@pytest.mark.ac("PLT-1.1", "PLT-4.2", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_public_actions_are_compact_grouped_native_controls(page, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto("/")
    expect(
        page.get_by_text(
            "Create test rounds, record results and review feedback with your team.",
            exact=True,
        )
    ).to_be_visible()
    expect(
        page.get_by_text("Testing workflows are coming soon.", exact=True)
    ).to_have_count(0)
    sign_in_link = page.get_by_role("link", name="Sign in", exact=True)
    demo = page.get_by_role("button", name="Create a demo workspace", exact=True)
    assert background(sign_in_link) == "rgb(255, 255, 255)"
    assert background(demo) != background(sign_in_link)
    group = sign_in_link.locator("..")
    expect(group.get_by_role("button", name="Create a demo workspace")).to_have_count(1)
    assert group.evaluate("el => getComputedStyle(el).gap") == "8px"
    for control in (sign_in_link, demo):
        assert_compact_label(control)
        assert control.evaluate("el => getComputedStyle(el).margin") == "0px"
    form = demo.locator("..")
    assert form.get_attribute("method") == "post"
    assert form.get_attribute("action") == "/demo/"
    expect(form.locator("input[name=csrfmiddlewaretoken]")).to_have_count(1)
    assert form.evaluate("el => getComputedStyle(el).margin") == "0px"
    assert_action_link_states(page, sign_in_link)
    assert_layout(page, width)
    group.evaluate("el => el.style.maxWidth = '160px'")
    assert assert_compact_label(demo) > 1
    assert_compact_label(sign_in_link)
    assert_layout(page, width)
    assert_keyboard_focus(page, 1)
    sign_in_link.click()
    expect(page).to_have_url("/sign-in/")


@pytest.mark.ac("PLT-4.2", "PLT-4.4", "PLT-4.5", "PLT-4.6")
@pytest.mark.parametrize("width", [320, 1440])
def test_repeated_edit_delete_groups_have_compact_targets(
    page, browser_accounts, width
):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(page, browser_accounts, "coordinator")
    page.goto(browser_accounts["draft"])
    for kind in ("criterion", "test case"):
        edit = page.get_by_role("link", name=f"Edit {kind}", exact=True)
        delete = page.get_by_role("button", name=f"Delete {kind}", exact=True)
        group = edit.locator("..")
        for control in (edit, delete):
            box = control.bounding_box()
            assert 32 <= box["height"] <= 36
            assert box["width"] >= 24
        assert group.evaluate("el => getComputedStyle(el).flexWrap") == "wrap"
        assert group.evaluate("el => getComputedStyle(el).gap") == "8px"
        a, b = edit.bounding_box(), delete.bounding_box()
        horizontal_gap = b["x"] - a["x"] - a["width"]
        vertical_gap = b["y"] - a["y"] - a["height"]
        assert horizontal_gap >= 7.9 or vertical_gap >= 7.9
        form = delete.locator("..")
        assert form.evaluate("el => getComputedStyle(el).margin") == "0px"
        assert form.get_attribute("method") == "post"
        expect(form.locator("input[name=csrfmiddlewaretoken]")).to_have_count(1)
        assert_action_link_states(page, edit)
    publish = page.get_by_role("button", name="Publish round", exact=True)
    assert 38 <= publish.bounding_box()["height"] <= 42
    assert_action_link_states(
        page, page.get_by_role("link", name="Edit round", exact=True)
    )
    assert_layout(page, width)


@pytest.mark.ac("PLT-4.5")
@pytest.mark.parametrize(
    ("role", "route", "label"),
    [
        ("coordinator", "draft", "Publish round"),
        ("tester", "entry", "Save draft"),
        ("coordinator", "draft", "Delete criterion"),
    ],
)
def test_button_contrast_at_rest_and_while_keyboard_pressed(
    page, browser_accounts, role, route, label
):
    sign_in(page, browser_accounts, role)
    page.goto(browser_accounts[route])
    control = page.get_by_role("button", name=label, exact=True)
    page.mouse.move(0, 0)
    assert_contrast(control)
    control.focus()
    page.keyboard.down("Space")
    try:
        assert control.evaluate("el => el.matches(':active')")
        assert not control.evaluate("el => el.matches(':hover')")
        assert_contrast(control)
    finally:
        page.keyboard.up("Space")


@pytest.mark.ac("PLT-4.2", "PLT-4.6", "PLT-4.7", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_coordinator_action_hierarchy_and_top_context(page, browser_accounts, width):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(page, browser_accounts, "coordinator")
    new_round = page.get_by_role("link", name="New round", exact=True)
    sign_out = page.get_by_role("button", name="Sign out", exact=True)
    assert background(new_round) != "rgba(0, 0, 0, 0)"
    assert background(new_round) != background(sign_out)
    assert sign_out.bounding_box()["y"] < new_round.bounding_box()["y"]
    assert sign_out.locator("..").get_attribute("method") == "post"
    assert (
        sign_out.locator("..").locator("input[name=csrfmiddlewaretoken]").count() == 1
    )
    new_round.click()
    assert_short_navigation(page, "Coordinator home")
    page.goto(browser_accounts["draft"])
    assert_top_navigation(page, "Coordinator home")
    edit = page.get_by_role("link", name="Edit criterion", exact=True)
    delete = page.get_by_role("button", name="Delete criterion", exact=True)
    add = page.get_by_role("link", name="Add acceptance criterion", exact=True)
    assert background(add) != background(edit)
    assert background(edit) == background(delete)
    assert edit.evaluate("el => getComputedStyle(el).color") != delete.evaluate(
        "el => getComputedStyle(el).color"
    )
    group = edit.locator("..")
    expect(group.get_by_role("button", name="Delete criterion")).to_be_visible()
    assert group.evaluate("el => getComputedStyle(el).display") == "flex"
    assert group.evaluate("el => getComputedStyle(el).flexWrap") == "wrap"
    assert delete.locator("..").get_attribute("method") == "post"
    assert_layout(page, width)
    edit.click()
    assert_short_navigation(page, "Coordinator home", "Back to round")
    page.get_by_role("navigation", name="Page navigation").get_by_role(
        "link", name="Back to round", exact=True
    ).click()
    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    assert_short_navigation(page, "Coordinator home", "Back to round")
    page.goto(browser_accounts["draft"])
    form_links = [
        (
            page.get_by_role("link", name=label, exact=True).get_attribute("href"),
            "Back to round",
        )
        for label in (
            "Edit round",
            "Add acceptance criterion",
            "Add test case",
            "Edit test case",
        )
    ]
    for route, back in form_links + [
        (browser_accounts["open"] + "retest/", "Back to round")
    ]:
        page.goto(route)
        assert_short_navigation(page, "Coordinator home", back)
        if route == browser_accounts["draft"] + "edit/":
            page.get_by_label("Title", exact=True).fill(" ")
            page.get_by_role("button", name="Save", exact=True).click()
            expect(
                page.get_by_text("Enter 1 to 120 characters.", exact=True)
            ).to_be_visible()
            assert_short_navigation(page, "Coordinator home", "Back to round")
            page.get_by_role("link", name="Back to round", exact=True).click()
            assert page.url.endswith(browser_accounts["draft"])
        assert_layout(page, width)
    page.goto(browser_accounts["open"] + "results/")
    assert_top_navigation(page, "Coordinator home", "Back to round")
    expect(page.locator("form")).to_have_count(0)
    expect(page.get_by_role("button")).to_have_count(0)
    assert_layout(page, width)


@pytest.mark.ac("PLT-4.2", "PLT-4.7", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_tester_action_emphasis_and_native_result_submission(
    page, browser_accounts, width
):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(page, browser_accounts, "tester")
    page.goto(browser_accounts["entry"])
    assert_short_navigation(page, "Tester home", "Back to round")
    save = page.get_by_role("button", name="Save draft", exact=True)
    submit = page.get_by_role("button", name="Submit", exact=True)
    assert background(save) != background(submit)
    assert save.get_attribute("value") == "save"
    assert submit.get_attribute("value") == "submit"
    assert save.locator("..").get_attribute("method") == "post"
    assert_layout(page, width)
    page.get_by_label("Observation", exact=True).fill("Synthetic revised observation")
    with page.expect_navigation(wait_until="load", timeout=10000):
        save.click()
    page.reload()
    expect(page.get_by_label("Observation", exact=True)).to_have_value(
        "Synthetic revised observation"
    )
    page.get_by_role("button", name="Observation feedback", exact=True).click()
    assert_short_navigation(page, "Tester home", "Back to result")
    page.goto(browser_accounts["entry"])
    page.get_by_role("button", name="Submit", exact=True).click()
    expect(page.get_by_text("Status: Submitted", exact=True)).to_be_visible()
    expect(page.locator("form")).to_have_count(0)
    assert_short_navigation(page, "Tester home", "Back to round")
    page.goto(browser_accounts["history"])
    assert_top_navigation(page, "Tester home", "Back to round")
    expect(page.locator("form")).to_have_count(0)
    expect(page.get_by_role("button")).to_have_count(0)
    assert_layout(page, width)


@pytest.mark.ac("PLT-4.1", "PLT-4.2", "PLT-4.3", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_public_pages_controls_messages_and_credentials(page, browser_accounts, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto("/")
    assert_layout(page, width)
    assert_keyboard_focus(page, 2)
    page.goto("/sign-in/")
    assert_layout(page, width)
    assert_keyboard_focus(page, 3)
    page.get_by_label("Username", exact=True).fill(browser_accounts["coordinator"])
    page.get_by_label("Password", exact=True).fill("IncorrectSynthetic16")
    page.get_by_role("button", name="Sign in", exact=True).click()
    alert = page.get_by_role("alert")
    expect(alert).to_have_text("Username or password is incorrect.")
    error = alert.locator("..")
    error_background = error.evaluate("el => getComputedStyle(el).backgroundColor")
    assert error.evaluate("el => parseFloat(getComputedStyle(el).borderLeftWidth)") >= 3
    assert_layout(page, width)
    sign_in(page, browser_accounts, "coordinator")
    page.get_by_role("button", name="Sign out", exact=True).click()
    status = page.get_by_role("status")
    expect(status).to_have_text("You have signed out.")
    assert (
        status.evaluate("el => getComputedStyle(el).backgroundColor")
        != error_background
    )
    assert_layout(page, width)
    page.goto("/")
    page.get_by_role("button", name="Create a demo workspace", exact=True).click()
    expect(page.get_by_role("heading", name="Your demo workspace")).to_be_visible()
    assert_layout(page, width)
    cells = page.locator("tbody td")
    assert cells.count() == 9
    for cell in cells.all():
        assert cell.inner_text()
        assert cell.evaluate("el => getComputedStyle(el).userSelect") != "none"
        assert cell.evaluate("el => parseFloat(getComputedStyle(el).paddingTop)") >= 6
        assert (
            cell.evaluate("el => parseFloat(getComputedStyle(el).borderBottomWidth)")
            >= 1
        )
    sign_in_link = page.get_by_role("link", name="Sign in", exact=True)
    assert_action_link_states(page, sign_in_link)
    expect(sign_in_link).to_have_class("action secondary")
    sign_in_link.click()
    expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()


@pytest.mark.ac("PLT-4.2", "PLT-4.4", "PLT-4.5", "PLT-4.10")
@pytest.mark.parametrize("width", [320, 1440])
def test_sign_in_returns_to_public_home(page, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto("/sign-in/")
    back = page.get_by_role("link", name="Back to home", exact=True)
    expect(back).to_have_count(1)
    assert_action_link_states(page, back)
    assert back.bounding_box()["y"] < page.locator("form").bounding_box()["y"]
    back.click()
    expect(page.get_by_role("heading", name="Relay", exact=True)).to_be_visible()
    assert_layout(page, width)


@pytest.mark.ac("PLT-4.1", "PLT-4.2", "PLT-4.3", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_coordinator_forms_long_text_and_ai_states(page, browser_accounts, width):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(page, browser_accounts, "coordinator")
    assert_layout(page, width)
    page.goto(browser_accounts["draft"])
    assert_layout(page, width)
    assert (
        page.get_by_text("State: Draft", exact=True).evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
        != "rgba(0, 0, 0, 0)"
    )
    assert (
        page.get_by_role("link", name="Edit round", exact=True)
        .locator("..")
        .evaluate("el => getComputedStyle(el).backgroundColor")
        == "rgba(0, 0, 0, 0)"
    )
    criterion_row = page.get_by_role("link", name="Edit criterion", exact=True).locator(
        "../.."
    )
    expect(criterion_row.locator(":scope > span[dir=auto]")).to_have_text(LONG)
    page.get_by_role("link", name="Add test case", exact=True).click()
    assert_layout(page, width)
    assert_keyboard_focus(page, 3)
    page.get_by_label("Title", exact=True).fill(" ")
    page.get_by_label("Steps", exact=True).fill("Synthetic steps")
    page.get_by_label("Expected result", exact=True).fill("Synthetic expected result")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Add test case", exact=True).click()
    expect(page.locator(".error")).to_have_text("Enter 1 to 120 characters.")
    assert_layout(page, width)
    page.goto(browser_accounts["draft"])
    page.get_by_role("link", name="Draft test cases with AI", exact=True).click()
    assert_layout(page, width)
    checkbox = page.get_by_role("checkbox")
    checkbox.check()
    box, label = checkbox.bounding_box(), page.locator("label").bounding_box()
    assert box["x"] + box["width"] <= label["x"]
    assert abs(box["y"] - label["y"]) < 12
    with mock.patch("ai.views.gateway.complete", return_value=Failed("unavailable")):
        page.get_by_role("button", name="Draft test cases", exact=True).click()
    expect(page.locator(".error")).to_be_visible()
    assert_short_navigation(page, "Coordinator home", "Back to round")
    assert_layout(page, width)
    reply = {
        "drafts": [
            {
                "title": "Synthetic suggestion",
                "steps": LONG,
                "expected_result": MARKUP,
                "criteria": ["C1"],
            }
        ]
    }
    with mock.patch(
        "ai.views.gateway.complete", return_value=Success(json.dumps(reply))
    ):
        page.get_by_role("button", name="Draft test cases", exact=True).click()
    expect(page.get_by_role("button", name="Use this draft")).to_be_visible()
    assert_short_navigation(page, "Coordinator home", "Back to round")
    assert_layout(page, width)
    expect(page.locator("main")).to_contain_text(MARKUP)
    expect(page.locator("main b")).to_have_count(0)


@pytest.mark.ac("PLT-4.1", "PLT-4.2", "PLT-4.3", "PLT-4.4", "PLT-4.5")
@pytest.mark.parametrize("width", [320, 1440])
def test_tester_result_and_feedback_long_content(page, browser_accounts, width):
    page.set_viewport_size({"width": width, "height": 900})
    sign_in(page, browser_accounts, "tester")
    assert_layout(page, width)
    page.get_by_role("link", name="Synthetic presentation round", exact=True).click()
    assert_layout(page, width)
    expect(page.locator("main")).to_contain_text(MARKUP)
    expect(page.locator("main b")).to_have_count(0)
    page.goto(browser_accounts["entry"])
    assert_layout(page, width)
    expect(page.get_by_label("Observation", exact=True)).to_have_value(LONG)
    page.get_by_role("button", name="Observation feedback", exact=True).click()
    assert_layout(page, width)
    expect(page.locator("span[dir=auto]", has_text=LONG).first).to_have_text(LONG)
    with mock.patch(
        "ai.feedback_views.gateway.complete", return_value=Failed("unavailable")
    ):
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
    expect(page.locator(".error")).to_be_visible()
    assert_short_navigation(page, "Tester home", "Back to result")
    assert_layout(page, width)
    with mock.patch(
        "ai.feedback_views.gateway.complete",
        return_value=Success(json.dumps({"questions": ["Which " + LONG[:200] + "?"]})),
    ):
        page.get_by_role("button", name="Suggest missing details", exact=True).click()
    expect(page.get_by_role("heading", name="Questions to consider")).to_be_visible()
    assert_short_navigation(page, "Tester home", "Back to result")
    assert_layout(page, width)


@pytest.mark.ac("PLT-4.1", "PLT-4.3", "PLT-4.4", "PLT-4.5", "PLT-4.17")
@pytest.mark.parametrize("width", [320, 1440])
def test_existing_error_pages_share_the_error_treatment(page, browser_accounts, width):
    """Exercise existing 404, 429, 503, 403 and conflict responses in-browser."""
    page.set_viewport_size({"width": width, "height": 900})

    def check_error(home=None):
        """Check the error treatment; follow PLT-4.17's link to the `home` heading."""
        assert_layout(page, width)
        error = page.locator(".error")
        expect(error).to_be_visible()
        heading = error.get_by_role("heading", level=1)
        expect(heading).to_be_visible()
        assert (
            error.evaluate("el => parseFloat(getComputedStyle(el).borderLeftWidth)")
            >= 3
        )
        if home is None:
            return
        navigation = page.get_by_role("navigation", name="Page navigation", exact=True)
        back = navigation.get_by_role("link", name="Back to home", exact=True)
        expect(page.get_by_role("link")).to_have_count(1)
        expect(back).to_have_attribute("href", "/")
        assert_action_link_states(page, back)
        assert back.bounding_box()["y"] < heading.bounding_box()["y"]
        back.click()
        expect(page.get_by_role("heading", name=home, exact=True)).to_be_visible()

    assert page.goto("/missing-presentation-page/").status == 404
    check_error("Relay")
    page.goto("/")
    with mock.patch("accounts.views._any_reached", return_value=True):
        with page.expect_response(
            lambda response: response.url.endswith("/demo/")
        ) as response:
            page.get_by_role(
                "button", name="Create a demo workspace", exact=True
            ).click()
        assert response.value.status == 429
    check_error("Relay")
    page.goto("/")
    with mock.patch(
        "accounts.demo.generate_passwords",
        side_effect=RuntimeError("Synthetic unavailable"),
    ):
        with page.expect_response(
            lambda response: response.url.endswith("/demo/")
        ) as response:
            page.get_by_role(
                "button", name="Create a demo workspace", exact=True
            ).click()
        assert response.value.status == 503
    check_error("Relay")
    sign_in(page, browser_accounts, "coordinator")
    assert page.goto("/tester/").status == 403
    check_error("Coordinator home")
    assert page.goto(browser_accounts["draft"] + "results/").status == 409
    check_error()
