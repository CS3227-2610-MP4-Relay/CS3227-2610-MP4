"""RND-6: closing a round through its round page."""

from unittest import mock

import pytest
from django.db import DatabaseError, transaction
from django.db.models import QuerySet
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import escape

from rounds import services
from rounds import urls as rounds_urls
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import (
    DENIED,
    NOT_FOUND,
    UNAVAILABLE,
    csrf_token,
    detail,
    page,
    race,
    signed_in,
)

pytestmark = pytest.mark.django_db

CLOSED = "Round closed."
WARNING = "Closing makes this round read-only. It cannot be reopened."
BUTTON = "Close round</button>"
CONFLICT = "This action is not available while the round is {}."
FSI, PDI, RLO, ZWSP, LF = chr(0x2068), chr(0x2069), chr(0x202E), chr(0x200B), chr(10)
MARKUP = "<script>alert(1)</script>\"'><img src=x onerror=alert(2)>&amp;"
BIDI_AND_INVISIBLE = "abc" + RLO + "def" + ZWSP + "ghi" + chr(0x2066)
RND2_AND_RND3_CONTROLS = (
    "Edit round",
    "Add acceptance criterion",
    "Add test case",
    "Edit criterion",
    "Delete criterion",
    "Edit test case",
    "Delete test case",
    "Publish round",
    "Build label",
)


def close_url(round_id):
    return f"/coordinator/rounds/{round_id}/close/"


def published(round_, cases=2, criterion="Synthetic criterion", label="Synthetic 1.0"):
    """Give `round_` a criterion and `cases` linked cases, then publish it."""
    linked = Criterion.objects.create(round=round_, text=criterion)
    for n in range(cases):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {n}",
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


def stays_open(round_):
    round_.refresh_from_db()
    assert (round_.state, round_.closed_at) == (Round.State.OPEN, None)


@pytest.fixture
def opened(make_round):
    return published(make_round("Synthetic open round"))


# RND-6.1


@pytest.mark.ac("RND-6.1")
def test_closing_an_open_round_redirects_and_closes_it(coord_client, opened):
    before = everything()[1:]
    response = coord_client.post(close_url(opened.pk))
    assert response.status_code == 302
    assert response["Location"] == detail(opened.pk)
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED and opened.closed_at is not None
    assert everything()[1:] == before


@pytest.mark.ac("RND-6.1")
def test_closed_round_page_shows_the_message_once_and_everything_without_controls(
    coord_client, opened
):
    coord_client.post(close_url(opened.pk))
    html = page(coord_client.get(detail(opened.pk)))
    assert html.count(CLOSED) == 1
    assert html.index("</h1>") < html.index(CLOSED) < html.index("<p>State: Closed</p>")
    assert "Synthetic criterion" in html
    label = '<span dir="auto">Synthetic 1.0</span>'
    for n in range(2):
        case_at = html.index(f'<h3><span dir="auto">Synthetic case {n}</span></h3>')
        build_at = html.index("<h4>Current build</h4>", case_at)
        assert html.index("<h4>Linked acceptance criteria</h4>", case_at) < build_at
        assert html.index(label, build_at) < html.index("<h2>Builds</h2>")
    builds = html[html.index("<h2>Builds</h2>") :]
    assert f"<h3>{label}</h3>" in builds and "<h4>Covered test cases</h4>" in builds
    assert "Synthetic case 0" in builds and "Synthetic case 1" in builds
    for control in (*RND2_AND_RND3_CONTROLS, WARNING, "Close round", "<form"):
        assert control not in html, control
    assert CLOSED not in page(coord_client.get(detail(opened.pk)))


# RND-6.2


