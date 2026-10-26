"""Service and form tests for requesting a retest (RND-5)."""

import pytest

from accounts.models import Workspace
from rounds import services
from rounds.forms import RetestForm
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

pytestmark = pytest.mark.django_db

NO_CASE = "Select at least one test case."
FOREIGN = "Choose test cases from this round."
DUPLICATE = "This build label is already used in this round."
CAP = "This round has reached its limit of 10 builds."
NOT_OPEN = "The round is not Open."
LABEL_LIMIT = "Enter 1 to 100 characters."
ZERO_WIDTH_SPACE = chr(0x200B)
COMBINING_ACUTE = chr(0x0301)
E_ACUTE = chr(0x00E9)
FULLWIDTH_ONE = chr(0xFF11)
SECRET = "Synthetic label kept out of messages"


@pytest.fixture
def workspace():
    return Workspace.objects.create(name="Demo workspace rnd50001")


def new_round(workspace, title="Synthetic round"):
    return Round.objects.create(workspace=workspace, title=title)


def fill(round_, cases=3):
    """Give `round_` a criterion and `cases` cases linked to it."""
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    made = []
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {n}",
            steps="Open the synthetic page.",
            expected_result="The synthetic page opens.",
        )
        CaseCriterion.objects.create(case=case, criterion=criterion)
        made.append(case)
    return made


def locked(round_):
    """Lock the round row, as the view does before calling the service."""
    return Round.objects.select_for_update().get(pk=round_.pk)


def published(workspace, cases=3, title="Synthetic round"):
    """A round with `cases` cases, published on "Synthetic build 1.0"."""
    round_ = new_round(workspace, title)
    made = fill(round_, cases)
    services.publish(locked(round_), "Synthetic build 1.0")
    round_.refresh_from_db()
    return round_, made


@pytest.fixture
def open_round(workspace):
    return published(workspace)


def retest(round_, label, cases):
    return services.request_retest(locked(round_), label, [c.pk for c in cases])


def current_build(case):
    """The newest build covering `case` (RND-3)."""
    return case.builds.order_by("-id").first()


def stored(round_):
    """Everything RND-2 and RND-3 store for a round."""
    return (
        list(Criterion.objects.filter(round=round_).values()),
        list(Case.objects.filter(round=round_).values()),
        list(CaseCriterion.objects.filter(case__round=round_).values()),
        list(Build.objects.filter(round=round_).values()),
        list(BuildCase.objects.filter(build__round=round_).values()),
    )


def refused(round_, label, case_ids, message, field):
    """Assert the service refuses with `message` and writes nothing."""
    before = stored(round_)
    with pytest.raises(services.Refused) as caught:
        services.request_retest(locked(round_), label, case_ids)
    assert str(caught.value) == message
    assert caught.value.field == field
    assert label not in repr(caught.value)
    assert stored(round_) == before


@pytest.mark.ac("RND-5.1")
def test_a_retest_covers_exactly_the_selected_cases(open_round):
    round_, (one, two, three) = open_round
    first = current_build(one)
    made = retest(round_, "Synthetic build 1.1", [one, three])
    assert made.round == round_ and made.label == "Synthetic build 1.1"
    assert made.key == "Synthetic build 1.1"
    assert set(made.cases.all()) == {one, three}
    assert current_build(one) == current_build(three) == made
    assert current_build(two) == first
    assert list(round_.builds.all()) == [first, made]


@pytest.mark.ac("RND-5.1")
def test_a_case_selected_twice_is_covered_once(open_round):
    round_, (one, two, _) = open_round
    made = services.request_retest(
        locked(round_), "Synthetic build 1.1", [one.pk, two.pk, one.pk]
    )
    assert BuildCase.objects.filter(build=made).count() == 2


@pytest.mark.ac("RND-5.2")
def test_selecting_no_case_is_refused_by_the_service(open_round):
    round_, _ = open_round
    refused(round_, "Synthetic build 1.1", [], NO_CASE, "cases")


@pytest.mark.ac("RND-5.3")
@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Synthetic build 1.0", "Synthetic build 1.0"),
        ("Synthetic build 1.0", "Synthetic build" + ZERO_WIDTH_SPACE + " 1.0"),
        ("caf" + E_ACUTE, "caf" + "e" + COMBINING_ACUTE),
        ("caf" + "e" + COMBINING_ACUTE, "caf" + E_ACUTE),
    ],
    ids=["equal", "format-character", "decomposed-after-composed", "composed-after"],
)
def test_a_label_with_a_used_key_is_refused(workspace, first, second):
    round_ = new_round(workspace)
    cases = fill(round_, 2)
    services.publish(locked(round_), first)
    refused(round_, second, [cases[0].pk], DUPLICATE, "label")


