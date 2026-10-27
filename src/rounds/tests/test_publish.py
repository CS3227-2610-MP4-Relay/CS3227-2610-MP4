"""RND-3: publishing a round to Beta Testers through its round page."""

from unittest import mock

import pytest
from django.db import DatabaseError, transaction
from django.test import Client
from django.utils.html import escape

from rounds import services
from rounds.forms import PublishForm
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import (
    DENIED,
    IMG_TAG,
    MARKUP,
    NOT_FOUND,
    SCRIPT_TAG,
    UNAVAILABLE,
    csrf_token,
    detail,
    page,
    race,
    signed_in,
)

pytestmark = pytest.mark.django_db

PUBLISHED = "Round published."
LABEL_LIMIT = "Enter 1 to 100 characters."
NO_CASES = "Add at least one test case before publishing."
CONFLICT = "This action is not available while the round is {}."
LF, ZWSP = chr(10), chr(0x200B)
# Right-to-left override, zero-width space and left-to-right isolate.
BIDI_AND_INVISIBLE = "abc" + chr(0x202E) + "def" + ZWSP + "ghi" + chr(0x2066)


def publish_url(round_id):
    return f"/coordinator/rounds/{round_id}/publish/"


def fill(round_, cases=2):
    """Two criteria and `cases` cases, the first case linked to both."""
    one = Criterion.objects.create(round=round_, text="Synthetic criterion one")
    two = Criterion.objects.create(round=round_, text="Synthetic criterion two")
    made = []
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {n}",
            steps="Synthetic steps",
            expected_result="Synthetic result",
        )
        for item in (one, two) if n == 0 else (two,):
            CaseCriterion.objects.create(case=case, criterion=item)
        made.append(case)
    return made


def everything():
    return (
        list(Round.objects.values()),
        list(Criterion.objects.values()),
        list(Case.objects.values()),
        list(CaseCriterion.objects.values()),
        list(Build.objects.values()),
        list(BuildCase.objects.values()),
    )


def stays_draft(round_):
    round_.refresh_from_db()
    assert (round_.state, round_.published_at) == (Round.State.DRAFT, None)
    assert not Build.objects.filter(round=round_).exists()


def no_store(response):
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control and "private" in cache_control


def message_next_to_label(html, message):
    """The message appears once, after the label input, before the button."""
    assert html.count(message) == 1
    start = html.index('name="label"')
    assert start < html.index(message) < html.index("Publish round</button>")


@pytest.fixture
def draft(make_round):
    return make_round("Synthetic draft round")


# RND-3.1


@pytest.mark.ac("RND-3.1")
def test_draft_round_page_has_the_publish_form_after_the_cases(coord_client, draft):
    fill(draft)
    html = page(coord_client.get(detail(draft.pk)))
    form = html.index(f'action="{publish_url(draft.pk)}"')
    assert html.index("<h2>Test cases</h2>") < html.index("Synthetic case 1") < form
    assert form < html.index('<label for="id_label">Build label</label>')
    assert html.index('name="label"') < html.index("Publish round</button>")
    assert html.index("Publish round</button>") < html.index("Coordinator home")
    assert "<h2>Builds</h2>" not in html and "Current build" not in html


@pytest.mark.ac("RND-3.1", "RND-3.3")
def test_the_publish_form_shows_on_a_draft_round_without_cases(coord_client, draft):
    html = page(coord_client.get(detail(draft.pk)))
    assert "Publish round</button>" in html


@pytest.mark.ac("RND-3.1")
def test_publishing_opens_the_round_on_one_build(coord_client, draft):
    cases = fill(draft, 3)
    response = coord_client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
    assert response.status_code == 302
    assert response["Location"] == detail(draft.pk)
    draft.refresh_from_db()
    assert draft.state == Round.State.OPEN and draft.published_at is not None
    (made,) = Build.objects.filter(round=draft)
    assert made.label == "Synthetic 1.0"
    assert list(made.cases.all()) == cases


