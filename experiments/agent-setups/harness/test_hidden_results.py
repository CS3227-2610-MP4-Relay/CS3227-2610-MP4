"""Hidden acceptance suite for task 3 of the agent-setups experiment (#31).

Written from the decisions in the task prompt for issue #13 (RES-2), before any
run. It drives the tester's result entry page over HTTP and judges outcomes
only from status codes and page text: "Status: Draft", "Status: Submitted", the
outcome and observation shown, and whether the entry form is present. It never
imports a result model and never checks message wording, which the prompt
leaves to the candidate. Rounds are published, closed and retested through the
existing `rounds` services.
Races between result writes, closes and retests are not covered: an unpaused
race cannot be made to overlap reliably from outside the code.

Two checks are left out because the prompt leaves them to the candidate: whether
a retest copies a saved draft to the new build, and what closing does to a draft,
which only a reopen, not a product action, could show.
"""

import re
from html import unescape
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from django.db import transaction
from django.test import Client

from accounts.models import User, Workspace
from rounds import services
from rounds.models import Build, Case, CaseCriterion, Criterion, Round

PASSWORD = "Synthetic16Chars"
ALPHA = "Synthetic observation alpha"
BRAVO = "Synthetic observation bravo"
# Spaces, a tab and a line feed: whitespace only.
BLANK = "  " + chr(9) + chr(10) + "  "
SCRIPT = chr(0x3C) + "script" + chr(0x3E)
MARKUP = SCRIPT + "alert(1)" + chr(0x3C) + "/script" + chr(0x3E)


def entry(round_, case, build):
    """The result entry page of `case` on `build` in `round_`."""
    return f"/tester/rounds/{round_.pk}/cases/{case.pk}/builds/{build.pk}/result/"


def text(response):
    """The page's text with tags removed, entities decoded, whitespace collapsed."""
    plain = re.sub(r"<[^>]+>", " ", response.content.decode())
    return re.sub(r"\s+", " ", unescape(plain))


def raw(response):
    """The page's markup with entities decoded, attribute values included."""
    return unescape(response.content.decode())


def status(response):
    """The status the page's text shows, Draft or Submitted, or None."""
    shown = [s for s in ("Draft", "Submitted") if f"Status: {s}" in text(response)]
    assert len(shown) <= 1, shown
    return shown[0] if shown else None


def shows_outcome(response, outcome):
    """Whether the page's text names `outcome` as a word, in any case."""
    return re.search(rf"\b{outcome}\b", text(response), re.IGNORECASE) is not None


class Controls(HTMLParser):
    """The form controls and links of a page, as a browser would read them."""

    def __init__(self, response):
        super().__init__()
        self.names = set()
        self.outcomes = set()
        self.outcome = None
        self.observation = None
        self.buttons = {}
        self.links = []
        self._select = self._option = self._area = self._button = self._link = None
        self.feed(response.content.decode())
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        name, kind = attrs.get("name"), (attrs.get("type") or "").lower()
        if tag in ("input", "select", "textarea", "button") and name:
            self.names.add(name)
        if tag == "select":
            self._select = name
        elif tag == "option" and self._select == "outcome":
            self._end_option()
            self._option = [attrs.get("value"), "selected" in attrs, ""]
        elif tag == "textarea" and name == "observation":
            self._area = []
        elif tag == "input" and name == "outcome" and kind == "radio":
            self.outcomes.add(attrs.get("value"))
            if "checked" in attrs:
                self.outcome = attrs.get("value")
        elif tag == "input" and name == "observation":
            self.observation = attrs.get("value") or ""
        elif tag == "input" and name == "action" and kind == "submit":
            self.buttons[attrs.get("value")] = attrs.get("value")
        elif tag == "button" and name == "action" and kind in ("", "submit"):
            self._button = [attrs.get("value"), ""]
        elif tag == "a":
            self._link = [attrs.get("href") or "", ""]

    def handle_data(self, data):
        for part in (self._option, self._button, self._link):
            if part is not None:
                part[-1] += data
        if self._area is not None:
            self._area.append(data)

    def handle_endtag(self, tag):
        if tag in ("option", "select"):
            self._end_option()
            if tag == "select":
                self._select = None
        elif tag == "textarea" and self._area is not None:
            value = "".join(self._area)
            # A browser drops one line break directly after <textarea>.
            self.observation = value.removeprefix("\r\n").removeprefix("\n")
            self._area = None
        elif tag == "button" and self._button is not None:
            value, label = self._button
            self.buttons[value] = " ".join(label.split())
            self._button = None
        elif tag == "a" and self._link is not None:
            href, label = self._link
            self.links.append((urlparse(href).path, " ".join(label.split())))
            self._link = None

    def _end_option(self):
        if self._option is not None:
            value, selected, label = self._option
            value = label.strip() if value is None else value
            self.outcomes.add(value)
            if selected:
                self.outcome = value
            self._option = None


