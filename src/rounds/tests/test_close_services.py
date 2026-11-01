"""Service and data-model tests for closing a round (RND-6)."""

import pytest

from accounts.models import Workspace
from rounds import services
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import locked

pytestmark = pytest.mark.django_db


@pytest.fixture
def round_():
    workspace = Workspace.objects.create(name="Demo workspace rnd60001")
    return Round.objects.create(workspace=workspace, title="Synthetic round")


def published(round_, cases=2):
    """Give `round_` a criterion and `cases` linked cases, then publish it."""
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {n}",
            steps="Open the synthetic page.",
            expected_result="The synthetic page opens.",
        )
        CaseCriterion.objects.create(case=case, criterion=criterion)
    services.publish(locked(round_), "Synthetic build 1.0")
    round_.refresh_from_db()
    return round_


def snapshot(round_):
    """Everything RND-2 and RND-3 store for a round."""
    return (
        list(Criterion.objects.filter(round=round_).values()),
        list(Case.objects.filter(round=round_).values()),
        list(CaseCriterion.objects.filter(case__round=round_).values()),
        list(Build.objects.filter(round=round_).values()),
        list(BuildCase.objects.filter(build__round=round_).values()),
    )


@pytest.mark.ac("RND-6.1")
def test_close_makes_an_open_round_closed_and_keeps_its_records(round_):
    published(round_)
    before = snapshot(round_)
    published_at = round_.published_at
    services.close(locked(round_))
    round_.refresh_from_db()
    assert round_.state == Round.State.CLOSED
    assert round_.closed_at is not None
    assert round_.closed_at >= published_at
    assert round_.published_at == published_at
    assert round_.title == "Synthetic round"
    assert snapshot(round_) == before


@pytest.mark.ac("RND-6.2")
def test_close_needs_no_precondition_for_untested_cases(round_):
    # No results exist yet (RES), so every case is untested.
    published(round_, cases=1)
    services.close(locked(round_))
    round_.refresh_from_db()
    assert round_.state == Round.State.CLOSED


def test_closing_time_is_empty_until_closing(round_):
    assert round_.closed_at is None
    published(round_)
    assert round_.closed_at is None


@pytest.mark.ac("RND-6.3")
@pytest.mark.parametrize("state", [Round.State.DRAFT, Round.State.CLOSED])
def test_close_refuses_a_round_that_is_not_open(round_, state):
    published(round_)
    if state == Round.State.DRAFT:
        draft = Round.objects.create(workspace=round_.workspace, title="Synthetic")
        target = draft
    else:
        services.close(locked(round_))
        target = round_
    target.refresh_from_db()
    before = (target.state, target.closed_at, snapshot(target))
    with pytest.raises(services.RoundNotOpen) as refused:
        services.close(locked(target))
    assert str(refused.value) == "The round is not Open."
    target.refresh_from_db()
    assert (target.state, target.closed_at, snapshot(target)) == before
