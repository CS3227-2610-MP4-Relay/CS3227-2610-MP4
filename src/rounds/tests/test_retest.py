"""RND-5: requesting a retest from an Open round's page."""

from unittest import mock

import pytest
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import QuerySet
from django.test import Client
from django.utils.html import escape

from rounds import services
from rounds.forms import RetestForm
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round
from rounds.templatetags import rounds_text

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
    stored_retest,
)

pytestmark = pytest.mark.django_db

DUPLICATE = "This build label is already used in this round."
CAP = "This round has reached its limit of 10 builds."
NO_CASE = "Select at least one test case."
FOREIGN = "Choose test cases from this round."
LABEL_LIMIT = "Enter 1 to 100 characters."
CONFLICT = "This action is not available while the round is {}."
LINK = "Request a retest</a>"
BUTTON = "Request retest</button>"
FSI, PDI, RLO, ZWSP, LF = chr(0x2068), chr(0x2069), chr(0x202E), chr(0x200B), chr(10)
LINE_SEPARATOR = chr(0x2028)
BIDI_AND_INVISIBLE = "abc" + RLO + "def" + ZWSP + "ghi" + chr(0x2066)


def retest_url(round_id):
    return f"/coordinator/rounds/{round_id}/retest/"


def close_url(round_id):
    return f"/coordinator/rounds/{round_id}/close/"


def published(round_, cases=3, title="Synthetic case", label="Synthetic 1.0"):
    """Give `round_` a criterion and `cases` linked cases, then publish it."""
    linked = Criterion.objects.create(round=round_, text="Synthetic criterion")
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"{title} {n}",
            steps="Synthetic steps",
            expected_result="Synthetic result",
        )
        CaseCriterion.objects.create(case=case, criterion=linked)
    with transaction.atomic():
        services.publish(Round.objects.select_for_update().get(pk=round_.pk), label)
    round_.refresh_from_db()
    return round_


def everything():
    return (
        list(Round.objects.values()),
        list(Criterion.objects.values()),
        list(Case.objects.values()),
        list(CaseCriterion.objects.values()),
        list(Build.objects.values()),
        list(BuildCase.objects.values()),
    )


def no_store(response):
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control and "private" in cache_control


def cases_of(round_):
    return list(round_.cases.order_by("id"))


def data(cases, label="Synthetic 1.1"):
    return {
        "cases": [case.pk if hasattr(case, "pk") else case for case in cases],
        "label": label,
    }


def current_build(case):
    return case.builds.order_by("-id").first()


def message(count, label):
    noun = "test case" if count == 1 else "test cases"
    return (
        f"Retest requested for {count} {noun} on build "
        f'<span dir="auto">{escape(label)}</span>.'
    )


def next_to_cases(html, text):
    """`text` sits after the case checkboxes and before the label field."""
    return html.index("</fieldset>") < html.index(text) < html.index("Build label")


def next_to_label(html, text):
    """`text` sits after the label field and before the button."""
    return html.index('name="label"') < html.index(text) < html.index(BUTTON)


@pytest.fixture
def opened(make_round):
    return published(make_round("Synthetic open round"))


# RND-5.1


@pytest.mark.ac("RND-5.1")
def test_retest_page_lists_every_case_unselected_with_the_label_field(
    coord_client, opened, make_round
):
    published(make_round("Synthetic other"), title="Synthetic foreign")
    response = coord_client.get(retest_url(opened.pk))
    assert response.status_code == 200
    no_store(response)
    html = page(response)
    assert "<title>Request a retest</title>" in html
    assert "<h1>Request a retest</h1>" in html
    assert "<legend>Test cases to retest</legend>" in html
    assert html.count('type="checkbox"') == 3 and "checked" not in html
    at = [html.index(f'<span dir="auto">Synthetic case {n}</span>') for n in range(3)]
    assert html.index("<legend>") < at[0] < at[1] < at[2] < html.index("Build label")
    assert "Synthetic foreign" not in html
    assert html.index("Build label") < html.index(BUTTON)
    assert f'<a href="{detail(opened.pk)}">Back to round</a>' in html


