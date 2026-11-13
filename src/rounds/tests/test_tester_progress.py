"""RES-1.1 grouping and RES-1.9 to RES-1.12: a tester's own progress."""

import re
from datetime import timedelta

import pytest
from django.db import OperationalError, connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.html import escape

from rounds import services
from rounds.models import BuildCase, Result, Round

from .conftest import (
    MARKUP,
    UNAVAILABLE,
    assert_no_raw_markup,
    domain_rows,
    no_store,
    page,
    signed_in,
)
from .test_coordinator_overview import add_cases, make_testers, opened, stable
from .test_review import lock_and

pytestmark = pytest.mark.django_db
HOME = "/tester/"
OPEN_HEADING, CLOSED_HEADING = "<h3>Open tests</h3>", "<h3>Closed tests</h3>"
OVERVIEW = '<p class="round-overview">'
STATUS = {
    "Record result": "Not recorded",
    "Continue draft": "Draft",
    "View result": "Submitted",
}


def detail(round_):
    return f"/tester/rounds/{round_.pk}/"


def entry(html, round_):
    """The round's Tester home entry."""
    start = html.index(f'<li><a href="{detail(round_)}">')
    return html[start : html.index("</li>", start) + len("</li>")]


def progress(text):
    return f"(Open){OVERVIEW}{text}</p></li>"


def draft(tester, case, build):
    return Result.objects.create(tester=tester, case=case, build=build, outcome="pass")


def submitted(tester, case, build):
    return Result.objects.create(
        tester=tester,
        case=case,
        build=build,
        outcome="pass",
        submitted_at=timezone.now(),
    )


def statuses(html):
    """Each case's (title, summary status or None, body action or None)."""
    found = []
    for block in html.split('<details class="record"')[1:]:
        summary, body = block.split("</summary>", 1)
        title = re.search(r'<h3><span dir="auto">([^<]*)</span></h3>', summary)[1]
        status = re.search(
            r'<span class="record-meta">Your result: ([^<]+)</span>', summary
        )
        action = re.search(r">(Record result|Continue draft|View result)</a>", body)
        found.append((title, status and status[1], action and action[1]))
    return found


def assert_status_matches_action(html, expected):
    shown = statuses(html)
    assert [status for _, status, _ in shown] == expected
    for _, status, action in shown:
        assert status == STATUS[action]


def closed(round_):
    lock_and(round_, services.close)
    round_.refresh_from_db()
    return round_


# RES-1.9


@pytest.mark.ac("RES-1.9")
def test_open_round_shows_own_counts_and_case_status(tester, make_round):
    reference, old_cases, old_build = opened(make_round, 1, "Synthetic reference")
    submitted(tester, old_cases[0], old_build)
    closed(reference)
    round_, cases, build = opened(make_round, 5)
    draft(tester, cases[1], build)
    submitted(tester, cases[2], build)
    submitted(tester, cases[4], build)
    client = signed_in(tester)
    home = page(client.get(HOME))
    assert home.index(OPEN_HEADING) < home.index(f'href="{detail(round_)}"')
    assert home.index(f'href="{detail(round_)}"') < home.index(CLOSED_HEADING)
    assert home.index(CLOSED_HEADING) < home.index(f'href="{detail(reference)}"')
    assert entry(home, round_).endswith(progress("2 to record · 1 draft · 2 submitted"))
    assert entry(home, reference).endswith("</a> (Closed)</li>")
    assert_status_matches_action(
        page(client.get(detail(round_))),
        ["Not recorded", "Draft", "Submitted", "Not recorded", "Submitted"],
    )


@pytest.mark.ac("RES-1.1")
def test_open_rounds_precede_closed_rounds_each_newest_first(tester, make_round):
    rounds = {
        name: make_round(f"Synthetic {name}", state)
        for name, state in (
            ("old open", Round.State.OPEN),
            ("old closed", Round.State.CLOSED),
            ("tied closed", Round.State.CLOSED),
            ("new open", Round.State.OPEN),
            ("new closed", Round.State.CLOSED),
        )
    }
    now = timezone.now()
    for age, names in enumerate(
        (["new open", "new closed"], ["tied closed", "old closed"], ["old open"])
    ):
        Round.objects.filter(pk__in=[rounds[name].pk for name in names]).update(
            created_at=now - timedelta(days=age)
        )
    response = signed_in(tester).get(HOME)
    # "tied closed" was created after "old closed", so its higher ID comes first.
    expected = [
        rounds[name]
        for name in ("new open", "old open", "new closed", "tied closed", "old closed")
    ]
    assert list(response.context["rounds"]) == expected
    html = page(response)
    positions = [html.index(f'href="{detail(round_)}"') for round_ in expected]
    assert positions == sorted(positions)
    assert html.index(OPEN_HEADING) < positions[0] < positions[1]
    assert positions[1] < html.index(CLOSED_HEADING) < positions[2]


