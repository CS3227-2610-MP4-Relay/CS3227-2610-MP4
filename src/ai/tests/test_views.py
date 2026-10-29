"""End-to-end checks for the transient RND-8 drafting pages."""

import json
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from ai.fakes import FakeProvider
from ai.gateway import Failed, Refused, Success
from rounds.models import Case, Criterion, Round
from rounds.tests.conftest import csrf_token, signed_in


@pytest.fixture
def round_(workspace):
    return Round.objects.create(workspace=workspace, title="Synthetic round")


@pytest.fixture
def criteria(round_):
    return [
        Criterion.objects.create(round=round_, text="Synthetic criterion one"),
        Criterion.objects.create(round=round_, text="Synthetic criterion two"),
    ]


def reply(*drafts):
    return json.dumps({"drafts": list(drafts)})


def one(**changes):
    value = {
        "title": "Synthetic draft title",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": ["C1"],
    }
    value.update(changes)
    return value


def use(coord_client, round_, criteria=None, **fields):
    data = {
        "title": fields.get("title", "Synthetic draft title"),
        "steps": fields.get("steps", "Synthetic steps"),
        "expected_result": fields.get("expected_result", "Synthetic result"),
        "criteria": [item.pk for item in (criteria or [])],
    }
    return coord_client.post(reverse("ai:use-draft", args=[round_.pk]), data)


def test_round_page_links_to_drafting_only_while_draft(coord_client, round_, criteria):
    page = coord_client.get(round_.get_absolute_url()).content.decode()
    assert "Draft test cases with AI" in page
    round_.state = Round.State.OPEN
    round_.save(update_fields=["state"])
    assert (
        "Draft test cases with AI"
        not in coord_client.get(round_.get_absolute_url()).content.decode()
    )


def test_get_shows_selection_without_calling(
    coord_client, round_, criteria, django_capture_on_commit_callbacks
):
    with mock.patch("ai.views.gateway.complete") as complete:
        response = coord_client.get(reverse("ai:draft", args=[round_.pk]))
    assert response.status_code == 200
    assert "Acceptance criteria to draft from" in response.content.decode()
    complete.assert_not_called()


def test_success_renders_cleaned_drafts_and_sends_only_selected(
    coord_client, round_, criteria
):
    fake = FakeProvider(
        Success(reply(one(title="Synthetic\u202a title", criteria=["C1"])))
    )
    second = Criterion.objects.create(round=round_, text="Synthetic unselected")
    with mock.patch("ai.views.gateway.complete", return_value=fake.result) as complete:
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]),
            {"criteria": [criteria[0].pk]},
        )
    assert response.status_code == 200
    assert "Synthetic title" in response.content.decode()
    assert "\u202a" not in response.content.decode()
    sent = complete.call_args.args[2]
    assert "Synthetic criterion one" in sent
    assert second.text not in sent


def test_selection_is_validated_and_foreign_ids_are_refused(coord_client, workspace):
    other = Round.objects.create(workspace=workspace, title="Synthetic other")
    foreign = Criterion.objects.create(round=other, text="Synthetic foreign")
    make = Round.objects.create(workspace=workspace, title="Synthetic target")
    with mock.patch("ai.views.gateway.complete") as complete:
        response = coord_client.post(
            reverse("ai:draft", args=[make.pk]), {"criteria": [foreign.pk]}
        )
    assert "Choose criteria from this round." in response.content.decode()
    complete.assert_not_called()


@pytest.mark.parametrize("count", [0, 6])
def test_selection_count_is_one_to_five(coord_client, round_, count):
    ids = [
        Criterion.objects.create(round=round_, text=f"Synthetic {index}").pk
        for index in range(count)
    ]
    with mock.patch("ai.views.gateway.complete") as complete:
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": ids}
        )
    assert "Select 1 to 5 acceptance criteria." in response.content.decode()
    complete.assert_not_called()


def test_case_cap_is_checked_before_ai(coord_client, round_, criteria):
    Case.objects.bulk_create(
        [
            Case(
                round=round_,
                title=f"Synthetic {index}",
                steps="s",
                expected_result="r",
            )
            for index in range(30)
        ]
    )
    with mock.patch("ai.views.gateway.complete") as complete:
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": [criteria[0].pk]}
        )
    assert (
        "This round has reached its limit of 30 test cases."
        in response.content.decode()
    )
    complete.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        Refused("provider-refused"),
        Failed("timeout"),
        Failed("invalid-response"),
    ],
)
def test_gateway_failures_show_fixed_message_and_keep_selection(
    coord_client, round_, criteria, result
):
    with mock.patch("ai.views.gateway.complete", return_value=result):
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": [criteria[0].pk]}
        )
    page = response.content.decode()
    assert response.status_code == 200
    assert "Drafting is unavailable right now." in page
    assert f'value="{criteria[0].pk}" checked' in page or "checked" in page
    assert not Case.objects.exists()