def has_form(response):
    """Whether the page offers the entry form's outcome and observation fields."""
    return {"outcome", "observation"} <= Controls(response).names


def record_links(response):
    """The paths of the page's links whose text includes "Record result"."""
    return {
        href for href, label in Controls(response).links if "Record result" in label
    }


def make_user(workspace, username, role):
    """An account with `role` in `workspace`."""
    return User.objects.create_user(username, PASSWORD, workspace=workspace, role=role)


def signed_in(user):
    """A test client signed in as `user`."""
    client = Client()
    client.force_login(user)
    return client


def round_with_cases(workspace, count=2, state="open"):
    """A round with `count` linked cases, published on build B1 unless Draft."""
    round_ = Round.objects.create(workspace=workspace, title="Synthetic round")
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    cases = []
    for number in range(count):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {number + 1}",
            steps="Steps",
            expected_result="Result",
        )
        CaseCriterion.objects.create(case=case, criterion=criterion)
        cases.append(case)
    if state in ("open", "closed"):
        with transaction.atomic():
            locked = Round.objects.select_for_update().get(pk=round_.pk)
            services.publish(locked, "B1")
    if state == "closed":
        close(round_)
    round_.refresh_from_db()
    return round_, cases


def close(round_):
    """Close the Open `round_` through the rounds service."""
    with transaction.atomic():
        services.close(Round.objects.select_for_update().get(pk=round_.pk))


def retest(round_, cases, label):
    """Request a retest of `cases` in the Open `round_` on a new build."""
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=round_.pk)
        return services.request_retest(locked, label, [case.pk for case in cases])


def reopen(round_):
    """Move a Closed round back to Open, which only a test can do.

    Nothing in the product reopens a round; this shows whether an entry
    recorded before closing was kept.
    """
    Round.objects.filter(pk=round_.pk).update(state=Round.State.OPEN, closed_at=None)


def post(client, address, action, outcome="fail", observation=ALPHA):
    """POST the entry form; None leaves a field out."""
    data = {"action": action}
    if outcome is not None:
        data["outcome"] = outcome
    if observation is not None:
        data["observation"] = observation
    return client.post(address, data)


@pytest.fixture
def setup(db):
    """A workspace's coordinator, two testers, an Open and a Closed round."""
    workspace = Workspace.objects.create(name="Demo workspace hid3a")
    coordinator = make_user(workspace, "coord-hid3a", "coordinator")
    tester = make_user(workspace, "tester-hid3a", "tester")
    other = make_user(workspace, "tester-hid3b", "tester")
    round_, cases = round_with_cases(workspace)
    closed, closed_cases = round_with_cases(workspace, state="closed")
    b1 = Build.objects.get(round=round_)
    return SimpleNamespace(
        workspace=workspace,
        coordinator=coordinator,
        tester=tester,
        client=signed_in(tester),
        other_tester=other,
        other=signed_in(other),
        round=round_,
        cases=cases,
        b1=b1,
        url=entry(round_, cases[0], b1),
        closed=closed,
        closed_url=entry(closed, closed_cases[0], Build.objects.get(round=closed)),
    )


# --- "Record result" links on the tester's round page ---


def test_open_round_page_links_each_case_to_its_current_build(setup):
    s = setup
    response = s.client.get(f"/tester/rounds/{s.round.pk}/")
    assert response.status_code == 200
    assert record_links(response) == {entry(s.round, case, s.b1) for case in s.cases}


