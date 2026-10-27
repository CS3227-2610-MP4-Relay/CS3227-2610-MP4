"""RND-7: the sample draft round each new demo workspace starts with."""

import re

import pytest
from django.db import transaction
from django.test import Client

from accounts import demo
from accounts.models import Workspace
from rounds import services
from rounds.forms import CaseForm, CriterionForm, RoundForm
from rounds.models import CaseCriterion, Round

from .conftest import LIMIT_MESSAGE, NEW, NOT_FOUND, detail, page, signed_in

pytestmark = pytest.mark.django_db

TITLE = "Sample round"
PUBLISHED = "Round published."
CLOSED = "Round closed."
HOME_ITEM = r'<li><a href="([^"]+)"><span dir="auto">([^<]+)</span></a> \((\w+)\)</li>'


def new_workspace():
    """A demo workspace made by the same function the `/demo/` view calls."""
    with transaction.atomic():
        workspace, _ = demo.create_demo_workspace(demo.generate_passwords())
    return workspace


def coordinator_of(workspace):
    return workspace.accounts.get(role="coordinator")


def sample_of(workspace):
    return Round.objects.get(workspace=workspace)


def content(round_):
    """A round's text, criteria, cases and links, without IDs."""
    criteria = list(round_.criteria.order_by("pk"))
    position = {criterion.pk: index for index, criterion in enumerate(criteria)}
    cases = [
        (
            case.title,
            case.steps,
            case.expected_result,
            sorted(position[link.criterion_id] for link in case.links.all()),
        )
        for case in round_.cases.order_by("pk")
    ]
    return round_.title, [criterion.text for criterion in criteria], cases


def snapshot(round_):
    """Everything about a round that editing, publishing or closing changes."""
    round_.refresh_from_db()
    links = CaseCriterion.objects.filter(case__round=round_)
    return {
        "round": (round_.title, round_.state, round_.published_at, round_.closed_at),
        "criteria": list(round_.criteria.order_by("pk").values_list("pk", "text")),
        "cases": list(
            round_.cases.order_by("pk").values_list(
                "pk", "title", "steps", "expected_result"
            )
        ),
        "links": sorted(links.values_list("case_id", "criterion_id")),
        "builds": list(round_.builds.order_by("pk").values_list("pk", "label")),
    }


@pytest.mark.ac("RND-7.1")
def test_new_workspace_has_one_draft_sample_round_of_3_criteria_and_4_cases():
    workspace = new_workspace()
    assert Round.objects.filter(workspace=workspace).count() == 1
    round_ = sample_of(workspace)
    assert round_.title == TITLE
    assert round_.state == Round.State.DRAFT
    assert round_.published_at is None and round_.closed_at is None
    assert round_.criteria.count() == 3
    assert round_.cases.count() == 4
    assert not round_.builds.exists()
    for case in round_.cases.all():
        assert case.links.exists(), case.title
        assert {link.criterion.round_id for link in case.links.all()} == {round_.pk}
    for criterion in round_.criteria.all():
        assert criterion.links.exists(), criterion.text


@pytest.mark.ac("RND-7.1")
def test_sample_text_is_synthetic_ascii_and_passes_the_round_forms():
    round_ = sample_of(new_workspace())
    texts = [round_.title]
    assert RoundForm({"title": round_.title}).is_valid()
    for criterion in round_.criteria.all():
        form = CriterionForm(round_, {"text": criterion.text})
        assert form.is_valid(), form.errors
        assert form.cleaned_data["text"] == criterion.text
        texts.append(criterion.text)
    for case in round_.cases.all():
        data = {
            "title": case.title,
            "steps": case.steps,
            "expected_result": case.expected_result,
            "criteria": [link.criterion_id for link in case.links.all()],
        }
        form = CaseForm(round_, data)
        assert form.is_valid(), form.errors
        for field in ("title", "steps", "expected_result"):
            assert form.cleaned_data[field] == data[field]
            texts.append(data[field])
    for text in texts:
        assert text.isascii(), text
        assert "\r" not in text and "\x00" not in text


@pytest.mark.ac("RND-7.1")
def test_sample_text_is_the_same_fixed_text_in_every_workspace():
    first, second = sample_of(new_workspace()), sample_of(new_workspace())
    assert first.pk != second.pk
    assert content(first) == content(second)
    assert len(set(content(first)[1])) == 3
    assert len({case[0] for case in content(first)[2]}) == 4


@pytest.mark.ac("RND-7.1")
def test_demo_route_workspace_lists_the_sample_round_on_coordinator_home():
    assert Client().post("/demo/").status_code == 200
    workspace = Workspace.objects.get()
    round_ = sample_of(workspace)
    html = page(signed_in(coordinator_of(workspace)).get("/coordinator/"))
    assert re.findall(HOME_ITEM, html) == [(detail(round_.pk), TITLE, "Draft")]
    assert "No rounds yet." not in html


