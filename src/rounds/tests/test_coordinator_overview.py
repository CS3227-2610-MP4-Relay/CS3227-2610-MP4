"""RND-1.8 to RND-1.11: the Coordinator home's workspace overview."""

import re
from unittest import mock

import pytest
from django.db import DatabaseError, connection
from django.test.utils import CaptureQueriesContext
from django.utils.html import escape

from accounts.models import User
from rounds import results, services
from rounds.models import Build, BuildCase, Case, Criterion, Result, Round

from .conftest import (
    MARKUP,
    PASSWORD,
    assert_no_raw_markup,
    detail,
    domain_rows,
    no_store,
    page,
)
from .test_review import T1, T2, lock_and, submit

pytestmark = pytest.mark.django_db
HOME = "/coordinator/"
OVERVIEW = '<p class="round-overview">'


def results_url(round_):
    return f"/coordinator/rounds/{round_.pk}/results/"


def summary(draft, open_, closed, testers):
    return (
        f"<p>Draft: {draft} · Open: {open_} · Closed: {closed} · "
        f"Beta Testers: {testers}</p>"
    )


def coverage(round_, text):
    """An Open round's overview line with its results link."""
    return (
        f"{OVERVIEW}{text} "
        f'<a class="action secondary" href="{results_url(round_)}">Review results</a>'
        "</p></li>"
    )


def add_cases(round_, count):
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    cases = []
    for index in range(count):
        case = Case.objects.create(
            round=round_,
            title=f"Synthetic case {index}",
            steps="Synthetic steps",
            expected_result="Synthetic expected",
        )
        case.criteria.add(criterion)
        cases.append(case)
    return cases


def opened(make_round, count, title="Synthetic open round", **kwargs):
    """An Open round with `count` cases, published on build Synthetic 1.0."""
    round_ = make_round(title, **kwargs)
    cases = add_cases(round_, count)
    build = lock_and(round_, services.publish, "Synthetic 1.0")
    round_.refresh_from_db()
    return round_, cases, build


def make_testers(workspace, count, prefix="tester-extra"):
    return [
        User.objects.create_user(
            f"{prefix}{index}", PASSWORD, workspace=workspace, role="tester"
        )
        for index in range(count)
    ]


def stable(html):
    """The page without its per-render CSRF tokens."""
    return re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", html)


def entry(html, round_):
    """The round's list entry."""
    start = html.index(f'<li><a href="{detail(round_.pk)}">')
    return html[start : html.index("</li>", start) + len("</li>")]


# RND-1.8


@pytest.mark.ac("RND-1.8")
def test_overview_summarises_states_testers_and_each_rounds_progress(
    coord_client, make_round, workspace, tester
):
    make_testers(workspace, 1)
    make_round("Synthetic older closed", Round.State.CLOSED)
    make_round("Synthetic newer closed", Round.State.CLOSED)
    open_, cases, build = opened(make_round, 5)
    for case in cases[:3]:
        submit(tester, case, build)
    draft = make_round("Synthetic draft round")
    add_cases(draft, 4)
    html = page(coord_client.get(HOME))
    line = summary(1, 1, 2, 2)
    new_round = '<a class="action" href="/coordinator/rounds/new/">New round</a>'
    assert html.count(line) == 1
    assert html.index(new_round) < html.index(line) < html.index("<ul>")
    assert entry(html, draft).endswith(f"(Draft){OVERVIEW}4 test cases</p></li>")
    assert entry(html, open_).endswith(
        "(Open)"
        + coverage(
            open_, "3 of 5 test cases have a submitted result for their current build."
        )
    )
    for closed in Round.objects.filter(state=Round.State.CLOSED):
        assert entry(html, closed).endswith("</a> (Closed)</li>")
    assert html.count("Review results") == 1
    review = coord_client.get(results_url(open_))
    assert review.status_code == 200
    assert "<h1>Results: " in page(review)


# RND-1.9


@pytest.mark.ac("RND-1.9")
def test_no_rounds_shows_zero_counts_before_the_empty_text(
    coord_client, workspace, tester
):
    make_testers(workspace, 1)
    html = page(coord_client.get(HOME))
    line = summary(0, 0, 0, 2)
    assert html.index(line) < html.index("<p>No rounds yet.</p>")