def test_after_a_retest_only_the_current_build_is_linked(setup):
    s = setup
    b2 = retest(s.round, [s.cases[0]], "B2")
    response = s.client.get(f"/tester/rounds/{s.round.pk}/")
    assert record_links(response) == {
        entry(s.round, s.cases[0], b2),
        entry(s.round, s.cases[1], s.b1),
    }


def test_a_closed_round_page_has_no_record_result_link(setup):
    s = setup
    response = s.client.get(f"/tester/rounds/{s.closed.pk}/")
    assert response.status_code == 200
    assert "Record result" not in text(response)
    assert not [href for href, _ in Controls(response).links if "/result/" in href]


# --- A fresh entry and drafts ---


def test_a_fresh_entry_shows_the_form_without_a_status(setup):
    s = setup
    response = s.client.get(s.url)
    assert response.status_code == 200
    controls = Controls(response)
    assert {"outcome", "observation"} <= controls.names
    assert controls.outcomes - {"", None} == {"pass", "fail"}
    assert controls.buttons.get("save") == "Save draft"
    assert controls.buttons.get("submit") == "Submit"
    assert status(response) is None
    assert status(s.client.get(s.url)) is None


def test_saving_a_draft_redirects_to_the_same_page(setup):
    s = setup
    response = post(s.client, s.url, "save")
    assert response.status_code == 302
    assert urlparse(response["Location"]).path == s.url


def test_a_saved_draft_shows_draft_status_and_its_values(setup):
    s = setup
    post(s.client, s.url, "save", "fail", ALPHA)
    response = s.client.get(s.url)
    assert response.status_code == 200
    assert status(response) == "Draft"
    controls = Controls(response)
    assert (controls.outcome, controls.observation) == ("fail", ALPHA)


def test_a_draft_is_kept_for_a_new_session(setup):
    s = setup
    post(s.client, s.url, "save", "pass", ALPHA)
    response = signed_in(s.tester).get(s.url)
    assert status(response) == "Draft"
    controls = Controls(response)
    assert (controls.outcome, controls.observation) == ("pass", ALPHA)


def test_a_draft_can_be_replaced(setup):
    s = setup
    post(s.client, s.url, "save", "pass", ALPHA)
    assert post(s.client, s.url, "save", "fail", BRAVO).status_code == 302
    response = s.client.get(s.url)
    assert status(response) == "Draft"
    controls = Controls(response)
    assert (controls.outcome, controls.observation) == ("fail", BRAVO)
    assert ALPHA not in raw(response)


# --- Submission ---


def test_a_result_can_be_submitted_directly(setup):
    s = setup
    response = post(s.client, s.url, "submit", "fail", ALPHA)
    assert response.status_code == 302
    assert urlparse(response["Location"]).path == s.url
    page = s.client.get(s.url)
    assert status(page) == "Submitted"
    assert shows_outcome(page, "fail")
    assert ALPHA in text(page)


def test_a_saved_draft_can_be_submitted_with_the_supplied_values(setup):
    s = setup
    post(s.client, s.url, "save", "pass", ALPHA)
    assert post(s.client, s.url, "submit", "fail", BRAVO).status_code == 302
    page = s.client.get(s.url)
    assert status(page) == "Submitted"
    assert shows_outcome(page, "fail")
    assert BRAVO in text(page)
    assert ALPHA not in raw(page)


def test_the_submitted_view_is_read_only(setup):
    s = setup
    post(s.client, s.url, "submit", "fail", ALPHA)
    page = s.client.get(s.url)
    assert page.status_code == 200
    assert status(page) == "Submitted"
    assert not Controls(page).names & {"outcome", "observation", "action"}


@pytest.mark.parametrize(
    "action, outcome, observation",
    [
        ("save", "pass", BRAVO),
        ("submit", "pass", BRAVO),
        ("submit", "fail", ALPHA),
        ("submit", "maybe", BRAVO),
    ],
    ids=["save", "resubmit", "identical", "invalid"],
)
def test_any_post_after_submission_gets_409_and_changes_nothing(
    setup, action, outcome, observation
):
    s = setup
    post(s.client, s.url, "submit", "fail", ALPHA)
    assert post(s.client, s.url, action, outcome, observation).status_code == 409
    page = s.client.get(s.url)
    assert status(page) == "Submitted"
    assert shows_outcome(page, "fail")
    assert ALPHA in text(page)
    assert BRAVO not in raw(page)


