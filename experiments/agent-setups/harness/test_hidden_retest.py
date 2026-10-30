"""Hidden acceptance suite for task 2 of the agent-setups experiment (#31).

Written from RND-5 as it stood at 99169c7, the route table and the decisions in
the task prompt, before any run. It drives the coordinator's pages over HTTP
and checks outcomes through the Build records that existed at the start, so it
does not depend on how a candidate structures its code. RND-5.7's races are
not covered: an unpaused race cannot be made to overlap reliably from outside
the code.
"""

import re

import pytest
from django.db import transaction
from django.test import Client

from accounts.models import User, Workspace
from rounds import services
from rounds.models import Build, Case, CaseCriterion, Criterion, Round

ZWSP = chr(0x200B)
SCRIPT = chr(0x3C) + "script" + chr(0x3E)
MARKUP = SCRIPT + "alert(1)" + chr(0x3C) + "/script" + chr(0x3E)


def url(round_):
    """The retest page of `round_`."""
    return f"/coordinator/rounds/{round_.pk}/retest/"


def text(response):
    """The page's text with tags removed and whitespace collapsed."""
    plain = re.sub(r"<[^>]+>", "", response.content.decode())
    return re.sub(r"\s+", " ", plain)


def workspace_with_coordinator(name):
    """A workspace and its Test Coordinator."""
    workspace = Workspace.objects.create(name=f"Demo workspace {name}")
    user = User.objects.create_user(
        f"coord-{name}", "Synthetic16Chars", workspace=workspace, role="coordinator"
    )
    return workspace, user


def signed_in(user):
    """A test client signed in as `user`."""
    client = Client()
    client.force_login(user)
    return client


def round_with_cases(workspace, count=3, state="open"):
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
        with transaction.atomic():
            services.close(Round.objects.select_for_update().get(pk=round_.pk))
    round_.refresh_from_db()
    return round_, cases


def current_build(case):
    """The last build covering `case`."""
    return Build.objects.filter(cases=case).order_by("id").last()


@pytest.fixture
def setup(db):
    """A coordinator's client and an Open round with three cases on build B1."""
    workspace, user = workspace_with_coordinator("hid2a")
    round_, cases = round_with_cases(workspace)
    return signed_in(user), workspace, user, round_, cases


# --- RND-5.8: rules for every round action ---


def test_open_round_has_the_retest_page(setup):
    client, _, _, round_, _ = setup
    response = client.get(url(round_))
    assert response.status_code == 200
    assert "Request a retest" in text(response)


def test_the_open_round_page_links_to_the_retest_page(setup):
    client, _, _, round_, _ = setup
    page = client.get(f"/coordinator/rounds/{round_.pk}/").content.decode()
    assert url(round_) in page


@pytest.mark.parametrize("state", ["draft", "closed"])
def test_a_draft_or_closed_round_gets_409(db, state):
    workspace, user = workspace_with_coordinator("hid2b")
    round_, cases = round_with_cases(workspace, state=state)
    client = signed_in(user)
    builds = Build.objects.count()
    assert client.get(url(round_)).status_code == 409
    response = client.post(url(round_), {"cases": [cases[0].pk], "label": "B2"})
    assert response.status_code == 409
    assert Build.objects.count() == builds


def test_a_draft_round_page_has_no_retest_link(db):
    workspace, user = workspace_with_coordinator("hid2c")
    round_, _ = round_with_cases(workspace, state="draft")
    page = signed_in(user).get(f"/coordinator/rounds/{round_.pk}/").content.decode()
    assert url(round_) not in page


def test_signed_out_is_redirected_to_sign_in(setup):
    _, _, _, round_, _ = setup
    response = Client().get(url(round_))
    assert response.status_code == 302
    assert "/sign-in/" in response["Location"]


def test_a_tester_gets_403(setup):
    _, workspace, _, round_, _ = setup
    tester = User.objects.create_user(
        "tester-hid2a", "Synthetic16Chars", workspace=workspace, role="tester"
    )
    assert signed_in(tester).get(url(round_)).status_code == 403


def test_another_workspaces_round_gets_404(setup):
    client, *_ = setup
    other_workspace, _ = workspace_with_coordinator("hid2d")
    other, _ = round_with_cases(other_workspace)
    assert client.get(url(other)).status_code == 404
    assert client.post(url(other), {"label": "B2"}).status_code == 404


def test_markup_in_the_label_is_escaped_in_the_success_message(setup):
    client, _, _, round_, cases = setup
    response = client.post(
        url(round_), {"cases": [cases[0].pk], "label": MARKUP}, follow=True
    )
    assert Build.objects.filter(round=round_).count() == 2
    assert SCRIPT not in response.content.decode()


# --- RND-5.1: happy path ---


def test_two_selected_cases_move_to_the_new_build(setup):
    client, _, _, round_, cases = setup
    data = {"cases": [cases[0].pk, cases[2].pk], "label": "B2"}
    response = client.post(url(round_), data, follow=True)
    assert response.status_code == 200
    assert "Retest requested for 2 test cases on build B2." in text(response)
    new = Build.objects.get(round=round_, label="B2")
    assert set(new.cases.all()) == {cases[0], cases[2]}
    assert current_build(cases[0]) == new
    assert current_build(cases[2]) == new
    assert current_build(cases[1]).label == "B1"


