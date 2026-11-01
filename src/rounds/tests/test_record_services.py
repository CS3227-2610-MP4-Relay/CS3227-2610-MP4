"""Service-level tests for criteria, cases and their links (RND-2)."""

import pytest
from django.db import DataError, IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import Workspace
from rounds import services
from rounds.models import Case, CaseCriterion, Criterion, Round

from .conftest import locked

pytestmark = pytest.mark.django_db

CASE_FIELDS = {
    "title": "Synthetic case",
    "steps": "Open the synthetic page.",
    "expected_result": "The synthetic page opens.",
}
FOREIGN = "Choose criteria from this round."
NO_LINK = "Link at least one acceptance criterion."
LINKED = "This criterion is linked to a test case. Unlink it first."


@pytest.fixture
def workspace():
    return Workspace.objects.create(name="Demo workspace rnd20001")


@pytest.fixture
def round_(workspace):
    return Round.objects.create(workspace=workspace, title="Synthetic round")


@pytest.fixture
def sibling(workspace):
    """Another round in the same workspace."""
    return Round.objects.create(workspace=workspace, title="Synthetic sibling")


@pytest.fixture
def foreign_round():
    other = Workspace.objects.create(name="Demo workspace rnd20002")
    return Round.objects.create(workspace=other, title="Synthetic foreign")


def criteria(round_, count):
    return [
        Criterion.objects.create(round=round_, text=f"Synthetic criterion {n}")
        for n in range(count)
    ]


def make_case(round_, linked, title="Synthetic case"):
    case = Case.objects.create(round=round_, **{**CASE_FIELDS, "title": title})
    for criterion in linked:
        CaseCriterion.objects.create(case=case, criterion=criterion)
    return case


def snapshot(round_):
    """Everything RND-2 stores for a round, to show a refusal changed nothing."""
    return (
        list(Criterion.objects.filter(round=round_).values()),
        list(Case.objects.filter(round=round_).values()),
        list(CaseCriterion.objects.filter(case__round=round_).values()),
    )


@pytest.mark.ac("RND-2.1")
def test_add_criterion_adds_it_to_the_round_in_creation_order(round_):
    first = services.add_criterion(locked(round_), "Synthetic first")
    second = services.add_criterion(locked(round_), "Synthetic second")
    assert first.round == round_
    assert list(round_.criteria.all()) == [first, second]
    assert Criterion.objects.get(pk=first.pk).text == "Synthetic first"


@pytest.mark.ac("RND-2.2")
def test_add_case_links_the_chosen_criteria(round_):
    one, two, three = criteria(round_, 3)
    case = services.add_case(locked(round_), CASE_FIELDS, [three.pk, one.pk])
    case.refresh_from_db()
    assert case.round == round_
    assert (case.title, case.steps, case.expected_result) == tuple(CASE_FIELDS.values())
    assert list(case.criteria.all()) == [one, three]
    later = services.add_case(locked(round_), CASE_FIELDS, [two.pk])
    assert list(round_.cases.all()) == [case, later]


@pytest.mark.ac("RND-2.7")
def test_a_repeated_criterion_id_counts_once(round_):
    (only,) = criteria(round_, 1)
    case = services.add_case(locked(round_), CASE_FIELDS, [only.pk, only.pk])
    assert CaseCriterion.objects.filter(case=case).count() == 1


@pytest.mark.ac("RND-2.3")
def test_save_case_changes_fields_and_replaces_links(round_):
    one, two, three = criteria(round_, 3)
    case = make_case(round_, [one, two])
    fields = {"title": "Edited", "steps": "Edited steps", "expected_result": "Done"}
    services.save_case(case, fields, [three.pk, two.pk])
    case.refresh_from_db()
    assert (case.title, case.steps, case.expected_result) == (
        "Edited",
        "Edited steps",
        "Done",
    )
    assert list(case.criteria.all()) == [two, three]
    assert CaseCriterion.objects.filter(case=case).count() == 2


@pytest.mark.ac("RND-2.3")
def test_delete_case_removes_its_links_and_keeps_its_criteria(round_):
    one, two = criteria(round_, 2)
    case = make_case(round_, [one, two])
    kept = make_case(round_, [one], title="Synthetic kept")
    services.delete_case(case)
    assert not Case.objects.filter(pk=case.pk).exists()
    assert not CaseCriterion.objects.filter(case_id=case.pk).exists()
    assert list(round_.criteria.all()) == [one, two]
    assert list(kept.criteria.all()) == [one]


@pytest.mark.ac("RND-2.3")
def test_delete_criterion_removes_an_unlinked_criterion(round_):
    one, two = criteria(round_, 2)
    make_case(round_, [two])
    services.delete_criterion(one)
    assert list(round_.criteria.all()) == [two]


