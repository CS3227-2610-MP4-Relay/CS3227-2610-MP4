"""Hidden acceptance suite for the agent-setups experiment (#31).

Written from issue #68 and the fixed decision sheet only, before any run. It is
copied into each candidate at evaluation time and never shown to the agents. It
drives the coordinator's round forms over HTTP, so it does not depend on how a
candidate structures its code, and checks outcomes in the database rather than
message wording.

Decision 1: refuse U+202A to U+202E and U+2066 to U+2069 in round text.
Decision 1 also allows the direction marks U+200E, U+200F and U+061C.
Decision 2: other invisible characters are not refused in this slice.
"""

import pytest
from django.db import transaction
from django.test import Client

from accounts.models import User, Workspace
from rounds import services
from rounds.models import Build, Case, CaseCriterion, Criterion, Round

CONTROLS = [*range(0x202A, 0x202F), *range(0x2066, 0x206A)]
assert len(CONTROLS) == 9

# Text that must still be accepted: direction marks, joiners, a zero-width space
# beside visible text, and ordinary non-ASCII scripts and symbols.
ALLOWED = {
    "lrm": "Login \u200eflow",
    "rlm": "Login \u200fflow",
    "alm": "Login \u061cflow",
    "zwj-zwnj": "Family \U0001f468\u200d\U0001f469 and \u200cjoin",
    "zwsp": "Zero\u200bwidth",
    "scripts": (
        "Caf\u00e9 \u2018quoted\u2019 \U0001f642 "
        "\u0645\u0631\u062d\u0628\u0627 \u05e9\u05dc\u05d5\u05dd"
    ),
}

BASE = "/coordinator/rounds"


def with_control(code):
    """Visible text with one control character inside it."""
    return f"Login {chr(code)}flow"


@pytest.fixture
def setup(db):
    """A coordinator's client and a Draft round with a linked criterion and case."""
    workspace = Workspace.objects.create(name="Demo workspace hidden01")
    user = User.objects.create_user(
        "coord-hidden01", "Synthetic16Chars", workspace=workspace, role="coordinator"
    )
    client = Client()
    client.force_login(user)
    round_ = Round.objects.create(workspace=workspace, title="Synthetic round")
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    case = Case.objects.create(
        round=round_, title="Synthetic case", steps="Steps", expected_result="Result"
    )
    CaseCriterion.objects.create(case=case, criterion=criterion)
    return client, workspace, round_, criterion, case


def published(round_):
    """Publish `round_` on build Synthetic 1.0 through the service."""
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=round_.pk)
        services.publish(locked, "Synthetic 1.0")
    round_.refresh_from_db()
    return round_


def case_data(criterion, **override):
    data = {
        "title": "Valid case",
        "steps": "Valid steps",
        "expected_result": "Valid result",
        "criteria": [criterion.pk],
    }
    data.update(override)
    return data


# --- Refusals: every round text input refuses each of the nine controls. ---


@pytest.mark.parametrize("code", CONTROLS)
def test_new_round_title_refused(setup, code):
    client, *_ = setup
    before = Round.objects.count()
    response = client.post(f"{BASE}/new/", {"title": with_control(code)})
    assert response.status_code == 200
    assert Round.objects.count() == before


@pytest.mark.parametrize("code", CONTROLS)
def test_round_retitle_refused(setup, code):
    client, _, round_, *_ = setup
    response = client.post(f"{BASE}/{round_.pk}/edit/", {"title": with_control(code)})
    round_.refresh_from_db()
    assert response.status_code == 200
    assert round_.title == "Synthetic round"


@pytest.mark.parametrize("code", CONTROLS)
def test_new_criterion_text_refused(setup, code):
    client, _, round_, *_ = setup
    response = client.post(
        f"{BASE}/{round_.pk}/criteria/new/", {"text": with_control(code)}
    )
    assert response.status_code == 200
    assert round_.criteria.count() == 1


@pytest.mark.parametrize("code", CONTROLS)
def test_criterion_edit_refused(setup, code):
    client, _, round_, criterion, _ = setup
    response = client.post(
        f"{BASE}/{round_.pk}/criteria/{criterion.pk}/edit/",
        {"text": with_control(code)},
    )
    criterion.refresh_from_db()
    assert response.status_code == 200
    assert criterion.text == "Synthetic criterion"


@pytest.mark.parametrize("field", ["title", "steps", "expected_result"])
@pytest.mark.parametrize("code", CONTROLS)
def test_new_case_field_refused(setup, code, field):
    client, _, round_, criterion, _ = setup
    data = case_data(criterion, **{field: with_control(code)})
    response = client.post(f"{BASE}/{round_.pk}/cases/new/", data)
    assert response.status_code == 200
    assert round_.cases.count() == 1


@pytest.mark.parametrize("field", ["title", "steps", "expected_result"])
@pytest.mark.parametrize("code", CONTROLS)
def test_case_edit_field_refused(setup, code, field):
    client, _, round_, criterion, case = setup
    data = case_data(criterion, **{field: with_control(code)})
    response = client.post(f"{BASE}/{round_.pk}/cases/{case.pk}/edit/", data)
    case.refresh_from_db()
    assert response.status_code == 200
    assert (case.title, case.steps, case.expected_result) == (
        "Synthetic case",
        "Steps",
        "Result",
    )


@pytest.mark.parametrize("code", CONTROLS)
def test_publish_label_refused(setup, code):
    client, _, round_, *_ = setup
    url = f"{BASE}/{round_.pk}/publish/"
    response = client.post(url, {"label": with_control(code)})
    round_.refresh_from_db()
    assert response.status_code == 200
    assert round_.state == Round.State.DRAFT
    assert Build.objects.filter(round=round_).count() == 0


@pytest.mark.parametrize("code", CONTROLS)
def test_retest_label_refused(setup, code):
    client, _, round_, _, case = setup
    published(round_)
    response = client.post(
        f"{BASE}/{round_.pk}/retest/", {"cases": [case.pk], "label": with_control(code)}
    )
    assert response.status_code == 200
    assert Build.objects.filter(round=round_).count() == 1


# --- Over-blocking: text the decisions keep allowed is still accepted. ---


@pytest.mark.parametrize("name", ALLOWED)
def test_new_round_title_accepted(setup, name):
    client, workspace, *_ = setup
    response = client.post(f"{BASE}/new/", {"title": ALLOWED[name]})
    assert response.status_code == 302
    assert Round.objects.filter(workspace=workspace, title=ALLOWED[name]).exists()


@pytest.mark.parametrize("name", ALLOWED)
def test_new_criterion_text_accepted(setup, name):
    client, _, round_, *_ = setup
    response = client.post(f"{BASE}/{round_.pk}/criteria/new/", {"text": ALLOWED[name]})
    assert response.status_code == 302
    assert round_.criteria.filter(text=ALLOWED[name]).exists()


@pytest.mark.parametrize("name", ALLOWED)
def test_new_case_steps_accepted(setup, name):
    client, _, round_, criterion, _ = setup
    data = case_data(criterion, steps=ALLOWED[name])
    response = client.post(f"{BASE}/{round_.pk}/cases/new/", data)
    assert response.status_code == 302
    assert round_.cases.filter(steps=ALLOWED[name]).exists()


@pytest.mark.parametrize("name", ALLOWED)
def test_publish_label_accepted(setup, name):
    client, _, round_, *_ = setup
    response = client.post(f"{BASE}/{round_.pk}/publish/", {"label": ALLOWED[name]})
    round_.refresh_from_db()
    assert response.status_code == 302
    assert round_.state == Round.State.OPEN