@pytest.mark.ac("RND-3.1")
def test_round_page_after_publishing_shows_the_message_once_and_the_open_view(
    coord_client, draft
):
    fill(draft, 2)
    coord_client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
    html = page(coord_client.get(detail(draft.pk)))
    heading = html.index("</h1>")
    assert html.count(PUBLISHED) == 1
    assert heading < html.index(PUBLISHED) < html.index("<p>State: Open</p>")
    label = '<span dir="auto">Synthetic 1.0</span>'
    # Each case's current build, then the build in the builds list.
    assert html.count(label) == 3
    for n in range(2):
        case_at = html.index(f'<h3><span dir="auto">Synthetic case {n}</span></h3>')
        build_at = html.index("<h4>Current build</h4>", case_at)
        assert html.index("<h4>Linked acceptance criteria</h4>", case_at) < build_at
        assert html.index(label, build_at) == html.index("<p>", build_at) + 3
    builds = html.index("<h2>Builds</h2>")
    assert html.rindex("Current build") < builds
    after = html[builds:]
    assert after.index(f"<h3>{label}</h3>") < after.index("<h4>Covered test cases</h4>")
    assert after.index("Synthetic case 0") < after.index("Synthetic case 1")
    assert "Synthetic criterion one" in html and "Synthetic steps" in html
    for control in (
        "Edit round",
        "Add acceptance criterion",
        "Add test case",
        "Edit criterion",
        "Delete criterion",
        "Edit test case",
        "Delete test case",
        "Publish round",
        "Build label",
        # RND-6 adds the "Close round" form; no RND-2 or RND-3 form remains.
        '/delete/"',
        '/publish/"',
    ):
        assert control not in html, control
    again = page(coord_client.get(detail(draft.pk)))
    assert PUBLISHED not in again


@pytest.mark.ac("RND-3.1")
def test_builds_list_oldest_first_and_current_build_is_the_newest_covering(
    coord_client, make_round
):
    # A later build (RND-5's retest) is put in directly.
    opened = make_round("Synthetic open", Round.State.OPEN)
    first, second = fill(opened, 2)
    old = Build.objects.create(round=opened, label="Synthetic old", key="old")
    BuildCase.objects.bulk_create(
        [BuildCase(build=old, case=first), BuildCase(build=old, case=second)]
    )
    new = Build.objects.create(round=opened, label="Synthetic new", key="new")
    BuildCase.objects.create(build=new, case=second)
    html = page(coord_client.get(detail(opened.pk)))
    builds = html.index("<h2>Builds</h2>")
    current = [
        html[html.index("<h4>Current build</h4>", html.index(f"Synthetic case {n}")) :]
        for n in range(2)
    ]
    assert current[0].index("Synthetic old") < current[0].index("Synthetic new")
    assert current[1].index("Synthetic new") < current[1].index("Synthetic old")
    listed = html[builds:]
    assert listed.index("Synthetic old") < listed.index("Synthetic new")
    covered_by_new = listed[listed.index("Synthetic new") :]
    assert "Synthetic case 1" in covered_by_new
    assert "Synthetic case 0" not in covered_by_new


# RND-3.2


@pytest.mark.ac("RND-3.2")
@pytest.mark.parametrize(
    ("entered", "saved"),
    [("b" * 100, "b" * 100), ("  " + "b" * 99 + "c  ", "b" * 99 + "c")],
)
def test_a_label_of_up_to_100_characters_publishes(coord_client, draft, entered, saved):
    fill(draft, 1)
    response = coord_client.post(publish_url(draft.pk), {"label": entered})
    assert response.status_code == 302
    assert Build.objects.get(round=draft).label == saved


@pytest.mark.ac("RND-3.2")
@pytest.mark.parametrize(
    "entered",
    ["", "   ", ZWSP * 3, "b" * 101],
    ids=["empty", "spaces", "invisible", "101"],
)
def test_an_invalid_label_is_refused_next_to_the_field(coord_client, draft, entered):
    fill(draft, 1)
    response = coord_client.post(publish_url(draft.pk), {"label": entered})
    assert response.status_code == 200
    html = page(response)
    message_next_to_label(html, LABEL_LIMIT)
    if entered.strip():
        assert f'value="{entered}"' in html
    assert "<p>State: Draft</p>" in html
    no_store(response)
    stays_draft(draft)