@pytest.mark.ac("RND-1.9")
def test_draft_only_workspace_shows_case_counts_and_no_results_link(
    coord_client, make_round
):
    empty = make_round("Synthetic empty draft")
    single = make_round("Synthetic single draft")
    add_cases(single, 1)
    html = page(coord_client.get(HOME))
    assert summary(2, 0, 0, 0) in html
    assert entry(html, empty).endswith(f"(Draft){OVERVIEW}0 test cases</p></li>")
    assert entry(html, single).endswith(f"(Draft){OVERVIEW}1 test case</p></li>")
    assert "Review results" not in html


@pytest.mark.ac("RND-1.9")
@pytest.mark.parametrize(
    ("submitted", "total", "text"),
    [
        (0, 2, "0 of 2 test cases have a submitted result for their current build."),
        (1, 2, "1 of 2 test cases has a submitted result for its current build."),
        (1, 1, "1 of 1 test case has a submitted result for its current build."),
        (2, 2, "2 of 2 test cases have a submitted result for their current build."),
    ],
)
def test_open_round_line_agrees_with_its_counts(
    coord_client, make_round, tester, submitted, total, text
):
    round_, cases, build = opened(make_round, total)
    for case in cases[:submitted]:
        submit(tester, case, build)
    html = page(coord_client.get(HOME))
    assert entry(html, round_).endswith("(Open)" + coverage(round_, text))


@pytest.mark.ac("RND-1.9")
def test_a_case_submitted_by_two_testers_counts_once(
    coord_client, make_round, workspace, tester
):
    (second,) = make_testers(workspace, 1)
    _, cases, build = opened(make_round, 2)
    submit(tester, cases[0], build, T1)
    submit(second, cases[0], build, T2)
    html = page(coord_client.get(HOME))
    assert "1 of 2 test cases has a submitted result for its current build." in html


# RND-1.10


@pytest.mark.ac("RND-1.10")
def test_only_results_the_results_page_lists_for_current_builds_count(
    coord_client, make_round, tester, other_workspace
):
    round_, cases, build = opened(make_round, 2)
    _, _, other_build = opened(make_round, 1, "Synthetic other round")
    _, _, foreign_build = opened(
        make_round, 1, "Synthetic foreign round", owner=other_workspace
    )
    Result.objects.create(tester=tester, case=cases[0], build=build, outcome="pass")
    # A build of another round forged to cover this round's case.
    BuildCase.objects.create(build=other_build, case=cases[0])
    submit(tester, cases[0], other_build)
    # A build of this round that does not cover the case.
    uncovered = lock_and(
        round_, services.request_retest, "Synthetic 2.0", [cases[1].pk]
    )
    submit(tester, cases[0], uncovered)
    (outsider,) = make_testers(other_workspace, 1, "tester-outsider")
    submit(outsider, cases[0], build)
    BuildCase.objects.create(build=foreign_build, case=cases[0])
    submit(tester, cases[0], foreign_build)
    # cases[1]'s only submission is for its earlier build.
    submit(tester, cases[1], build)
    html = page(coord_client.get(HOME))
    assert entry(html, round_).endswith(
        "(Open)"
        + coverage(
            round_, "0 of 2 test cases have a submitted result for their current build."
        )
    )
    assert "Synthetic foreign round" not in html


@pytest.mark.ac("RND-1.10")
def test_a_retest_drops_selected_cases_until_their_new_build_is_submitted(
    coord_client, make_round, tester
):
    round_, cases, build = opened(make_round, 2)
    for case in cases:
        submit(tester, case, build)

    def line():
        return entry(page(coord_client.get(HOME)), round_)

    assert "2 of 2 test cases have" in line()
    retest = lock_and(round_, services.request_retest, "Synthetic 2.0", [cases[0].pk])
    assert "1 of 2 test cases has" in line()
    draft = Result.objects.create(
        tester=tester, case=cases[0], build=retest, outcome="fail"
    )
    assert "1 of 2 test cases has" in line()
    Result.objects.filter(pk=draft.pk).update(submitted_at=T2)
    assert "2 of 2 test cases have" in line()


@pytest.mark.ac("RND-1.10", "RND-4.4")
def test_overview_and_results_page_share_one_result_selection(
    coord_client, make_round, tester
):
    round_, cases, build = opened(make_round, 1)
    submit(tester, cases[0], build)
    with mock.patch(
        "rounds.results.listed_results", wraps=results.listed_results
    ) as listed:
        coord_client.get(HOME)
        coord_client.get(results_url(round_))
    assert [call.args for call in listed.call_args_list] == [(round_,), (round_,)]


# RND-1.11