@pytest.mark.ac("RND-6.2")
def test_open_round_page_shows_the_warning_directly_before_the_close_button(
    coord_client, opened
):
    html = page(coord_client.get(detail(opened.pk)))
    assert html.count(WARNING) == 1 and html.count(BUTTON) == 1
    warning = html.index(f"<p>{WARNING}</p>")
    form = html.index(f'<form method="post" action="{close_url(opened.pk)}">')
    assert html.index("<h2>Builds</h2>") < warning < form < html.index(BUTTON)
    assert html.index(BUTTON) < html.index("Coordinator home")
    # Nothing but the form's start sits between the warning and the form.
    assert html[warning + len(f"<p>{WARNING}</p>") : form].strip() == ""
    assert "Publish round" not in html and "Edit round" not in html


@pytest.mark.ac("RND-6.2")
def test_draft_round_page_has_no_warning_or_close_button(coord_client, make_round):
    html = page(coord_client.get(detail(make_round("Synthetic draft").pk)))
    assert WARNING not in html and "Close round" not in html


@pytest.mark.ac("RND-6.2")
def test_a_round_with_untested_cases_closes(coord_client, make_round):
    # No results exist (RES), so every case is untested.
    untested = published(make_round("Synthetic untested"), cases=1)
    assert coord_client.post(close_url(untested.pk)).status_code == 302
    untested.refresh_from_db()
    assert untested.state == Round.State.CLOSED


# RND-6.3


@pytest.mark.ac("RND-6.3")
def test_closing_a_closed_round_gets_409_and_changes_nothing(coord_client, opened):
    coord_client.post(close_url(opened.pk))
    before = everything()
    response = coord_client.post(close_url(opened.pk))
    assert response.status_code == 409
    html = page(response)
    assert "<title>Action not available</title>" in html
    assert f"<h1>{CONFLICT.format('Closed')}</h1>" in html
    no_store(response)
    assert everything() == before


@pytest.mark.ac("RND-6.3")
def test_no_rounds_route_returns_a_closed_round_to_open_or_draft(coordinator, opened):
    case = opened.cases.first()
    criterion = opened.criteria.first()
    client = signed_in(coordinator, enforce_csrf_checks=True)
    token = csrf_token(client)
    client.post(close_url(opened.pk), HTTP_X_CSRFTOKEN=token)
    before = everything()
    ids = {"round_id": opened.pk, "criterion_id": criterion.pk, "case_id": case.pk}
    data = {"title": "Synthetic", "text": "Synthetic", "label": "Synthetic 2.0"}
    for pattern in rounds_urls.urlpatterns:
        kwargs = {name: ids[name] for name in pattern.pattern.converters}
        url = reverse(f"rounds:{pattern.name}", kwargs=kwargs)
        client.get(url)
        response = client.post(url, data, HTTP_X_CSRFTOKEN=token)
        if pattern.name != "new":
            assert response.status_code in (405, 409), url
    # Only "new" may add a round; this round and its records are unchanged.
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED
    assert list(Round.objects.filter(pk=opened.pk).values()) == [
        row for row in before[0] if row["id"] == opened.pk
    ]
    assert everything()[1:] == before[1:]
    html = page(client.get(detail(opened.pk)))
    assert "<form" not in html and "<p>State: Closed</p>" in html


# RND-6.4


def close(round_):
    return lambda client: client.post(close_url(round_.pk))


@pytest.mark.ac("RND-6.4")
@pytest.mark.django_db(transaction=True)
def test_of_two_closes_exactly_one_succeeds(coordinator):
    opened = published(
        Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    )
    first, second = race(coordinator, close(opened), close(opened), ["close"])
    assert (first.status_code, second.status_code) == (302, 409)
    assert CONFLICT.format("Closed") in page(second)
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED
    closed_at = opened.closed_at
    assert closed_at is not None
    # The loser wrote nothing: a further close is refused and keeps the time.
    third = signed_in(coordinator).post(close_url(opened.pk))
    assert third.status_code == 409
    opened.refresh_from_db()
    assert opened.closed_at == closed_at