def test_one_case_uses_the_singular(setup):
    client, _, _, round_, cases = setup
    data = {"cases": [cases[1].pk], "label": "B2"}
    response = client.post(url(round_), data, follow=True)
    assert "Retest requested for 1 test case on build B2." in text(response)


def test_one_case_submitted_twice_counts_once(setup):
    client, _, _, round_, cases = setup
    data = {"cases": [cases[1].pk, cases[1].pk], "label": "B2"}
    response = client.post(url(round_), data, follow=True)
    assert "Retest requested for 1 test case on build B2." in text(response)
    assert Build.objects.get(round=round_, label="B2").cases.count() == 1


# --- RND-5.2: boundaries ---


def test_no_case_is_refused(setup):
    client, _, _, round_, _ = setup
    response = client.post(url(round_), {"label": "B2"})
    assert response.status_code == 200
    assert "Select at least one test case." in text(response)
    assert Build.objects.filter(round=round_).count() == 1


def test_a_100_character_label_is_accepted(setup):
    client, _, _, round_, cases = setup
    client.post(url(round_), {"cases": [cases[0].pk], "label": "L" * 100})
    assert Build.objects.filter(round=round_, label="L" * 100).exists()


@pytest.mark.parametrize("label", ["", "   ", ZWSP, "L" * 101])
def test_an_empty_invisible_or_too_long_label_is_refused(setup, label):
    client, _, _, round_, cases = setup
    response = client.post(url(round_), {"cases": [cases[0].pk], "label": label})
    assert response.status_code == 200
    assert "Enter 1 to 100 characters." in text(response)
    assert Build.objects.filter(round=round_).count() == 1


# --- RND-5.3: duplicate labels ---


@pytest.mark.parametrize("label", ["B1", "B" + ZWSP + "1"], ids=["equal", "format"])
def test_a_used_label_is_refused(setup, label):
    client, _, _, round_, cases = setup
    response = client.post(url(round_), {"cases": [cases[0].pk], "label": label})
    assert response.status_code == 200
    assert "This build label is already used in this round." in text(response)
    assert Build.objects.filter(round=round_).count() == 1


def test_a_decomposed_form_of_a_used_label_is_refused(setup):
    client, _, _, round_, cases = setup
    composed = "Caf" + chr(0xE9)
    decomposed = "Cafe" + chr(0x301)
    client.post(url(round_), {"cases": [cases[0].pk], "label": composed})
    response = client.post(url(round_), {"cases": [cases[1].pk], "label": decomposed})
    assert "This build label is already used in this round." in text(response)
    assert Build.objects.filter(round=round_).count() == 2


@pytest.mark.parametrize("label", ["b1", chr(0xFF22) + "1"], ids=["case", "width"])
def test_labels_differing_in_case_or_compatibility_form_are_accepted(setup, label):
    client, _, _, round_, cases = setup
    client.post(url(round_), {"cases": [cases[0].pk], "label": label})
    assert Build.objects.filter(round=round_, label=label).exists()


def test_a_label_used_in_another_round_is_accepted(setup):
    client, workspace, _, round_, cases = setup
    client.post(url(round_), {"cases": [cases[0].pk], "label": "B2"})
    other, other_cases = round_with_cases(workspace)
    client.post(url(other), {"cases": [other_cases[0].pk], "label": "B2"})
    assert Build.objects.filter(round=other, label="B2").exists()


# --- RND-5.4: the build cap ---


def test_the_tenth_build_is_created_and_the_eleventh_refused(setup):
    client, _, _, round_, cases = setup
    for number in range(2, 11):
        client.post(url(round_), {"cases": [cases[0].pk], "label": f"B{number}"})
    assert Build.objects.filter(round=round_).count() == 10
    response = client.post(url(round_), {"cases": [cases[0].pk], "label": "B11"})
    assert "This round has reached its limit of 10 builds." in text(response)
    assert Build.objects.filter(round=round_).count() == 10


# --- RND-5.5: repeated retests ---


def test_a_case_can_be_retested_twice_and_history_stays(setup):
    client, _, _, round_, cases = setup
    criteria, case_count = round_.criteria.count(), round_.cases.count()
    client.post(url(round_), {"cases": [cases[0].pk], "label": "B2"})
    client.post(url(round_), {"cases": [cases[0].pk], "label": "B3"})
    assert Build.objects.filter(cases=cases[0]).count() == 3
    assert set(Build.objects.get(round=round_, label="B1").cases.all()) == set(cases)
    assert current_build(cases[0]).label == "B3"
    assert (round_.criteria.count(), round_.cases.count()) == (criteria, case_count)
    page = text(client.get(f"/coordinator/rounds/{round_.pk}/"))
    assert all(label in page for label in ("B1", "B2", "B3"))


# --- RND-5.6: foreign cases ---


def test_a_case_of_another_round_or_workspace_or_none_is_refused(setup):
    client, workspace, _, round_, _ = setup
    _, other_cases = round_with_cases(workspace)
    other_workspace, _ = workspace_with_coordinator("hid2e")
    _, foreign_cases = round_with_cases(other_workspace)
    missing = max(Case.objects.values_list("pk", flat=True)) + 100
    for case_id in (other_cases[0].pk, foreign_cases[0].pk, missing):
        response = client.post(url(round_), {"cases": [case_id], "label": "B2"})
        assert response.status_code == 200
        assert "Choose test cases from this round." in text(response)
    assert Build.objects.filter(round=round_).count() == 1