@pytest.mark.ac("RND-3.2")
def test_a_missing_label_field_is_refused(coord_client, draft):
    fill(draft, 1)
    response = coord_client.post(publish_url(draft.pk), {})
    message_next_to_label(page(response), LABEL_LIMIT)
    stays_draft(draft)


@pytest.mark.ac("RND-3.2")
def test_a_null_character_in_the_label_is_refused(coord_client, draft):
    fill(draft, 1)
    response = coord_client.post(publish_url(draft.pk), {"label": "a" + chr(0) + "b"})
    message_next_to_label(page(response), "Null characters are not allowed.")
    stays_draft(draft)


# RND-3.3


@pytest.mark.ac("RND-3.3")
def test_a_round_without_cases_is_refused(coord_client, draft):
    Criterion.objects.create(round=draft, text="Synthetic criterion")
    before = everything()
    response = coord_client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
    assert response.status_code == 200
    html = page(response)
    message_next_to_label(html, NO_CASES)
    assert 'value="Synthetic 1.0"' in html
    assert "Edit round" in html
    assert everything() == before


@pytest.mark.ac("RND-3.3")
def test_an_invalid_label_on_a_round_without_cases_gets_only_the_label_message(
    coord_client, draft
):
    response = coord_client.post(publish_url(draft.pk), {"label": ""})
    html = page(response)
    message_next_to_label(html, LABEL_LIMIT)
    assert NO_CASES not in html
    stays_draft(draft)


# RND-3.4


@pytest.mark.ac("RND-3.4")
def test_the_published_round_keeps_exactly_what_was_saved(coord_client, draft):
    fill(draft, 3)
    records = everything()[1:4]
    before = page(coord_client.get(detail(draft.pk)))
    coord_client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
    assert everything()[1:4] == records
    after = page(coord_client.get(detail(draft.pk)))
    for text in ("Synthetic criterion one", "Synthetic criterion two"):
        assert after.count(text) == before.count(text)
    for n in range(3):
        assert f"Synthetic case {n}" in after


# RND-3.5


def add_case(round_, linked):
    data = {
        "title": "Synthetic racer",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": [linked.pk],
    }
    return lambda client: client.post(
        f"/coordinator/rounds/{round_.pk}/cases/new/", data
    )


def publish(round_, label):
    return lambda client: client.post(publish_url(round_.pk), {"label": label})


@pytest.mark.ac("RND-3.5")
@pytest.mark.django_db(transaction=True)
def test_an_edit_saved_before_publishing_is_in_the_published_round(coordinator):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    (existing,) = fill(draft, 1)
    linked = existing.criteria.first()
    edit, published = race(
        coordinator,
        add_case(draft, linked),
        publish(draft, "Synthetic 1.0"),
        ["add_case", "publish"],
    )
    assert (edit.status_code, published.status_code) == (302, 302)
    racer = Case.objects.get(round=draft, title="Synthetic racer")
    (made,) = Build.objects.filter(round=draft)
    assert list(made.cases.all()) == [existing, racer]


@pytest.mark.ac("RND-3.5")
@pytest.mark.django_db(transaction=True)
def test_an_edit_arriving_during_publishing_gets_409(coordinator):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    (existing,) = fill(draft, 1)
    linked = existing.criteria.first()
    published, edit = race(
        coordinator,
        publish(draft, "Synthetic 1.0"),
        add_case(draft, linked),
        ["add_case", "publish"],
    )
    assert (published.status_code, edit.status_code) == (302, 409)
    assert CONFLICT.format("Open") in page(edit)
    assert not Case.objects.filter(title="Synthetic racer").exists()
    (made,) = Build.objects.filter(round=draft)
    assert list(made.cases.all()) == [existing]