@pytest.mark.ac("RND-5.1")
def test_requesting_a_retest_moves_only_the_selected_cases_to_the_new_build(
    coord_client, opened
):
    one, two, three = cases_of(opened)
    first = current_build(one)
    response = coord_client.post(retest_url(opened.pk), data([one, three]))
    assert response.status_code == 302
    assert response["Location"] == detail(opened.pk)
    made = opened.builds.order_by("-id").first()
    assert made.label == "Synthetic 1.1"
    assert set(made.cases.all()) == {one, three}
    assert current_build(one) == current_build(three) == made
    assert current_build(two) == first


@pytest.mark.ac("RND-5.1")
def test_round_page_shows_the_message_once_and_the_new_current_builds(
    coord_client, opened
):
    one, _, three = cases_of(opened)
    coord_client.post(retest_url(opened.pk), data([one, three]))
    html = page(coord_client.get(detail(opened.pk)))
    shown = f'<p role="status">{message(2, "Synthetic 1.1")}</p>'
    assert html.count(shown) == 1
    assert html.index("</h1>") < html.index(shown) < html.index("<p>State: Open</p>")
    new = '<span dir="auto">Synthetic 1.1</span>'
    old = '<span dir="auto">Synthetic 1.0</span>'
    for n, label in ((0, new), (1, old), (2, new)):
        case_at = html.index(f'<span dir="auto">Synthetic case {n}</span></h3>')
        after = html[html.index("<h4>Current build</h4>", case_at) :]
        assert after.split("<p>", 1)[1].split("</p>", 1)[0] == label
    builds = html[html.index("<h2>Builds</h2>") :]
    newest = builds[builds.index(f"<h3>{new}</h3>") :]
    assert builds.index("<h3>") < builds.index(f"<h3>{new}</h3>")
    assert "Synthetic case 0" in newest and "Synthetic case 2" in newest
    assert "Synthetic case 1" not in newest
    assert "Retest requested" not in page(coord_client.get(detail(opened.pk)))


@pytest.mark.ac("RND-5.1")
@pytest.mark.parametrize("repeat", [1, 2])
def test_one_case_gets_the_singular_message_even_if_sent_twice(
    coord_client, opened, repeat
):
    one = cases_of(opened)[0]
    coord_client.post(retest_url(opened.pk), data([one] * repeat))
    html = page(coord_client.get(detail(opened.pk)))
    assert message(1, "Synthetic 1.1") in html
    assert BuildCase.objects.filter(build__label="Synthetic 1.1").count() == 1


@pytest.mark.ac("RND-5.1")
def test_open_round_page_links_to_the_retest_page_under_the_builds_heading(
    coord_client, opened
):
    html = page(coord_client.get(detail(opened.pk)))
    link = f'<p><a href="{retest_url(opened.pk)}">Request a retest</a></p>'
    assert html.count(link) == 1
    builds = html.index("<h2>Builds</h2>")
    assert html[builds + len("<h2>Builds</h2>") : html.index(link)].strip() == ""
    assert html.index(link) < html.index("<h3>", builds)


@pytest.mark.ac("RND-5.1")
@pytest.mark.parametrize("state", ["draft", "closed"])
def test_draft_and_closed_round_pages_have_no_retest_link(
    coord_client, make_round, state
):
    made = make_round("Synthetic round")
    if state == "closed":
        published(made)
        coord_client.post(close_url(made.pk))
    assert "Request a retest" not in page(coord_client.get(detail(made.pk)))


# RND-5.2


@pytest.mark.ac("RND-5.2")
def test_selecting_no_case_shows_the_message_and_keeps_the_label(coord_client, opened):
    before = everything()
    response = coord_client.post(retest_url(opened.pk), data([], "Synthetic kept"))
    assert response.status_code == 200
    html = page(response)
    assert html.count(NO_CASE) == 1 and next_to_cases(html, NO_CASE)
    assert 'value="Synthetic kept"' in html
    assert everything() == before


@pytest.mark.ac("RND-5.2")
@pytest.mark.parametrize(
    "label",
    ["", ZWSP * 3, "b" * 101],
    ids=["empty", "invisible", "101"],
)
def test_an_invalid_label_shows_the_message_and_keeps_the_selection(
    coord_client, opened, label
):
    one, two, _ = cases_of(opened)
    before = everything()
    response = coord_client.post(retest_url(opened.pk), data([one, two], label))
    assert response.status_code == 200
    html = page(response)
    assert html.count(LABEL_LIMIT) == 1 and next_to_label(html, LABEL_LIMIT)
    assert html.count("checked") == 2
    assert everything() == before