def test_invalid_reply_is_rejected_whole(coord_client, round_, criteria):
    fake = FakeProvider(Success(reply(one(extra="state"))))
    with mock.patch("ai.views.gateway.complete", return_value=fake.result):
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": [criteria[0].pk]}
        )
    assert "Drafting is unavailable right now." in response.content.decode()
    assert "Synthetic draft title" not in response.content.decode()


def test_empty_reply_shows_no_drafts_message(coord_client, round_, criteria):
    with mock.patch("ai.views.gateway.complete", return_value=Success(reply())):
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": [criteria[0].pk]}
        )
    assert (
        "No test cases were suggested for these criteria." in response.content.decode()
    )


def test_all_empty_criteria_make_no_call(coord_client, round_):
    blank = Criterion.objects.create(round=round_, text="\u3164")
    with mock.patch("ai.views.gateway.complete") as complete:
        response = coord_client.post(
            reverse("ai:draft", args=[round_.pk]), {"criteria": [blank.pk]}
        )
    assert (
        "No test cases were suggested for these criteria." in response.content.decode()
    )
    complete.assert_not_called()


def test_use_draft_prefills_without_saving(coord_client, round_, criteria):
    response = use(coord_client, round_, criteria)
    page = response.content.decode()
    assert response.status_code == 200
    assert "Pre-filled from an AI draft." in page
    assert "Synthetic draft title" in page
    assert not Case.objects.exists()


def test_use_draft_submits_to_the_normal_case_route(coord_client, round_, criteria):
    page = use(coord_client, round_, criteria).content.decode()
    assert f'action="{reverse("rounds:case-new", args=[round_.pk])}"' in page


def test_foreign_selection_with_five_valid_criteria_shows_only_foreign_message(
    coord_client, workspace, round_, criteria
):
    other = Round.objects.create(workspace=workspace, title="Synthetic other")
    foreign = Criterion.objects.create(round=other, text="Synthetic foreign")
    ids = [item.pk for item in criteria]
    ids += [Criterion.objects.create(round=round_, text=f"X{i}").pk for i in range(3)]
    ids.append(foreign.pk)
    response = coord_client.post(
        reverse("ai:draft", args=[round_.pk]), {"criteria": ids}
    )
    page = response.content.decode()
    assert "Choose criteria from this round." in page
    assert "Only their text is sent" in page


def test_use_draft_cleans_text_and_ignores_foreign_ids(
    coord_client, workspace, round_, criteria
):
    other = Round.objects.create(workspace=workspace, title="Synthetic other")
    foreign = Criterion.objects.create(round=other, text="Synthetic foreign")
    response = use(
        coord_client,
        round_,
        criteria,
        title="Synthetic\u202a title\nnext",
        steps="Synthetic\r\nsteps",
    )
    form = response.context["form"]
    assert "\u202a" not in response.content.decode()
    assert form["steps"].value() == "Synthetic\nsteps"
    assert form["title"].value() == "Synthetic title next"
    assert not Case.objects.filter(criteria=foreign).exists()


def test_use_draft_requires_coordinator(round_, criteria, tester):
    response = signed_in(tester).post(
        reverse("ai:use-draft", args=[round_.pk]),
        {
            "title": "x",
            "steps": "y",
            "expected_result": "z",
            "criteria": [criteria[0].pk],
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize("state", [Round.State.OPEN, Round.State.CLOSED])
def test_drafting_pages_get_409_outside_draft(coord_client, round_, criteria, state):
    round_.state = state
    round_.save(update_fields=["state"])
    assert coord_client.get(reverse("ai:draft", args=[round_.pk])).status_code == 409
    assert use(coord_client, round_, criteria).status_code == 409


def test_foreign_origin_and_missing_token_are_refused(coord_client, round_, criteria):
    client = Client(enforce_csrf_checks=True)
    client.force_login(criteria[0].round.workspace.accounts.get(role="coordinator"))
    response = client.post(
        reverse("ai:draft", args=[round_.pk]),
        {"criteria": [criteria[0].pk]},
        HTTP_ORIGIN="https://evil.example",
        HTTP_X_CSRFTOKEN=csrf_token(coord_client),
    )
    assert response.status_code == 403