@pytest.mark.ac("RND-3.5")
@pytest.mark.django_db(transaction=True)
def test_of_two_publishes_exactly_one_succeeds(coordinator):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    fill(draft, 2)
    first, second = race(
        coordinator,
        publish(draft, "Synthetic first"),
        publish(draft, "Synthetic second"),
        ["publish"],
    )
    assert (first.status_code, second.status_code) == (302, 409)
    assert CONFLICT.format("Open") in page(second)
    (made,) = Build.objects.filter(round=draft)
    assert made.label == "Synthetic first"
    assert BuildCase.objects.count() == 2
    assert Round.objects.get(pk=draft.pk).state == Round.State.OPEN


def retitle(round_):
    return lambda client: client.post(
        f"/coordinator/rounds/{round_.pk}/edit/", {"title": "Synthetic retitled"}
    )


def delete_case(round_, case):
    return lambda client: client.post(
        f"/coordinator/rounds/{round_.pk}/cases/{case.pk}/delete/"
    )


@pytest.mark.ac("RND-3.5")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("edit_first", [True, False])
def test_a_retitle_racing_a_publish_is_saved_first_or_refused(coordinator, edit_first):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    fill(draft, 1)
    requests = [retitle(draft), publish(draft, "Synthetic 1.0")]
    if not edit_first:
        requests.reverse()
    first, second = race(coordinator, *requests, [(Round, "save")])
    edit, published = (first, second) if edit_first else (second, first)
    assert published.status_code == 302
    final = Round.objects.get(pk=draft.pk)
    assert final.state == Round.State.OPEN
    assert Build.objects.filter(round=draft).count() == 1
    if edit_first:
        assert edit.status_code == 302
        assert final.title == "Synthetic retitled"
    else:
        assert edit.status_code == 409
        assert CONFLICT.format("Open") in page(edit)
        assert final.title == "Synthetic"


@pytest.mark.ac("RND-3.5")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("edit_first", [True, False])
def test_a_case_deletion_racing_a_publish_is_applied_first_or_refused(
    coordinator, edit_first
):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    kept, doomed = fill(draft, 2)
    requests = [delete_case(draft, doomed), publish(draft, "Synthetic 1.0")]
    if not edit_first:
        requests.reverse()
    first, second = race(coordinator, *requests, ["delete_case", "publish"])
    edit, published = (first, second) if edit_first else (second, first)
    assert published.status_code == 302
    (made,) = Build.objects.filter(round=draft)
    if edit_first:
        assert edit.status_code == 302
        assert not Case.objects.filter(pk=doomed.pk).exists()
        assert list(made.cases.all()) == [kept]
    else:
        # Never a 500 or 503 from the build's protected link to the case.
        assert edit.status_code == 409
        assert CONFLICT.format("Open") in page(edit)
        assert list(made.cases.all()) == [kept, doomed]
        assert CaseCriterion.objects.filter(case=doomed).exists()


# RND-3.6


@pytest.mark.ac("RND-3.6")
@pytest.mark.parametrize("signed", [True, False])
def test_get_head_and_put_get_405_uncached(coordinator, draft, signed):
    fill(draft, 1)
    client = signed_in(coordinator) if signed else Client()
    for method in ("get", "head", "put"):
        response = getattr(client, method)(publish_url(draft.pk))
        assert response.status_code == 405, method
        no_store(response)
    stays_draft(draft)


@pytest.mark.ac("RND-3.6")
@pytest.mark.parametrize(
    "token, origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_post_without_valid_csrf_or_same_origin_gets_403(
    coordinator, draft, token, origin
):
    fill(draft, 1)
    client = signed_in(coordinator, enforce_csrf_checks=True)
    data = {"label": "Synthetic 1.0"}
    if token != "missing":
        data["csrfmiddlewaretoken"] = (
            csrf_token(client) if token == "valid" else "x" * 32
        )
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    response = client.post(publish_url(draft.pk), data, **extra)
    assert response.status_code == 403
    assert DENIED in page(response)
    stays_draft(draft)


@pytest.mark.ac("RND-3.6")
def test_signed_out_visitor_is_redirected_to_sign_in(draft):
    fill(draft, 1)
    client = Client(enforce_csrf_checks=True)
    token = csrf_token(client)
    for round_id in (draft.pk, draft.pk + 1000):
        response = client.post(
            publish_url(round_id),
            {"label": "Synthetic 1.0", "csrfmiddlewaretoken": token},
        )
        assert response.status_code == 302
        assert response["Location"] == "/sign-in/"
    stays_draft(draft)


