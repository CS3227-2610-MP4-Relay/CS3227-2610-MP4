"""Service, form and data-model tests for publishing a round (RND-3)."""

import pytest
from django.db import DataError, IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import Workspace
from rounds import services
from rounds.forms import PublishForm
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import locked

pytestmark = pytest.mark.django_db

NO_CASES = "Add at least one test case before publishing."
LABEL_LIMIT = "Enter 1 to 100 characters."
ZERO_WIDTH_SPACE = chr(0x200B)
COMBINING_ACUTE = chr(0x0301)
E_ACUTE = chr(0x00E9)


@pytest.fixture
def workspace():
    return Workspace.objects.create(name="Demo workspace rnd30001")


@pytest.fixture
def round_(workspace):
    return Round.objects.create(workspace=workspace, title="Synthetic round")


@pytest.fixture
def other_round(workspace):
    return Round.objects.create(workspace=workspace, title="Synthetic other")


def fill(round_, cases=2):
    """Give `round_` two criteria and `cases` cases linked to them."""
    one = Criterion.objects.create(round=round_, text="Synthetic criterion 1")
    two = Criterion.objects.create(round=round_, text="Synthetic criterion 2")
    made = []
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {n}",
            steps="Open the synthetic page.",
            expected_result="The synthetic page opens.",
        )
        CaseCriterion.objects.create(case=case, criterion=one if n % 2 else two)
        made.append(case)
    return made


def snapshot(round_):
    """Everything RND-2 stores for a round."""
    return (
        list(Criterion.objects.filter(round=round_).values()),
        list(Case.objects.filter(round=round_).values()),
        list(CaseCriterion.objects.filter(case__round=round_).values()),
    )


def build(round_, label):
    return Build.objects.create(
        round=round_, label=label, key=services.build_key(label)
    )


@pytest.mark.ac("RND-3.1")
def test_publish_opens_the_round_with_one_build_covering_every_case(
    round_, other_round
):
    cases = fill(round_, 3)
    fill(other_round, 1)
    made = services.publish(locked(round_), "Synthetic build 1.0")
    round_.refresh_from_db()
    assert round_.state == Round.State.OPEN
    assert round_.published_at is not None
    assert list(Build.objects.filter(round=round_)) == [made]
    assert made.label == "Synthetic build 1.0"
    assert made.key == "Synthetic build 1.0"
    assert list(made.cases.all()) == cases
    assert not Build.objects.filter(round=other_round).exists()
    assert Round.objects.get(pk=other_round.pk).state == Round.State.DRAFT


@pytest.mark.ac("RND-3.3")
def test_publish_refuses_a_round_with_no_cases_before_any_write(round_):
    Criterion.objects.create(round=round_, text="Synthetic criterion")
    with pytest.raises(services.Refused) as refused:
        services.publish(locked(round_), "Synthetic build")
    assert str(refused.value) == NO_CASES
    assert refused.value.field == "label"
    round_.refresh_from_db()
    assert (round_.state, round_.published_at) == (Round.State.DRAFT, None)
    assert not Build.objects.exists()
    assert not BuildCase.objects.exists()


@pytest.mark.ac("RND-3.3")
def test_the_refusal_names_no_user_text(round_):
    secret_label = "Synthetic label kept out of messages"
    with pytest.raises(services.Refused) as refused:
        services.publish(locked(round_), secret_label)
    assert secret_label not in str(refused.value)
    assert secret_label not in repr(refused.value)


@pytest.mark.ac("RND-3.4")
def test_publishing_leaves_criteria_cases_and_links_unchanged(round_):
    fill(round_, 3)
    before = snapshot(round_)
    services.publish(locked(round_), "Synthetic build")
    assert snapshot(round_) == before


@pytest.mark.ac("RND-3.2")
@pytest.mark.parametrize(
    ("entered", "saved"),
    [
        ("b" * 100, "b" * 100),
        ("  " + "b" * 100 + "  ", "b" * 100),
        ("b", "b"),
    ],
)
def test_publish_form_accepts_1_to_100_characters(entered, saved):
    form = PublishForm({"label": entered})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["label"] == saved


@pytest.mark.ac("RND-3.2")
@pytest.mark.parametrize(
    "entered",
    ["", "   ", ZERO_WIDTH_SPACE * 3, "b" * 101, " " + "b" * 101],
    ids=["empty", "spaces", "invisible", "101", "101-padded"],
)
def test_publish_form_refuses_an_empty_invisible_or_long_label(entered):
    form = PublishForm({"label": entered})
    assert not form.is_valid()
    assert form.errors == {"label": [LABEL_LIMIT]}


@pytest.mark.ac("RND-3.2")
def test_publish_form_field_is_build_label_with_auto_direction():
    form = PublishForm()
    assert form.fields["label"].label == "Build label"
    assert 'dir="auto"' in str(form["label"])
    assert 'maxlength="100"' in str(form["label"])


def test_build_key_removes_format_characters():
    assert services.build_key("v1" + ZERO_WIDTH_SPACE + ".0") == "v1.0"


def test_build_key_applies_nfc_and_stays_case_sensitive():
    assert services.build_key("caf" + "e" + COMBINING_ACUTE) == "caf" + E_ACUTE
    assert services.build_key("caf" + E_ACUTE) == "caf" + E_ACUTE
    assert services.build_key("Beta") != services.build_key("beta")


def test_a_build_key_is_unique_within_a_round_only(round_, other_round):
    build(round_, "v1")
    with pytest.raises(IntegrityError), transaction.atomic():
        build(round_, "v" + ZERO_WIDTH_SPACE + "1")
    build(other_round, "v1")
    build(round_, "V1")
    assert Build.objects.count() == 3


@pytest.mark.parametrize(("label", "key"), [("b" * 101, "b"), ("b", "b" * 301)])
def test_database_limits_build_label_and_key(round_, label, key):
    with pytest.raises(DataError), transaction.atomic():
        Build.objects.create(round=round_, label=label, key=key)


def test_database_accepts_the_longest_label_and_key(round_):
    Build.objects.create(round=round_, label="b" * 100, key="b" * 300)


def test_builds_are_listed_in_creation_order(round_):
    first, second = build(round_, "v1"), build(round_, "v2")
    assert list(round_.builds.all()) == [first, second]


def test_a_build_covers_a_case_once(round_):
    (case,) = fill(round_, 1)
    made = build(round_, "v1")
    BuildCase.objects.create(build=made, case=case)
    with pytest.raises(IntegrityError), transaction.atomic():
        BuildCase.objects.create(build=made, case=case)


def test_a_covered_case_and_a_build_with_cases_cannot_be_deleted(round_):
    (case,) = fill(round_, 1)
    made = services.publish(locked(round_), "Synthetic build")
    case.links.all().delete()
    with pytest.raises(ProtectedError), transaction.atomic():
        case.delete()
    with pytest.raises(ProtectedError), transaction.atomic():
        made.delete()
    assert Case.objects.filter(pk=case.pk).exists()
    assert Build.objects.filter(pk=made.pk).exists()


def test_a_build_shows_no_user_text_in_its_string(round_):
    made = build(round_, "Synthetic label kept out of logs")
    assert "Synthetic label" not in str(made)
    assert "Synthetic label" not in repr(made)