@pytest.mark.ac("RND-5.2")
def test_a_100_character_label_is_accepted(coord_client, opened):
    one = cases_of(opened)[0]
    response = coord_client.post(retest_url(opened.pk), data([one], "b" * 100))
    assert response.status_code == 302
    assert opened.builds.filter(label="b" * 100).exists()


@pytest.mark.ac("RND-5.2")
def test_both_fields_invalid_show_both_messages(coord_client, opened):
    html = page(coord_client.post(retest_url(opened.pk), data([], "")))
    assert next_to_cases(html, NO_CASE) and next_to_label(html, LABEL_LIMIT)


# RND-5.3


@pytest.mark.ac("RND-5.3")
@pytest.mark.parametrize(
    "label", ["Synthetic 1.0", "Synthetic" + ZWSP + " 1.0"], ids=["equal", "cf"]
)
def test_a_used_label_shows_the_message_next_to_build_label(
    coord_client, opened, label
):
    one = cases_of(opened)[0]
    before = everything()
    response = coord_client.post(retest_url(opened.pk), data([one], label))
    assert response.status_code == 200
    html = page(response)
    assert html.count(DUPLICATE) == 1 and next_to_label(html, DUPLICATE)
    assert html.count("checked") == 1 and f'value="{label}"' in html
    assert everything() == before


# RND-5.4


@pytest.mark.ac("RND-5.4")
def test_the_tenth_build_is_created_and_the_eleventh_refused(coord_client, opened):
    one = cases_of(opened)[0]
    for n in range(1, 10):
        response = coord_client.post(retest_url(opened.pk), data([one], f"v{n}"))
        assert response.status_code == 302
    assert opened.builds.count() == 10
    before = everything()
    for label in ("Synthetic 9.9", "Synthetic 1.0"):
        html = page(coord_client.post(retest_url(opened.pk), data([one], label)))
        assert html.count(CAP) == 1 and next_to_label(html, CAP)
        assert DUPLICATE not in html
    assert everything() == before


# RND-5.5


@pytest.mark.ac("RND-5.5")
def test_retesting_a_case_again_keeps_earlier_builds_listed(coord_client, opened):
    one, two, _ = cases_of(opened)
    records = everything()[1:4]
    coord_client.post(retest_url(opened.pk), data([one, two], "Synthetic 1.1"))
    coord_client.post(retest_url(opened.pk), data([one], "Synthetic 1.2"))
    assert everything()[1:4] == records
    html = page(coord_client.get(detail(opened.pk)))
    builds = html[html.index("<h2>Builds</h2>") :]
    parts = builds.split("<h3>")[1:]
    assert [part.split("</h3>")[0] for part in parts] == [
        f'<span dir="auto">Synthetic 1.{n}</span>' for n in range(3)
    ]
    assert all(f"Synthetic case {n}" in parts[0] for n in range(3))
    assert "Synthetic case 1" in parts[1] and "Synthetic case 2" not in parts[1]
    assert "Synthetic case 0" in parts[2] and "Synthetic case 1" not in parts[2]


# RND-5.6


@pytest.mark.ac("RND-5.6")
def test_a_foreign_missing_or_malformed_case_shows_the_message(
    coord_client, opened, make_round, other_workspace
):
    one = cases_of(opened)[0]
    same = cases_of(published(make_round("Synthetic other")))[0]
    foreign = cases_of(published(make_round("Synthetic far", owner=other_workspace)))
    before = everything()
    for bad in (same.pk, foreign[0].pk, 999999, "abc"):
        for chosen in ([bad], [one, bad]):
            response = coord_client.post(retest_url(opened.pk), data(chosen))
            assert response.status_code == 200, bad
            html = page(response)
            assert html.count(FOREIGN) == 1 and next_to_cases(html, FOREIGN), bad
    assert everything() == before


# RND-5.7


def post_retest(round_, cases, label):
    return lambda client: client.post(retest_url(round_.pk), data(cases, label))


def post_close(round_):
    return lambda client: client.post(close_url(round_.pk))


def new_open_round(coordinator):
    made = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    return published(made)