@pytest.mark.ac("RND-5.3")
def test_the_duplicate_refusal_names_no_label(workspace):
    round_ = new_round(workspace)
    (case,) = fill(round_, 1)
    services.publish(locked(round_), SECRET)
    with pytest.raises(services.Refused) as caught:
        retest(round_, SECRET, [case])
    assert SECRET not in str(caught.value)
    assert SECRET not in repr(caught.value)


@pytest.mark.ac("RND-5.3")
@pytest.mark.parametrize(
    "label",
    ["synthetic build 1.0", "Synthetic build " + FULLWIDTH_ONE + ".0"],
    ids=["case-differs", "compatibility-look-alike"],
)
def test_labels_differing_in_case_or_by_compatibility_form_are_new(open_round, label):
    round_, (one, _, _) = open_round
    made = retest(round_, label, [one])
    assert made.label == label
    assert round_.builds.count() == 2


@pytest.mark.ac("RND-5.3")
def test_a_label_used_in_another_round_is_accepted(workspace, open_round):
    round_, (one, _, _) = open_round
    other, (theirs, _) = published(workspace, cases=2, title="Synthetic other")
    retest(other, "Synthetic build 1.1", [theirs])
    made = retest(round_, "Synthetic build 1.1", [one])
    assert made.round == round_


@pytest.mark.ac("RND-5.4")
def test_the_tenth_build_is_created_and_the_eleventh_refused(open_round):
    round_, (one, two, _) = open_round
    for n in range(1, 9):
        retest(round_, f"Synthetic build 1.{n}", [one])
    assert round_.builds.count() == 9
    tenth = retest(round_, "Synthetic build 2.0", [two])
    assert round_.builds.count() == 10
    assert list(tenth.cases.all()) == [two]
    refused(round_, "Synthetic build 3.0", [one.pk], CAP, "label")


@pytest.mark.ac("RND-5.4")
def test_the_cap_is_checked_before_the_cases_and_the_label(open_round, workspace):
    round_, (one, _, _) = open_round
    for n in range(1, 10):
        retest(round_, f"Synthetic build 1.{n}", [one])
    _, (foreign, _) = published(workspace, cases=2, title="Synthetic other")
    refused(round_, "Synthetic build 1.0", [foreign.pk], CAP, "label")


@pytest.mark.ac("RND-5.5")
def test_a_case_can_be_retested_again_and_earlier_builds_stay(open_round):
    round_, (one, two, _) = open_round
    first = current_build(one)
    records = stored(round_)[:3]
    second = retest(round_, "Synthetic build 1.1", [one, two])
    third = retest(round_, "Synthetic build 1.2", [one])
    assert list(one.builds.order_by("id")) == [first, second, third]
    assert current_build(one) == third and current_build(two) == second
    assert set(first.cases.all()) == set(round_.cases.all())
    assert set(second.cases.all()) == {one, two}
    assert stored(round_)[:3] == records


@pytest.mark.ac("RND-5.6")
def test_a_case_of_another_round_or_workspace_or_missing_is_refused(open_round):
    round_, (one, _, _) = open_round
    _, (same_workspace, _) = published(round_.workspace, 2, "Synthetic other")
    elsewhere = Workspace.objects.create(name="Demo workspace rnd50002")
    _, (other_workspace, _) = published(elsewhere, 2)
    missing = Case.objects.order_by("-id").first().pk + 1000
    for foreign in (same_workspace.pk, other_workspace.pk, missing):
        refused(round_, "Synthetic build 1.1", [foreign], FOREIGN, "cases")
        refused(round_, "Synthetic build 1.1", [one.pk, foreign], FOREIGN, "cases")


@pytest.mark.ac("RND-5.6")
def test_the_cases_are_checked_before_the_label(open_round, workspace):
    round_, _ = open_round
    _, (foreign, _) = published(workspace, cases=2, title="Synthetic other")
    refused(round_, "Synthetic build 1.0", [foreign.pk], FOREIGN, "cases")


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("state", ["draft", "closed"])
def test_a_round_that_is_not_open_is_refused_before_any_write(workspace, state):
    if state == "draft":
        round_ = new_round(workspace)
        cases = fill(round_, 2)
    else:
        round_, cases = published(workspace, cases=2)
        services.close(locked(round_))
    round_.refresh_from_db()
    before = (round_.state, stored(round_))
    with pytest.raises(services.RoundNotOpen) as caught:
        retest(round_, SECRET, cases)
    assert str(caught.value) == NOT_OPEN
    assert SECRET not in repr(caught.value)
    round_.refresh_from_db()
    assert (round_.state, stored(round_)) == before