# RES-1.10


@pytest.mark.ac("RES-1.10")
@pytest.mark.parametrize(
    ("drafts", "submits", "text"),
    [
        (0, 0, "3 to record · 0 drafts · 0 submitted"),
        (0, 3, "0 to record · 0 drafts · 3 submitted"),
        (1, 0, "2 to record · 1 draft · 0 submitted"),
        (2, 1, "0 to record · 2 drafts · 1 submitted"),
    ],
)
def test_count_line_always_shows_all_three_numbers(
    tester, make_round, drafts, submits, text
):
    round_, cases, build = opened(make_round, 3)
    for case in cases[:drafts]:
        draft(tester, case, build)
    for case in cases[drafts : drafts + submits]:
        submitted(tester, case, build)
    home = page(signed_in(tester).get(HOME))
    assert entry(home, round_).endswith(progress(text))


@pytest.mark.ac("RES-1.10")
@pytest.mark.parametrize("states", [["open"], ["closed"], [], ["draft"]])
def test_group_headings_appear_only_for_groups_with_rounds(tester, make_round, states):
    for state in states:
        make_round(f"Synthetic {state}", state)
    html = page(signed_in(tester).get(HOME))
    assert "<h2>Available tests</h2>" in html
    assert (OPEN_HEADING in html) == ("open" in states)
    assert (CLOSED_HEADING in html) == ("closed" in states)
    assert ("<p>No tests available.</p>" in html) == (
        "open" not in states and "closed" not in states
    )


@pytest.mark.ac("RES-1.10")
def test_closed_round_shows_no_counts_or_status_even_with_saved_results(
    tester, make_round
):
    round_, cases, build = opened(make_round, 2)
    draft(tester, cases[0], build)
    submitted(tester, cases[1], build)
    closed(round_)
    client = signed_in(tester)
    home = page(client.get(HOME))
    assert entry(home, round_).endswith("</a> (Closed)</li>")
    assert OVERVIEW not in home
    html = page(client.get(detail(round_)))
    assert "Your result" not in html
    assert [status for _, status, _ in statuses(html)] == [None, None]


# RES-1.11


@pytest.mark.ac("RES-1.11")
def test_retest_puts_selected_cases_back_to_record(tester, make_round):
    round_, cases, build = opened(make_round, 3)
    for case in cases:
        submitted(tester, case, build)
    client = signed_in(tester)

    def check(text, expected):
        home = page(client.get(HOME))
        assert entry(home, round_).endswith(progress(text))
        assert_status_matches_action(page(client.get(detail(round_))), expected)

    check("0 to record · 0 drafts · 3 submitted", ["Submitted"] * 3)
    retest = lock_and(round_, services.request_retest, "Synthetic 2.0", [cases[0].pk])
    check(
        "1 to record · 0 drafts · 2 submitted",
        ["Not recorded", "Submitted", "Submitted"],
    )
    saved = draft(tester, cases[0], retest)
    check("0 to record · 1 draft · 2 submitted", ["Draft", "Submitted", "Submitted"])
    Result.objects.filter(pk=saved.pk).update(submitted_at=timezone.now())
    check("0 to record · 0 drafts · 3 submitted", ["Submitted"] * 3)


@pytest.mark.ac("RES-1.11")
def test_earlier_and_foreign_build_rows_never_count(tester, make_round):
    round_, cases, build = opened(make_round, 2)
    _, _, other_build = opened(make_round, 1, "Synthetic other round")
    BuildCase.objects.create(build=other_build, case=cases[1])
    submitted(tester, cases[1], other_build)
    submitted(tester, cases[0], build)
    lock_and(round_, services.request_retest, "Synthetic 2.0", [cases[0].pk])
    client = signed_in(tester)
    home = page(client.get(HOME))
    assert entry(home, round_).endswith(
        progress("2 to record · 0 drafts · 0 submitted")
    )
    assert_status_matches_action(
        page(client.get(detail(round_))), ["Not recorded", "Not recorded"]
    )


# RES-1.12