# --- Validation ---


@pytest.mark.parametrize(
    "observation", [None, "", BLANK], ids=["absent", "empty", "blank"]
)
def test_fail_without_an_observation_is_refused(setup, observation):
    s = setup
    response = post(s.client, s.url, "submit", "fail", observation)
    assert response.status_code == 200
    assert has_form(response)
    assert status(s.client.get(s.url)) is None


def test_pass_with_an_empty_observation_is_accepted(setup):
    s = setup
    assert post(s.client, s.url, "submit", "pass", "").status_code == 302
    page = s.client.get(s.url)
    assert status(page) == "Submitted"
    assert shows_outcome(page, "pass")


def test_an_observation_of_2000_characters_is_accepted(setup):
    s = setup
    assert post(s.client, s.url, "save", "fail", "o" * 2000).status_code == 302
    response = s.client.get(s.url)
    assert status(response) == "Draft"
    assert Controls(response).observation == "o" * 2000


@pytest.mark.parametrize("action", ["save", "submit"])
def test_an_observation_of_2001_characters_is_refused(setup, action):
    s = setup
    response = post(s.client, s.url, action, "fail", "o" * 2001)
    assert response.status_code == 200
    assert has_form(response)
    assert status(s.client.get(s.url)) is None


@pytest.mark.parametrize(
    "outcome", [None, "", "maybe"], ids=["absent", "empty", "other"]
)
def test_an_invalid_or_absent_outcome_is_refused(setup, outcome):
    s = setup
    response = post(s.client, s.url, "submit", outcome, ALPHA)
    assert response.status_code == 200
    assert has_form(response)
    assert status(s.client.get(s.url)) is None


def test_a_refused_post_keeps_the_earlier_draft(setup):
    s = setup
    post(s.client, s.url, "save", "pass", ALPHA)
    assert post(s.client, s.url, "submit", "fail", "").status_code == 200
    assert post(s.client, s.url, "save", "maybe", BRAVO).status_code == 200
    response = s.client.get(s.url)
    assert status(response) == "Draft"
    controls = Controls(response)
    assert (controls.outcome, controls.observation) == ("pass", ALPHA)


# --- Privacy between testers ---


def test_a_second_tester_sees_a_fresh_form(setup):
    s = setup
    post(s.client, s.url, "save", "fail", ALPHA)
    response = s.other.get(s.url)
    assert response.status_code == 200
    assert has_form(response)
    assert status(response) is None
    assert ALPHA not in raw(response)


def test_two_testers_keep_separate_drafts(setup):
    s = setup
    post(s.client, s.url, "save", "fail", ALPHA)
    assert post(s.other, s.url, "save", "pass", BRAVO).status_code == 302
    mine, theirs = s.client.get(s.url), s.other.get(s.url)
    assert (status(mine), status(theirs)) == ("Draft", "Draft")
    assert (Controls(mine).outcome, Controls(mine).observation) == ("fail", ALPHA)
    assert (Controls(theirs).outcome, Controls(theirs).observation) == ("pass", BRAVO)
    assert BRAVO not in raw(mine)
    assert ALPHA not in raw(theirs)


def test_identity_fields_in_a_post_cannot_reach_another_testers_entry(setup):
    s = setup
    data = {"action": "save", "outcome": "fail", "observation": ALPHA}
    for name in ("tester", "tester_id", "user", "user_id"):
        data[name] = s.other_tester.pk
    assert s.client.post(s.url, data).status_code == 302
    theirs = s.other.get(s.url)
    assert status(theirs) is None
    assert ALPHA not in raw(theirs)


def test_one_testers_submission_leaves_the_other_free_to_save(setup):
    s = setup
    post(s.client, s.url, "submit", "fail", ALPHA)
    assert post(s.other, s.url, "save", "pass", BRAVO).status_code == 302
    theirs = s.other.get(s.url)
    assert status(theirs) == "Draft"
    assert ALPHA not in raw(theirs)
    mine = s.client.get(s.url)
    assert status(mine) == "Submitted"
    assert ALPHA in text(mine)
    assert BRAVO not in raw(mine)