@pytest.mark.ac("RND-3.6")
def test_tester_gets_the_same_403_for_existing_and_missing_rounds(tester, draft):
    fill(draft, 1)
    client = signed_in(tester)
    with mock.patch("rounds.views.get_object_or_404") as lookup:
        first = client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
        second = client.post(publish_url(draft.pk + 1000), {"label": "Synthetic 1.0"})
    lookup.assert_not_called()
    assert first.status_code == second.status_code == 403
    assert first.content == second.content and DENIED in page(first)
    stays_draft(draft)


@pytest.mark.ac("RND-3.6")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_another_workspaces_round_gets_404_not_409(
    coord_client, make_round, other_workspace, state
):
    foreign = make_round("Synthetic foreign", state, owner=other_workspace)
    fill(foreign, 1)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    for round_id in (foreign.pk, 999999):
        response = coord_client.post(publish_url(round_id), {"label": "Synthetic"})
        assert response.status_code == 404
        assert response.content == reference.content
        assert NOT_FOUND in page(response)
    assert everything() == before


@pytest.mark.ac("RND-3.6")
@pytest.mark.parametrize("state, name", [("open", "Open"), ("closed", "Closed")])
@pytest.mark.parametrize("label", ["Synthetic 2.0", ""])
def test_publishing_an_open_or_closed_round_gets_409(
    coord_client, make_round, state, name, label
):
    frozen = make_round("Synthetic frozen", state)
    fill(frozen, 1)
    before = everything()
    response = coord_client.post(publish_url(frozen.pk), {"label": label})
    assert response.status_code == 409
    html = page(response)
    assert "<title>Action not available</title>" in html
    assert f"<h1>{CONFLICT.format(name)}</h1>" in html
    no_store(response)
    assert everything() == before


@pytest.mark.ac("RND-3.6")
def test_round_opened_after_the_state_check_gets_409_from_the_locked_recheck(
    coord_client, draft
):
    fill(draft, 1)
    real_is_valid = PublishForm.is_valid

    def open_then_validate(form):
        Round.objects.filter(pk=draft.pk).update(state=Round.State.OPEN)
        return real_is_valid(form)

    with mock.patch.object(PublishForm, "is_valid", open_then_validate):
        response = coord_client.post(publish_url(draft.pk), {"label": "Synthetic"})
    assert response.status_code == 409
    assert CONFLICT.format("Open") in page(response)
    assert not Build.objects.exists()


@pytest.mark.ac("RND-3.6")
def test_storage_failure_mid_publish_gives_503_and_changes_nothing(
    coord_client, draft, caplog
):
    fill(draft, 2)
    before = everything()
    with mock.patch.object(Round, "save", side_effect=DatabaseError("synthetic")):
        response = coord_client.post(publish_url(draft.pk), {"label": "Synthetic"})
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    no_store(response)
    assert everything() == before
    logged = [record for record in caplog.records if record.name == "rounds.views"]
    assert len(logged) == 1 and logged[0].exc_info[0] is DatabaseError
    assert "Synthetic" not in caplog.text


@pytest.mark.ac("RND-3.6")
def test_injected_fields_are_ignored(coord_client, draft, make_round):
    fill(draft, 1)
    other = make_round("Synthetic other")
    fill(other, 1)
    data = {
        "label": "Synthetic 1.0",
        "round": other.pk,
        "state": "closed",
        "key": "Synthetic forged",
        "cases": [Case.objects.filter(round=other).first().pk],
    }
    coord_client.post(publish_url(draft.pk), data)
    (made,) = Build.objects.all()
    assert (made.round, made.key) == (draft, "Synthetic 1.0")
    assert list(made.cases.all()) == list(draft.cases.all())
    assert Round.objects.get(pk=draft.pk).state == Round.State.OPEN
    assert Round.objects.get(pk=other.pk).state == Round.State.DRAFT