@pytest.mark.ac("RND-5.7")
@pytest.mark.django_db(transaction=True)
def test_of_two_retests_with_one_label_exactly_one_succeeds(coordinator, caplog):
    opened = new_open_round(coordinator)
    one, two, _ = cases_of(opened)
    first, second = race(
        coordinator,
        post_retest(opened, [one], "Synthetic 2.0"),
        post_retest(opened, [two], "Synthetic 2.0"),
        ["request_retest"],
    )
    assert (first.status_code, second.status_code) == (302, 200)
    assert DUPLICATE in page(second)
    made = opened.builds.get(label="Synthetic 2.0")
    assert list(made.cases.all()) == [one]
    assert opened.builds.count() == 2
    assert not [r for r in caplog.records if r.exc_info]
    assert not any("Synthetic 2.0" in r.getMessage() for r in caplog.records)


@pytest.mark.ac("RND-5.7")
@pytest.mark.django_db(transaction=True)
def test_a_retest_that_locks_first_completes_before_the_close(coordinator):
    opened = new_open_round(coordinator)
    one = cases_of(opened)[0]
    first, second = race(
        coordinator,
        post_retest(opened, [one], "Synthetic 2.0"),
        post_close(opened),
        ["request_retest"],
    )
    assert (first.status_code, second.status_code) == (302, 302)
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED
    assert current_build(one).label == "Synthetic 2.0"


@pytest.mark.ac("RND-5.7")
@pytest.mark.django_db(transaction=True)
def test_a_retest_after_a_close_gets_409(coordinator):
    opened = new_open_round(coordinator)
    one = cases_of(opened)[0]
    first, second = race(
        coordinator,
        post_close(opened),
        post_retest(opened, [one], "Synthetic 2.0"),
        ["close"],
    )
    assert (first.status_code, second.status_code) == (302, 409)
    assert CONFLICT.format("Closed") in page(second)
    assert opened.builds.count() == 1