# --- Refusals ---


@pytest.mark.parametrize("method", ["get", "post"])
def test_signed_out_is_redirected_to_sign_in(setup, method):
    s = setup
    response = getattr(Client(), method)(s.url)
    assert response.status_code == 302
    assert urlparse(response["Location"]).path == "/sign-in/"


def test_a_coordinator_gets_403(setup):
    s = setup
    client = signed_in(s.coordinator)
    assert client.get(s.url).status_code == 403
    assert post(client, s.url, "save").status_code == 403


def missing(model):
    """An ID no `model` row has."""
    return SimpleNamespace(pk=max(model.objects.values_list("pk", flat=True)) + 100)


def unrelated_entry(s, kind):
    """An entry URL whose round, case or build the tester cannot use."""
    case, b1 = s.cases[0], s.b1
    if kind == "missing round":
        return entry(missing(Round), case, b1)
    if kind == "missing case":
        return entry(s.round, missing(Case), b1)
    if kind == "missing build":
        return entry(s.round, case, missing(Build))
    if kind == "draft round":
        draft, draft_cases = round_with_cases(s.workspace, state="draft")
        return entry(draft, draft_cases[0], b1)
    if kind == "foreign round":
        foreign = Workspace.objects.create(name="Demo workspace hid3b")
        other, other_cases = round_with_cases(foreign)
        return entry(other, other_cases[0], Build.objects.get(round=other))
    if kind == "case of another round":
        _, other_cases = round_with_cases(s.workspace)
        return entry(s.round, other_cases[0], b1)
    if kind == "build of another round":
        other, _ = round_with_cases(s.workspace)
        return entry(s.round, case, Build.objects.get(round=other))
    if kind == "build not covering the case":
        b2 = retest(s.round, [s.cases[1]], "B2")
        return entry(s.round, case, b2)
    raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind",
    [
        "missing round",
        "missing case",
        "missing build",
        "draft round",
        "foreign round",
        "case of another round",
        "build of another round",
        "build not covering the case",
    ],
)
def test_an_unusable_round_case_or_build_gets_404(setup, kind):
    s = setup
    assert s.client.get(s.url).status_code == 200
    address = unrelated_entry(s, kind)
    assert s.client.get(address).status_code == 404
    assert post(s.client, address, "save").status_code == 404


def test_a_closed_round_gets_409_on_get_and_post(setup):
    s = setup
    assert s.client.get(s.closed_url).status_code == 409
    assert post(s.client, s.closed_url, "save").status_code == 409
    assert post(s.client, s.closed_url, "submit").status_code == 409


# --- Retests ---


def test_after_a_retest_the_old_build_gets_409(setup):
    s = setup
    post(s.client, s.url, "save", "fail", ALPHA)
    retest(s.round, [s.cases[0]], "B2")
    assert s.client.get(s.url).status_code == 409
    assert post(s.client, s.url, "save", "pass", BRAVO).status_code == 409
    assert post(s.client, s.url, "submit", "pass", BRAVO).status_code == 409


def test_a_case_not_selected_for_a_retest_keeps_its_entry(setup):
    s = setup
    address = entry(s.round, s.cases[1], s.b1)
    post(s.client, address, "save", "fail", ALPHA)
    retest(s.round, [s.cases[0]], "B2")
    response = s.client.get(address)
    assert status(response) == "Draft"
    controls = Controls(response)
    assert (controls.outcome, controls.observation) == ("fail", ALPHA)


# --- Escaping ---


def test_markup_in_an_observation_is_escaped_in_the_submitted_view(setup):
    s = setup
    assert post(s.client, s.url, "submit", "fail", MARKUP).status_code == 302
    page = s.client.get(s.url)
    assert status(page) == "Submitted"
    assert SCRIPT not in page.content.decode()
    assert MARKUP in text(page)


def test_markup_in_a_draft_observation_is_escaped_in_the_form(setup):
    s = setup
    assert post(s.client, s.url, "save", "fail", MARKUP).status_code == 302
    page = s.client.get(s.url)
    assert SCRIPT not in page.content.decode()
    assert Controls(page).observation == MARKUP