@pytest.mark.ac("RES-1.12")
def test_another_testers_rows_change_nothing(tester, make_round, workspace):
    (peer,) = make_testers(workspace, 1)
    round_, cases, build = opened(make_round, 2)
    client = signed_in(tester)
    home_before = stable(page(client.get(HOME)))
    detail_before = page(client.get(detail(round_)))
    draft(peer, cases[0], build)
    submitted(peer, cases[1], build)
    assert stable(page(client.get(HOME))) == home_before
    assert page(client.get(detail(round_))) == detail_before
    assert "2 to record · 0 drafts · 0 submitted" in home_before
    peer_home = page(signed_in(peer).get(HOME))
    assert "0 to record · 1 draft · 1 submitted" in peer_home


@pytest.mark.ac("RES-1.12")
def test_other_workspaces_never_appear_or_count(tester, make_round, other_workspace):
    (outsider,) = make_testers(other_workspace, 1, "tester-outsider")
    foreign, foreign_cases, foreign_build = opened(
        make_round, 1, "Synthetic foreign", owner=other_workspace
    )
    submitted(outsider, foreign_cases[0], foreign_build)
    round_, cases, _ = opened(make_round, 1)
    BuildCase.objects.create(build=foreign_build, case=cases[0])
    submitted(tester, cases[0], foreign_build)
    home = page(signed_in(tester).get(HOME))
    assert "Synthetic foreign" not in home and f'href="{detail(foreign)}"' not in home
    assert entry(home, round_).endswith(
        progress("1 to record · 0 drafts · 0 submitted")
    )


@pytest.mark.ac("RES-1.12")
def test_query_parameters_select_nothing(tester, make_round, workspace):
    (peer,) = make_testers(workspace, 1)
    round_, cases, build = opened(make_round, 2)
    submitted(peer, cases[0], build)
    draft(tester, cases[1], build)
    client = signed_in(tester)
    forged = {"tester": peer.pk, "round": round_.pk, "build": build.pk, "state": "x"}
    for url in (HOME, detail(round_)):
        plain = stable(page(client.get(url)))
        assert stable(page(client.get(url, forged))) == plain
    assert "1 to record · 1 draft · 0 submitted" in page(client.get(HOME, forged))


@pytest.mark.ac("RES-1.12")
@pytest.mark.parametrize("method", ["head", "post", "put", "delete"])
@pytest.mark.parametrize("detail_page", [False, True])
def test_pages_stay_get_only_uncached_and_read_only(
    tester, make_round, method, detail_page
):
    round_, cases, build = opened(make_round, 2)
    draft(tester, cases[0], build)
    url = detail(round_) if detail_page else HOME
    client = signed_in(tester)
    before = domain_rows()
    refused = getattr(client, method)(url)
    assert refused.status_code == 405
    no_store(refused)
    shown = client.get(url)
    assert shown.status_code == 200
    no_store(shown)
    assert domain_rows() == before


@pytest.mark.ac("RES-1.12")
@pytest.mark.parametrize("detail_page", [False, True])
def test_storage_failure_reading_results_returns_503_without_round_content(
    tester, make_round, detail_page
):
    round_, cases, build = opened(make_round, 2)
    draft(tester, cases[0], build)
    url = detail(round_) if detail_page else HOME
    client = signed_in(tester)

    def fail(execute, sql, params, many, context):
        if '"rounds_result"' in sql:
            raise OperationalError("Synthetic unavailable storage")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(fail):
        response = client.get(url)
    assert response.status_code == 503
    html = page(response)
    assert UNAVAILABLE in html and round_.title not in html
    assert "to record" not in html and "Your result" not in html
    no_store(response)


@pytest.mark.ac("RES-1.12")
def test_round_title_keeps_rendering_rule_next_to_count_line(tester, make_round):
    round_, _, _ = opened(make_round, 1, MARKUP + "\nSynthetic second line")
    html = page(signed_in(tester).get(HOME))
    assert_no_raw_markup(html)
    assert entry(html, round_) == (
        f'<li><a href="{detail(round_)}"><span dir="auto">{escape(MARKUP)}</span><br>'
        '<span dir="auto">Synthetic second line</span></a> '
        + progress("1 to record · 0 drafts · 0 submitted")
    )


@pytest.mark.ac("RES-1.12")
def test_home_query_count_does_not_grow_with_cases_or_results(
    tester, make_round, workspace
):
    round_, cases, build = opened(make_round, 1)
    client = signed_in(tester)

    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert client.get(HOME).status_code == 200
        return len(captured)

    small = queries()
    (peer,) = make_testers(workspace, 1)
    for case in add_cases(round_, 3):
        BuildCase.objects.create(build=build, case=case)
        submitted(tester, case, build)
        draft(peer, case, build)
    lock_and(round_, services.request_retest, "Synthetic 2.0", [cases[0].pk])
    assert queries() == small