def published_page(client, round_, label):
    fill(round_, 1)
    client.post(publish_url(round_.pk), {"label": label})
    return page(client.get(detail(round_.pk)))


@pytest.mark.ac("RND-3.6")
def test_markup_in_a_build_label_is_escaped(coord_client, draft):
    html = published_page(coord_client, draft, MARKUP)
    isolated = f'<span dir="auto">{escape(MARKUP)}</span>'
    # The current build of the one case, and the build in the builds list.
    assert html.count(isolated) == 2
    assert SCRIPT_TAG not in html and IMG_TAG not in html


@pytest.mark.ac("RND-3.6")
def test_markup_in_a_refused_label_is_escaped_in_the_field_value(coord_client, draft):
    refused = MARKUP + "x" * 100
    fill(draft, 1)
    html = page(coord_client.post(publish_url(draft.pk), {"label": refused}))
    assert f'value="{escape(refused)}"' in html
    assert SCRIPT_TAG not in html and IMG_TAG not in html


@pytest.mark.ac("RND-3.6")
def test_markup_in_a_label_refused_for_no_cases_is_escaped(coord_client, draft):
    html = page(coord_client.post(publish_url(draft.pk), {"label": MARKUP}))
    assert NO_CASES in html
    assert f'value="{escape(MARKUP)}"' in html
    assert SCRIPT_TAG not in html and IMG_TAG not in html


@pytest.mark.ac("RND-3.6")
def test_a_label_posted_with_line_breaks_is_shown_line_by_line(coord_client, draft):
    html = published_page(coord_client, draft, "Synthetic one" + LF + "two")
    lines = '<span dir="auto">Synthetic one</span><br><span dir="auto">two</span>'
    assert html.count(lines) == 2


@pytest.mark.ac("RND-3.6")
def test_bidi_and_zero_width_characters_stay_inside_their_element(coord_client, draft):
    # Published without the form, which refuses text-direction controls (rule 5).
    fill(draft, 1)
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=draft.pk)
        services.publish(locked, BIDI_AND_INVISIBLE)
    html = page(coord_client.get(detail(draft.pk)))
    assert html.count(f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>') == 2
    outside = html.replace(f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>', "")
    for char in (chr(0x202E), ZWSP, chr(0x2066)):
        assert char not in outside


@pytest.mark.ac("RND-3.6")
def test_case_titles_in_the_builds_list_are_escaped_and_isolated(coord_client, draft):
    title = MARKUP + LF + BIDI_AND_INVISIBLE
    fill(draft, 1)
    Case.objects.filter(round=draft).update(title=title)
    coord_client.post(publish_url(draft.pk), {"label": "Synthetic 1.0"})
    html = page(coord_client.get(detail(draft.pk)))
    lines = (
        f'<span dir="auto">{escape(MARKUP)}</span><br>'
        f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>'
    )
    # The case heading under "Test cases" and the entry under "Builds".
    assert html.count(lines) == 2
    assert html.index("<h2>Builds</h2>") < html.rindex(lines)
    outside = html.replace(lines, "")
    assert SCRIPT_TAG not in outside and IMG_TAG not in outside
    for char in (chr(0x202E), ZWSP, chr(0x2066)):
        assert char not in outside


@pytest.mark.ac("RND-3.2")
@pytest.mark.parametrize("char", [0x1D1C0, 0x1D160], ids=["U1D1C0", "U1D160"])
def test_a_100_character_label_tripled_by_nfc_publishes(coord_client, draft, char):
    # Each character decomposes into 3 under NFC, the largest expansion.
    fill(draft, 1)
    response = coord_client.post(publish_url(draft.pk), {"label": chr(char) * 100})
    assert response.status_code == 302
    made = Build.objects.get(round=draft)
    assert len(made.label) == 100
    assert len(made.key) == 300


@pytest.mark.ac("RND-3.6")
def test_a_build_label_never_reaches_the_page_title(coord_client, draft):
    html = published_page(coord_client, draft, "Synthetic label")
    title = html.split("<title>", 1)[1].split("</title>", 1)[0]
    assert title == chr(0x2068) + "Synthetic draft round" + chr(0x2069)