@pytest.mark.ac("RND-7.2")
def test_sample_round_publishes_with_only_a_build_label():
    workspace = new_workspace()
    round_ = sample_of(workspace)
    client = signed_in(coordinator_of(workspace))
    response = client.post(
        f"{detail(round_.pk)}publish/", {"label": "Sample 1.0"}, follow=True
    )
    assert PUBLISHED in page(response)
    round_.refresh_from_db()
    assert round_.state == Round.State.OPEN
    build = round_.builds.get()
    assert build.label == "Sample 1.0"
    assert set(build.cases.values_list("pk", flat=True)) == set(
        round_.cases.values_list("pk", flat=True)
    )


@pytest.mark.ac("RND-7.2")
def test_sample_round_can_be_edited_like_any_draft_round_then_published():
    workspace = new_workspace()
    round_ = sample_of(workspace)
    client = signed_in(coordinator_of(workspace))
    base = detail(round_.pk)
    criterion = round_.criteria.order_by("pk").first()
    case = round_.cases.order_by("pk").last()

    assert client.post(f"{base}edit/", {"title": "Synthetic edited"}).status_code == 302
    edited = client.post(
        f"{base}criteria/{criterion.pk}/edit/", {"text": "Synthetic criterion"}
    )
    assert edited.status_code == 302
    added = client.post(
        f"{base}cases/new/",
        {
            "title": "Synthetic extra case",
            "steps": "Synthetic steps",
            "expected_result": "Synthetic result",
            "criteria": [criterion.pk],
        },
    )
    assert added.status_code == 302
    assert client.post(f"{base}cases/{case.pk}/delete/").status_code == 302

    round_.refresh_from_db()
    criterion.refresh_from_db()
    assert round_.title == "Synthetic edited"
    assert criterion.text == "Synthetic criterion"
    assert round_.cases.count() == 4
    assert round_.cases.filter(title="Synthetic extra case").exists()
    assert not round_.cases.filter(pk=case.pk).exists()
    published = client.post(f"{base}publish/", {"label": "Sample 2.0"}, follow=True)
    assert PUBLISHED in page(published)
    assert round_.builds.get().cases.count() == 4


@pytest.mark.ac("RND-7.3")
def test_sample_round_counts_toward_the_20_round_limit():
    workspace = new_workspace()
    client = signed_in(coordinator_of(workspace))
    for number in range(1, 19):
        services.create_round(workspace, f"Synthetic round {number}")
    assert Round.objects.filter(workspace=workspace).count() == 19
    # The 19th more round, the workspace's 20th, is still created.
    assert client.post(NEW, {"title": "Synthetic round 19"}).status_code == 302
    assert Round.objects.filter(workspace=workspace).count() == 20
    response = client.post(NEW, {"title": "Synthetic round 20"})
    assert response.status_code == 200
    assert LIMIT_MESSAGE in page(response)
    assert Round.objects.filter(workspace=workspace).count() == 20


@pytest.mark.ac("RND-7.4")
def test_changing_one_sample_round_leaves_another_workspaces_unchanged():
    own_workspace, other_workspace = new_workspace(), new_workspace()
    own, other = sample_of(own_workspace), sample_of(other_workspace)
    before = snapshot(other)
    client = signed_in(coordinator_of(own_workspace))
    base = detail(own.pk)
    criterion = own.criteria.order_by("pk").first()

    client.post(f"{base}edit/", {"title": "Synthetic edited"})
    client.post(f"{base}criteria/{criterion.pk}/edit/", {"text": "Synthetic text"})
    assert PUBLISHED in page(
        client.post(f"{base}publish/", {"label": "Sample 1.0"}, follow=True)
    )
    assert CLOSED in page(client.post(f"{base}close/", follow=True))

    assert snapshot(own)["round"][:2] == ("Synthetic edited", Round.State.CLOSED)
    assert snapshot(other) == before
    assert other.title == TITLE and other.state == Round.State.DRAFT


@pytest.mark.ac("RND-7.4")
def test_another_workspaces_sample_round_is_not_found():
    own_workspace, other_workspace = new_workspace(), new_workspace()
    own, other = sample_of(own_workspace), sample_of(other_workspace)
    before = snapshot(other)
    client = signed_in(coordinator_of(own_workspace))
    other_criterion = other.criteria.order_by("pk").first()
    requests = [
        client.get(detail(other.pk)),
        client.post(f"{detail(other.pk)}edit/", {"title": "Synthetic taken"}),
        client.post(f"{detail(other.pk)}publish/", {"label": "Sample 1.0"}),
        # Another workspace's criterion under this workspace's own sample round.
        client.post(
            f"{detail(own.pk)}criteria/{other_criterion.pk}/edit/",
            {"text": "Synthetic taken"},
        ),
    ]
    for response in requests:
        assert response.status_code == 404
        assert NOT_FOUND in page(response)
    assert snapshot(other) == before