@pytest.mark.ac("RND-5.8")
def test_a_stale_open_instance_of_a_closed_round_is_refused(open_round):
    round_, (one, _, _) = open_round
    Round.objects.filter(pk=round_.pk).update(state=Round.State.CLOSED)
    assert round_.state == Round.State.OPEN
    with pytest.raises(services.RoundNotOpen):
        services.request_retest(round_, "Synthetic build 1.1", [one.pk])
    assert round_.builds.count() == 1


# The retest form (RND-5.2, RND-5.6).


def form(round_, cases, label="Synthetic build 1.1"):
    return RetestForm(round_, {"cases": cases, "label": label})


@pytest.mark.ac("RND-5.1")
def test_form_choices_are_the_rounds_cases_in_creation_order(open_round, workspace):
    round_, cases = open_round
    published(workspace, cases=2, title="Synthetic other")
    field = RetestForm(round_).fields["cases"]
    assert list(field.queryset) == cases
    assert field.label == "Test cases to retest"
    rendered = str(RetestForm(round_)["cases"])
    assert rendered.count('type="checkbox"') == 3
    assert "checked" not in rendered


@pytest.mark.ac("RND-5.1")
def test_form_counts_a_repeated_case_once(open_round):
    round_, (one, two, _) = open_round
    valid = form(round_, [one.pk, two.pk, one.pk])
    assert valid.is_valid(), valid.errors
    assert sorted(c.pk for c in valid.cleaned_data["cases"]) == [one.pk, two.pk]


@pytest.mark.ac("RND-5.2")
@pytest.mark.parametrize(
    ("entered", "saved"),
    [("b" * 100, "b" * 100), ("  " + "b" * 100 + "  ", "b" * 100), ("b", "b")],
)
def test_form_accepts_a_label_of_1_to_100_characters(open_round, entered, saved):
    round_, (one, _, _) = open_round
    valid = form(round_, [one.pk], entered)
    assert valid.is_valid(), valid.errors
    assert valid.cleaned_data["label"] == saved


@pytest.mark.ac("RND-5.2")
@pytest.mark.parametrize(
    "entered",
    ["", "   ", ZERO_WIDTH_SPACE * 3, "b" * 101, " " + "b" * 101],
    ids=["empty", "spaces", "invisible", "101", "101-padded"],
)
def test_form_refuses_an_empty_invisible_or_long_label(open_round, entered):
    round_, (one, _, _) = open_round
    invalid = form(round_, [one.pk], entered)
    assert not invalid.is_valid()
    assert invalid.errors == {"label": [LABEL_LIMIT]}


@pytest.mark.ac("RND-5.2")
def test_form_refuses_no_selection(open_round):
    round_, _ = open_round
    invalid = form(round_, [])
    assert not invalid.is_valid()
    assert invalid.errors == {"cases": [NO_CASE]}


@pytest.mark.ac("RND-5.2")
def test_form_gives_both_messages_when_both_fields_are_invalid(open_round):
    round_, _ = open_round
    invalid = form(round_, [], "")
    assert not invalid.is_valid()
    assert invalid.errors == {"cases": [NO_CASE], "label": [LABEL_LIMIT]}


@pytest.mark.ac("RND-5.2")
def test_form_label_field_is_build_label_with_auto_direction(open_round):
    round_, _ = open_round
    field = RetestForm(round_)["label"]
    assert field.label == "Build label"
    assert 'dir="auto"' in str(field) and 'maxlength="100"' in str(field)


@pytest.mark.ac("RND-5.6")
def test_form_refuses_a_foreign_missing_or_non_integer_case(open_round):
    round_, (one, _, _) = open_round
    _, (same_workspace, _) = published(round_.workspace, 2, "Synthetic other")
    elsewhere = Workspace.objects.create(name="Demo workspace rnd50003")
    _, (other_workspace, _) = published(elsewhere, 2)
    missing = Case.objects.order_by("-id").first().pk + 1000
    for foreign in (same_workspace.pk, other_workspace.pk, missing, "abc"):
        for chosen in ([foreign], [one.pk, foreign]):
            invalid = form(round_, chosen)
            assert not invalid.is_valid()
            assert invalid.errors == {"cases": [FOREIGN]}, foreign


@pytest.mark.ac("RND-5.8")
def test_a_closed_round_at_the_cap_is_refused_as_not_open(open_round):
    round_, (one, _, _) = open_round
    for n in range(1, 10):
        retest(round_, f"Synthetic build 1.{n}", [one])
    services.close(locked(round_))
    before = stored(round_)
    with pytest.raises(services.RoundNotOpen):
        retest(round_, "Synthetic build 2.0", [one])
    assert stored(round_) == before