@pytest.mark.ac("RND-2.6")
def test_delete_criterion_refuses_a_linked_criterion(round_):
    one, two = criteria(round_, 2)
    make_case(round_, [one, two])
    before = snapshot(round_)
    with pytest.raises(services.Refused) as refused:
        services.delete_criterion(one)
    assert str(refused.value) == LINKED
    assert refused.value.field is None
    assert snapshot(round_) == before


@pytest.mark.ac("RND-2.6")
def test_a_case_needs_at_least_one_criterion(round_):
    (one,) = criteria(round_, 1)
    case = make_case(round_, [one])
    before = snapshot(round_)
    for write in (
        lambda: services.add_case(locked(round_), CASE_FIELDS, []),
        lambda: services.save_case(case, {"title": "Edited"}, []),
    ):
        with pytest.raises(services.Refused) as refused:
            write()
        assert str(refused.value) == NO_LINK
        assert refused.value.field == "criteria"
        assert snapshot(round_) == before


@pytest.mark.ac("RND-2.7")
@pytest.mark.parametrize("source", ["sibling", "foreign_round", "missing"])
def test_criteria_from_elsewhere_are_refused(request, round_, source):
    (own,) = criteria(round_, 1)
    if source == "missing":
        wrong = Criterion.objects.order_by("-pk").first().pk + 1000
    else:
        wrong = criteria(request.getfixturevalue(source), 1)[0].pk
    case = make_case(round_, [own])
    before = snapshot(round_)
    for write in (
        lambda: services.add_case(locked(round_), CASE_FIELDS, [own.pk, wrong]),
        lambda: services.save_case(case, {"title": "Edited"}, [own.pk, wrong]),
    ):
        with pytest.raises(services.Refused) as refused:
            write()
        assert str(refused.value) == FOREIGN
        assert refused.value.field == "criteria"
        assert snapshot(round_) == before
    assert not CaseCriterion.objects.filter(criterion_id=wrong).exists()


@pytest.mark.ac("RND-2.5")
def test_twentieth_criterion_is_added_and_twenty_first_refused(round_, sibling):
    criteria(sibling, 20)
    criteria(round_, 19)
    services.add_criterion(locked(round_), "Synthetic twentieth")
    assert round_.criteria.count() == 20
    with pytest.raises(services.Refused) as refused:
        services.add_criterion(locked(round_), "Synthetic twenty-first")
    assert str(refused.value) == (
        "This round has reached its limit of 20 acceptance criteria."
    )
    assert refused.value.field == "text"
    assert round_.criteria.count() == 20
    assert not Criterion.objects.filter(text="Synthetic twenty-first").exists()


@pytest.mark.ac("RND-2.5")
def test_thirtieth_case_is_added_and_thirty_first_refused(round_, sibling):
    (other,) = criteria(sibling, 1)
    for n in range(30):
        make_case(sibling, [other], title=f"Synthetic sibling case {n}")
    (own,) = criteria(round_, 1)
    for n in range(29):
        make_case(round_, [own], title=f"Synthetic case {n}")
    services.add_case(locked(round_), CASE_FIELDS, [own.pk])
    assert round_.cases.count() == 30
    before = snapshot(round_)
    with pytest.raises(services.Refused) as refused:
        services.add_case(locked(round_), CASE_FIELDS, [own.pk])
    assert str(refused.value) == "This round has reached its limit of 30 test cases."
    assert refused.value.field == "title"
    assert snapshot(round_) == before


@pytest.mark.parametrize(
    ("model", "field", "limit"),
    [
        (Criterion, "text", 500),
        (Case, "title", 120),
        (Case, "steps", 2000),
        (Case, "expected_result", 1000),
    ],
)
def test_text_fields_hold_their_maximum_in_the_database(round_, model, field, limit):
    values = {**CASE_FIELDS} if model is Case else {"text": "Synthetic"}
    model.objects.create(round=round_, **{**values, field: "a" * limit})
    with pytest.raises(DataError), transaction.atomic():
        model.objects.create(round=round_, **{**values, field: "a" * (limit + 1)})


def test_a_case_links_a_criterion_at_most_once(round_):
    (one,) = criteria(round_, 1)
    case = make_case(round_, [one])
    with pytest.raises(IntegrityError), transaction.atomic():
        CaseCriterion.objects.create(case=case, criterion=one)


def test_foreign_keys_protect_linked_records(round_):
    (one,) = criteria(round_, 1)
    case = make_case(round_, [one])
    for record in (one, case, round_):
        with pytest.raises(ProtectedError), transaction.atomic():
            record.delete()
    assert snapshot(round_)[2]


@pytest.mark.ac("RND-2.3")
def test_save_criterion_changes_only_its_text(round_):
    one, two = criteria(round_, 2)
    services.save_criterion(one, "Synthetic edited")
    assert Criterion.objects.get(pk=one.pk).text == "Synthetic edited"
    assert Criterion.objects.get(pk=two.pk).text == "Synthetic criterion 1"
