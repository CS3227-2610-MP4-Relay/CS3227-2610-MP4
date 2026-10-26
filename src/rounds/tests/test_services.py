import pytest
from django.db import DataError, IntegrityError, transaction

from accounts.models import User, Workspace
from accounts.workspaces import workspace_records
from rounds import services
from rounds.models import Round

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    return Workspace.objects.create(name="Demo workspace rnd00001")


@pytest.fixture
def other_workspace():
    return Workspace.objects.create(name="Demo workspace rnd00002")


def fill(workspace, count):
    Round.objects.bulk_create(
        Round(workspace=workspace, title=f"Synthetic round {n}") for n in range(count)
    )


@pytest.mark.ac("RND-1.1")
def test_create_round_makes_a_draft_round_in_the_given_workspace(workspace):
    created = services.create_round(workspace, "Synthetic round")
    created.refresh_from_db()
    assert created.workspace == workspace
    assert created.title == "Synthetic round"
    assert created.state == Round.State.DRAFT
    assert created.created_at is not None


def test_state_must_be_draft_open_or_closed(workspace):
    for state in ("draft", "open", "closed"):
        Round.objects.create(workspace=workspace, title="Synthetic", state=state)
    with pytest.raises(IntegrityError), transaction.atomic():
        Round.objects.create(workspace=workspace, title="Synthetic", state="archived")


def test_title_holds_at_most_120_characters(workspace):
    Round.objects.create(workspace=workspace, title="a" * 120)
    with pytest.raises(DataError), transaction.atomic():
        Round.objects.create(workspace=workspace, title="a" * 121)


@pytest.mark.ac("RND-1.1")
def test_rounds_are_listed_newest_first(workspace):
    first = services.create_round(workspace, "Synthetic first")
    second = services.create_round(workspace, "Synthetic second")
    Round.objects.filter(pk=second.pk).update(created_at=first.created_at)
    third = services.create_round(workspace, "Synthetic third")
    assert list(Round.objects.filter(workspace=workspace)) == [third, second, first]


@pytest.mark.ac("RND-1.4")
def test_twentieth_round_is_created_and_twenty_first_refused(workspace):
    fill(workspace, 19)
    services.create_round(workspace, "Synthetic twentieth")
    assert Round.objects.filter(workspace=workspace).count() == 20
    with pytest.raises(services.RoundLimitReached) as refused:
        services.create_round(workspace, "Synthetic twenty-first")
    assert str(refused.value) == "This workspace has reached its limit of 20 rounds."
    assert Round.objects.filter(workspace=workspace).count() == 20
    assert not Round.objects.filter(title="Synthetic twenty-first").exists()


@pytest.mark.ac("RND-1.4")
def test_other_workspaces_rounds_do_not_count(workspace, other_workspace):
    fill(other_workspace, 20)
    fill(workspace, 19)
    services.create_round(workspace, "Synthetic twentieth")
    assert Round.objects.filter(workspace=workspace).count() == 20


@pytest.mark.ac("ACC-2.4")
def test_workspace_records_returns_only_the_users_rounds(workspace, other_workspace):
    own = services.create_round(workspace, "Synthetic own")
    services.create_round(other_workspace, "Synthetic other")
    coordinator = User.objects.create_user(
        "coord-rnd00001", "Synthetic16Chars", workspace=workspace, role="coordinator"
    )
    assert list(workspace_records(coordinator, Round)) == [own]