# RND-5.8


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("state", ["draft", "closed"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_a_draft_or_closed_round_gets_409(coord_client, make_round, state, method):
    made = make_round("Synthetic round")
    if state == "closed":
        published(made)
        coord_client.post(close_url(made.pk))
    one = Case.objects.filter(round=made).first()
    before = everything()
    payload = data([one] if one else [], "Synthetic 2.0")
    response = getattr(coord_client, method)(retest_url(made.pk), payload)
    assert response.status_code == 409
    html = page(response)
    assert f"<h1>{CONFLICT.format(state.title())}</h1>" in html
    assert "<title>Action not available</title>" in html
    no_store(response)
    assert everything() == before


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("signed", [True, False])
def test_head_and_put_get_405_uncached(coordinator, opened, signed):
    client = signed_in(coordinator) if signed else Client()
    for method in ("head", "put", "delete"):
        response = getattr(client, method)(retest_url(opened.pk))
        assert response.status_code == 405, method
        no_store(response)


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize(
    "token, origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_post_without_valid_csrf_or_same_origin_gets_403(
    coordinator, opened, token, origin
):
    client = signed_in(coordinator, enforce_csrf_checks=True)
    payload = data(cases_of(opened)[:1])
    if token != "missing":
        payload["csrfmiddlewaretoken"] = (
            csrf_token(client) if token == "valid" else "x" * 32
        )
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    before = everything()
    response = client.post(retest_url(opened.pk), payload, **extra)
    assert response.status_code == 403
    assert DENIED in page(response)
    assert everything() == before


@pytest.mark.ac("RND-5.8")
def test_signed_out_visitor_is_redirected_to_sign_in(opened):
    client = Client(enforce_csrf_checks=True)
    token = csrf_token(client)
    before = everything()
    for round_id in (opened.pk, opened.pk + 1000):
        for response in (
            client.get(retest_url(round_id)),
            client.post(retest_url(round_id), {"csrfmiddlewaretoken": token}),
        ):
            assert response.status_code == 302
            assert response["Location"] == "/sign-in/"
    assert everything() == before


@pytest.mark.ac("RND-5.8")
def test_tester_gets_the_same_403_for_existing_and_missing_rounds(tester, opened):
    client = signed_in(tester)
    with mock.patch("rounds.views.get_object_or_404") as lookup:
        responses = [
            getattr(client, method)(retest_url(round_id), data(cases_of(opened)))
            for method in ("get", "post")
            for round_id in (opened.pk, opened.pk + 1000)
        ]
    lookup.assert_not_called()
    assert {response.status_code for response in responses} == {403}
    assert len({response.content for response in responses}) == 1
    assert opened.builds.count() == 1


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_another_workspaces_round_gets_404_not_409(
    coord_client, make_round, other_workspace, state
):
    foreign = make_round("Synthetic foreign", owner=other_workspace)
    if state != "draft":
        published(foreign)
    if state == "closed":
        Round.objects.filter(pk=foreign.pk).update(state=Round.State.CLOSED)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    for round_id in (foreign.pk, 999999):
        for method in ("get", "post"):
            payload = data(cases_of(foreign)[:1])
            response = getattr(coord_client, method)(retest_url(round_id), payload)
            assert response.status_code == 404
            assert response.content == reference.content
            assert NOT_FOUND in page(response)
    assert everything() == before


@pytest.mark.ac("RND-5.8")
def test_a_close_between_validation_and_the_locked_write_gives_409(
    coord_client, opened
):
    real_is_valid = RetestForm.is_valid

    def close_then_validate(form):
        Round.objects.filter(pk=opened.pk).update(state=Round.State.CLOSED)
        return real_is_valid(form)

    with mock.patch.object(RetestForm, "is_valid", close_then_validate):
        response = coord_client.post(retest_url(opened.pk), data(cases_of(opened)))
    assert response.status_code == 409
    assert CONFLICT.format("Closed") in page(response)
    assert opened.builds.count() == 1


@pytest.mark.ac("RND-5.8")
def test_a_round_not_open_inside_the_service_gives_409_not_500(coord_client, opened):
    # Even a refusal the view's own re-check did not foresee is the 409.
    refusing = mock.patch.object(
        services, "request_retest", side_effect=services.RoundNotOpen
    )
    with refusing:
        response = coord_client.post(retest_url(opened.pk), data(cases_of(opened)))
    assert response.status_code == 409
    assert "<title>Action not available</title>" in page(response)
    assert CONFLICT.format("Open") in page(response)
    no_store(response)
    assert opened.builds.count() == 1


@pytest.mark.ac("RND-5.8")
def test_storage_failure_mid_retest_gives_503_and_changes_nothing(
    coord_client, opened, caplog
):
    before = everything()
    real = services.request_retest

    def write_then_fail(*args):
        real(*args)
        raise DatabaseError("synthetic")

    with mock.patch.object(services, "request_retest", write_then_fail):
        response = coord_client.post(retest_url(opened.pk), data(cases_of(opened)))
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    no_store(response)
    assert everything() == before
    logged = [record for record in caplog.records if record.name == "rounds.views"]
    assert len(logged) == 1 and logged[0].exc_info[0] is DatabaseError


@pytest.mark.ac("RND-5.8")
def test_a_unique_constraint_backstop_is_not_reached(coord_client, opened):
    # The duplicate check runs before the insert, so no IntegrityError occurs.
    with mock.patch.object(
        Build.objects, "create", side_effect=IntegrityError("synthetic")
    ) as create:
        response = coord_client.post(
            retest_url(opened.pk), data(cases_of(opened)[:1], "Synthetic 1.0")
        )
    create.assert_not_called()
    assert DUPLICATE in page(response)


@pytest.mark.ac("RND-5.8")
def test_the_retest_form_on_the_page_carries_a_working_csrf_token(coordinator, opened):
    client = signed_in(coordinator, enforce_csrf_checks=True)
    html = page(client.get(retest_url(opened.pk)))
    token = html.split('name="csrfmiddlewaretoken" value="', 1)[1].split('"', 1)[0]
    payload = data(cases_of(opened)[:1])
    payload["csrfmiddlewaretoken"] = token
    response = client.post(retest_url(opened.pk), payload)
    assert response.status_code == 302
    assert opened.builds.count() == 2


@pytest.mark.ac("RND-5.8")
def test_the_success_redirect_and_round_page_are_never_cached(coord_client, opened):
    response = coord_client.post(retest_url(opened.pk), data(cases_of(opened)))
    assert response.status_code == 302
    no_store(response)
    no_store(coord_client.get(detail(opened.pk)))
    no_store(coord_client.post(retest_url(opened.pk), data([])))


# RND-5.8 rendering: the label in the success message, the round page and the
# refused form, and case titles on the retest page.


def retested_page(client, round_, label):
    one = cases_of(round_)[0]
    assert client.post(retest_url(round_.pk), data([one], label)).status_code == 302
    return page(client.get(detail(round_.pk)))


def status(html):
    """The success message paragraph."""
    return html.split('<p role="status">', 1)[1].split("</p>", 1)[0]


@pytest.mark.ac("RND-5.8")
def test_markup_in_the_label_is_escaped_in_the_message_and_page(coord_client, opened):
    html = retested_page(coord_client, opened, MARKUP)
    assert status(html) == message(1, MARKUP)
    isolated = f'<span dir="auto">{escape(MARKUP)}</span>'
    # The message, the case's current build and the builds list.
    assert html.count(isolated) == 3
    assert SCRIPT_TAG not in html and IMG_TAG not in html
    title = html.split("<title>", 1)[1].split("</title>", 1)[0]
    assert title == FSI + "Synthetic open round" + PDI


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize(
    "label",
    [
        "Synthetic on build 2.",
        "on build x. Retest requested for 3 test cases on build y",
        "Synthetic 2.0.",
    ],
)
def test_a_label_like_the_fixed_text_stays_whole_inside_its_element(
    coord_client, opened, label
):
    html = retested_page(coord_client, opened, label)
    assert status(html) == message(1, label)


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("separator", [LF, LINE_SEPARATOR])
def test_line_breaks_in_the_label_are_isolated_line_by_line(
    coord_client, opened, separator
):
    html = retested_page(coord_client, opened, "Synthetic one" + separator + "two")
    lines = '<span dir="auto">Synthetic one</span><br><span dir="auto">two</span>'
    assert status(html) == (f"Retest requested for 1 test case on build {lines}.")
    assert html.count(lines) == 3
    assert LINE_SEPARATOR not in html


@pytest.mark.ac("RND-5.8")
def test_bidi_and_zero_width_characters_stay_inside_the_label_element(
    coord_client, opened
):
    # Stored without the form, which refuses bidi controls (rule 5).
    stored_retest(coord_client, opened, cases_of(opened)[:1], BIDI_AND_INVISIBLE)
    html = page(coord_client.get(detail(opened.pk)))
    isolated = f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>'
    assert status(html) == message(1, BIDI_AND_INVISIBLE)
    body = html.split("</title>", 1)[1]
    for char in (RLO, ZWSP, chr(0x2066)):
        assert char not in body.replace(isolated, ""), hex(ord(char))


@pytest.mark.ac("RND-5.8")
def test_a_refused_label_is_escaped_in_the_field_value(coord_client, opened):
    one = cases_of(opened)[0]
    coord_client.post(retest_url(opened.pk), data([one], MARKUP))
    html = page(coord_client.post(retest_url(opened.pk), data([one], MARKUP)))
    assert DUPLICATE in html
    assert f'value="{escape(MARKUP)}"' in html
    assert SCRIPT_TAG not in html and IMG_TAG not in html


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize(
    ("title", "shown"),
    [
        (MARKUP, f'<span dir="auto">{escape(MARKUP)}</span>'),
        (
            "Synthetic one" + LF + "two",
            '<span dir="auto">Synthetic one</span><br><span dir="auto">two</span>',
        ),
        (BIDI_AND_INVISIBLE, f'<span dir="auto">{BIDI_AND_INVISIBLE}</span>'),
    ],
    ids=["markup", "line-break", "bidi"],
)
def test_case_titles_on_the_retest_page_are_escaped_and_isolated(
    coord_client, opened, title, shown
):
    Case.objects.filter(round=opened).update(title=title)
    html = page(coord_client.get(retest_url(opened.pk)))
    assert html.count(shown) == 3
    assert SCRIPT_TAG not in html and IMG_TAG not in html
    body = html.split("</title>", 1)[1]
    for char in (RLO, ZWSP, chr(0x2066)):
        assert char not in body.replace(shown, ""), hex(ord(char))
    assert "<title>Request a retest</title>" in html


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize(
    "text",
    [
        "Retest requested for 0 test cases on build x.",
        "Retest requested for 1 test cases on build x.",
        "Retest requested for 2 test case on build x.",
        "Retest requested for 1 test case on build x",
        "Retest requested for 1 test case on build .",
        " Retest requested for 1 test case on build x.",
        MARKUP,
    ],
)
def test_a_retest_message_that_does_not_match_shows_as_plain_escaped_text(text):
    shown = rounds_text.status_message(
        Message(constants.SUCCESS, text, extra_tags="retest")
    )
    assert shown == escape(text)
    assert "<span" not in shown


@pytest.mark.ac("RND-5.8")
def test_only_a_retest_tagged_message_is_split():
    text = rounds_text.retest_message(1, MARKUP)
    plain = rounds_text.status_message(Message(constants.SUCCESS, text))
    assert plain == escape(text)
    tagged = Message(constants.SUCCESS, text, extra_tags="retest")
    assert rounds_text.status_message(tagged) == message(1, MARKUP)
    for count, noun in ((1, "test case"), (2, "test cases")):
        expected = f"Retest requested for {count} {noun} on build x."
        assert rounds_text.retest_message(count, "x") == expected


# Repair round 1.


@pytest.mark.ac("RND-5.8")
def test_a_storage_failure_after_the_commit_cannot_lose_a_saved_retest(
    coord_client, opened
):
    real_count = QuerySet.count

    def failing_count(queryset):
        if queryset.model is BuildCase:
            raise DatabaseError("synthetic")
        return real_count(queryset)

    with mock.patch.object(QuerySet, "count", failing_count):
        response = coord_client.post(retest_url(opened.pk), data(cases_of(opened)))
    saved = opened.builds.filter(label="Synthetic 1.1").exists()
    # Either the retest is reported as done, or nothing of it was kept.
    assert (response.status_code, saved) in ((302, True), (503, False))


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("count", [10, 30])
def test_a_retest_message_with_a_larger_count_is_split(count):
    text = rounds_text.retest_message(count, MARKUP)
    tagged = Message(constants.SUCCESS, text, extra_tags="retest")
    assert rounds_text.status_message(tagged) == message(count, MARKUP)


@pytest.mark.ac("RND-5.8")
@pytest.mark.parametrize("count", ["02", "010"])
def test_a_retest_message_with_a_leading_zero_is_not_split(count):
    text = f"Retest requested for {count} test cases on build x."
    tagged = Message(constants.SUCCESS, text, extra_tags="retest")
    assert rounds_text.status_message(tagged) == escape(text)


@pytest.mark.ac("RND-5.2")
def test_a_label_with_a_null_character_is_refused_next_to_build_label(
    coord_client, opened
):
    before = everything()
    label = "Synthetic" + chr(0) + "1.1"
    response = coord_client.post(retest_url(opened.pk), data(cases_of(opened), label))
    assert response.status_code == 200
    html = page(response)
    assert next_to_label(html, "Null characters are not allowed.")
    assert everything() == before


@pytest.mark.ac("RND-5.6")
@pytest.mark.parametrize(
    "case_id",
    ["99999999999999999999", "9223372036854775808", str(10**30), "-1", "1.5"],
)
def test_an_out_of_range_case_id_gets_the_message_not_an_error(
    coord_client, opened, case_id
):
    before = everything()
    response = coord_client.post(retest_url(opened.pk), data([case_id]))
    assert response.status_code == 200
    html = page(response)
    assert html.count(FOREIGN) == 1 and next_to_cases(html, FOREIGN)
    assert everything() == before


@pytest.mark.ac("RND-5.7")
@pytest.mark.django_db(transaction=True)
def test_of_two_retests_for_the_tenth_build_exactly_one_succeeds(coordinator):
    opened = new_open_round(coordinator)
    one, two, _ = cases_of(opened)
    for n in range(1, 9):
        with transaction.atomic():
            services.request_retest(
                Round.objects.select_for_update().get(pk=opened.pk), f"v{n}", [one.pk]
            )
    assert opened.builds.count() == 9
    first, second = race(
        coordinator,
        post_retest(opened, [one], "Synthetic 9.1"),
        post_retest(opened, [two], "Synthetic 9.2"),
        ["request_retest"],
    )
    assert (first.status_code, second.status_code) == (302, 200)
    assert CAP in page(second)
    assert opened.builds.count() == 10
    assert opened.builds.filter(label="Synthetic 9.1").exists()


@pytest.mark.ac("RND-5.8")
def test_the_case_group_has_its_own_empty_text(coord_client, make_round):
    # Publishing needs a case, so an Open round without cases is put in directly.
    empty = make_round("Synthetic empty", Round.State.OPEN)
    html = page(coord_client.get(retest_url(empty.pk)))
    assert "No test cases yet." in html
    assert "No acceptance criteria yet." not in html