@pytest.mark.ac("RND-6.4")
@pytest.mark.django_db(transaction=True)
def test_the_losing_close_keeps_the_winners_closing_time(coordinator):
    opened = published(
        Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    )
    times = []
    real = services.close

    def recording(round_):
        real(round_)
        times.append(round_.closed_at)

    with mock.patch.object(services, "close", recording):
        race(coordinator, close(opened), close(opened), ["close"])
    assert len(times) == 1
    opened.refresh_from_db()
    assert opened.closed_at == times[0]


# RND-6.5


@pytest.mark.ac("RND-6.5")
@pytest.mark.parametrize("signed", [True, False])
def test_get_head_and_put_get_405_uncached(coordinator, opened, signed):
    client = signed_in(coordinator) if signed else Client()
    for method in ("get", "head", "put"):
        response = getattr(client, method)(close_url(opened.pk))
        assert response.status_code == 405, method
        no_store(response)
    stays_open(opened)


@pytest.mark.ac("RND-6.5")
@pytest.mark.parametrize(
    "token, origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_post_without_valid_csrf_or_same_origin_gets_403(
    coordinator, opened, token, origin
):
    client = signed_in(coordinator, enforce_csrf_checks=True)
    data = {}
    if token != "missing":
        data["csrfmiddlewaretoken"] = (
            csrf_token(client) if token == "valid" else "x" * 32
        )
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    response = client.post(close_url(opened.pk), data, **extra)
    assert response.status_code == 403
    assert DENIED in page(response)
    stays_open(opened)


@pytest.mark.ac("RND-6.5")
def test_signed_out_visitor_is_redirected_to_sign_in(opened):
    client = Client(enforce_csrf_checks=True)
    token = csrf_token(client)
    for round_id in (opened.pk, opened.pk + 1000):
        response = client.post(close_url(round_id), {"csrfmiddlewaretoken": token})
        assert response.status_code == 302
        assert response["Location"] == "/sign-in/"
    stays_open(opened)


@pytest.mark.ac("RND-6.5")
def test_tester_gets_the_same_403_for_existing_and_missing_rounds(tester, opened):
    client = signed_in(tester)
    with mock.patch("rounds.views.get_object_or_404") as lookup:
        first = client.post(close_url(opened.pk))
        second = client.post(close_url(opened.pk + 1000))
    lookup.assert_not_called()
    assert first.status_code == second.status_code == 403
    assert first.content == second.content and DENIED in page(first)
    stays_open(opened)


@pytest.mark.ac("RND-6.5")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_another_workspaces_round_gets_404_not_409(
    coord_client, make_round, other_workspace, state
):
    foreign = make_round("Synthetic foreign", state, owner=other_workspace)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    for round_id in (foreign.pk, 999999):
        response = coord_client.post(close_url(round_id))
        assert response.status_code == 404
        assert response.content == reference.content
        assert NOT_FOUND in page(response)
    assert everything() == before


@pytest.mark.ac("RND-6.5")
def test_closing_a_draft_round_gets_409(coord_client, make_round):
    draft = make_round("Synthetic draft")
    before = everything()
    response = coord_client.post(close_url(draft.pk))
    assert response.status_code == 409
    assert f"<h1>{CONFLICT.format('Draft')}</h1>" in page(response)
    no_store(response)
    assert everything() == before


@pytest.mark.ac("RND-6.5")
def test_storage_failure_mid_close_gives_503_and_changes_nothing(
    coord_client, opened, caplog
):
    before = everything()
    # The close is one conditional UPDATE, so storage fails there.
    failing = mock.patch.object(
        QuerySet, "update", side_effect=DatabaseError("synthetic")
    )
    with failing:
        response = coord_client.post(close_url(opened.pk))
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    no_store(response)
    assert everything() == before
    stays_open(opened)
    logged = [record for record in caplog.records if record.name == "rounds.views"]
    assert len(logged) == 1 and logged[0].exc_info[0] is DatabaseError