@pytest.mark.ac("RND-1.11")
def test_other_workspaces_never_change_a_count(
    coord_client, make_round, tester, other_workspace
):
    make_testers(other_workspace, 3, "tester-foreign")
    _, foreign_cases, foreign_build = opened(
        make_round, 2, "Synthetic foreign open", owner=other_workspace
    )
    make_round("Synthetic foreign draft", owner=other_workspace)
    make_round("Synthetic foreign closed", Round.State.CLOSED, owner=other_workspace)
    round_, _, _ = opened(make_round, 2)
    (foreign_tester,) = User.objects.filter(username="tester-foreign0")
    submit(foreign_tester, foreign_cases[0], foreign_build)
    html = page(coord_client.get(HOME))
    assert summary(0, 1, 0, 1) in html
    assert "0 of 2 test cases have" in entry(html, round_)
    assert "Synthetic foreign" not in html


@pytest.mark.ac("RND-1.11")
def test_a_draft_changes_nothing_on_the_page(coord_client, make_round, tester):
    _, cases, build = opened(make_round, 2)
    before = stable(page(coord_client.get(HOME)))
    assert "0 of 2 test cases have" in before
    Result.objects.create(
        tester=tester,
        case=cases[0],
        build=build,
        outcome="fail",
        observation="Synthetic private draft",
    )
    assert stable(page(coord_client.get(HOME))) == before


@pytest.mark.ac("RND-1.11")
def test_query_parameters_select_nothing(
    coord_client, make_round, tester, other_workspace
):
    _, cases, build = opened(make_round, 2)
    submit(tester, cases[0], build)
    foreign = make_round("Synthetic foreign", owner=other_workspace)
    plain = stable(page(coord_client.get(HOME)))
    assert "1 of 2 test cases has" in plain and "Synthetic foreign" not in plain
    forged = coord_client.get(
        HOME,
        {
            "workspace": other_workspace.pk,
            "round": foreign.pk,
            "state": "closed",
            "build": build.pk,
            "tester": tester.pk,
        },
    )
    assert stable(page(forged)) == plain


@pytest.mark.ac("RND-1.11")
@pytest.mark.parametrize("method", ["head", "post", "put", "delete"])
def test_page_stays_get_only_and_uncached(coord_client, make_round, tester, method):
    _, cases, build = opened(make_round, 1)
    submit(tester, cases[0], build)
    before = domain_rows()
    response = getattr(coord_client, method)(HOME)
    assert response.status_code == 405
    no_store(response)
    shown = coord_client.get(HOME)
    assert shown.status_code == 200
    no_store(shown)
    assert domain_rows() == before


@pytest.mark.ac("RND-1.11")
def test_titles_keep_the_rendering_rule_next_to_the_overview(coord_client, make_round):
    draft = make_round(MARKUP)
    open_, _, _ = opened(make_round, 1, MARKUP + "\nSynthetic second line")
    html = page(coord_client.get(HOME))
    assert_no_raw_markup(html)
    shown = f'<span dir="auto">{escape(MARKUP)}</span>'
    assert entry(html, draft).startswith(
        f'<li><a href="{detail(draft.pk)}">{shown}</a> (Draft){OVERVIEW}'
    )
    assert entry(html, open_).startswith(
        f'<li><a href="{detail(open_.pk)}">{shown}<br>'
        '<span dir="auto">Synthetic second line</span></a> (Open)'
    )


@pytest.mark.ac("RND-1.11")
def test_storage_failure_reading_progress_shows_no_partial_overview(
    coord_client, make_round
):
    opened(make_round, 1)
    coord_client.raise_request_exception = False
    with mock.patch(
        "rounds.results.current_build_coverage",
        side_effect=DatabaseError("synthetic"),
    ):
        response = coord_client.get(HOME)
    assert response.status_code == 500
    html = page(response)
    assert "Draft:" not in html and "Synthetic open round" not in html


@pytest.mark.ac("RND-1.11")
def test_query_count_does_not_grow_with_cases_or_results(
    coord_client, make_round, workspace, tester
):
    round_, cases, build = opened(make_round, 1)

    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert coord_client.get(HOME).status_code == 200
        return len(captured)

    small = queries()
    (second,) = make_testers(workspace, 1)
    for case in add_cases(round_, 3):
        BuildCase.objects.create(build=build, case=case)
        submit(tester, case, build, T1)
        submit(second, case, build, T2)
    lock_and(round_, services.request_retest, "Synthetic 2.0", [cases[0].pk])
    assert Build.objects.filter(round=round_).count() == 2
    assert queries() == small