@pytest.mark.ac("RND-6.5")
def test_injected_fields_are_ignored(coord_client, opened, make_round):
    other = published(make_round("Synthetic other"))
    data = {"round": other.pk, "state": "draft", "closed_at": "2020-01-01T00:00Z"}
    coord_client.post(close_url(opened.pk), data)
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED and opened.closed_at.year > 2020
    stays_open(other)


# Heading; criterion in its list and under the case; the case's title, steps,
# expected result and current build; the build label and the covered case's
# title in the builds list.
EVERY_PLACE = 9


def everywhere(make_round, text):
    """A published round with `text` in every user-written field it shows."""
    made = published(make_round(text), criterion=text, label=text, cases=1)
    Case.objects.filter(round=made).update(title=text, steps=text, expected_result=text)
    return made


def closed_page(client, round_):
    client.post(close_url(round_.pk))
    html = page(client.get(detail(round_.pk)))
    assert "<p>State: Closed</p>" in html
    return html


@pytest.mark.ac("RND-6.5")
def test_markup_on_the_closed_page_is_escaped(coord_client, make_round):
    html = closed_page(coord_client, everywhere(make_round, MARKUP))
    isolated = f'<span dir="auto">{escape(MARKUP)}</span>'
    assert html.count(isolated) == EVERY_PLACE
    assert "<script>" not in html and "<img" not in html
    title = html.split("<title>", 1)[1].split("</title>", 1)[0]
    assert title == FSI + escape(MARKUP) + PDI


@pytest.mark.ac("RND-6.5")
def test_closed_page_title_isolates_a_stray_pop_isolate(coord_client, make_round):
    made = published(make_round("Synthetic " + PDI + RLO + "Reversed"))
    html = closed_page(coord_client, made)
    title = html.split("<title>", 1)[1].split("</title>", 1)[0]
    assert title == FSI + "Synthetic Reversed" + PDI


@pytest.mark.ac("RND-6.5")
def test_line_breaks_on_the_closed_page_are_isolated_line_by_line(
    coord_client, make_round
):
    text = "Synthetic one" + LF + "two"
    html = closed_page(coord_client, everywhere(make_round, text))
    lines = '<span dir="auto">Synthetic one</span><br><span dir="auto">two</span>'
    assert html.count(lines) == EVERY_PLACE


@pytest.mark.ac("RND-6.5")
def test_bidi_and_zero_width_characters_stay_inside_their_element(
    coord_client, make_round
):
    text = BIDI_AND_INVISIBLE
    html = closed_page(coord_client, everywhere(make_round, text))
    isolated = f'<span dir="auto">{text}</span>'
    assert html.count(isolated) == EVERY_PLACE
    body = html.split("</title>", 1)[1]
    for char in (RLO, ZWSP, chr(0x2066)):
        assert char not in body.replace(isolated, ""), hex(ord(char))
    assert CLOSED in html


@pytest.mark.ac("RND-6.1")
def test_closed_page_does_not_show_the_closing_time(coord_client, opened):
    html = closed_page(coord_client, opened)
    opened.refresh_from_db()
    closed_at = timezone.localtime(opened.closed_at)
    for shown in (
        date_format(closed_at, "DATE_FORMAT"),
        date_format(closed_at, "SHORT_DATE_FORMAT"),
        closed_at.isoformat(),
        str(closed_at.year),
    ):
        assert shown not in html, shown


@pytest.mark.ac("RND-6.2")
def test_the_close_form_on_the_page_carries_a_working_csrf_token(coordinator, opened):
    client = signed_in(coordinator, enforce_csrf_checks=True)
    html = page(client.get(detail(opened.pk)))
    form = html[html.index(f'action="{close_url(opened.pk)}"') :]
    form = form[: form.index("</form>")]
    token = form.split('name="csrfmiddlewaretoken" value="', 1)[1].split('"', 1)[0]
    response = client.post(close_url(opened.pk), {"csrfmiddlewaretoken": token})
    assert response.status_code == 302
    opened.refresh_from_db()
    assert opened.state == Round.State.CLOSED
