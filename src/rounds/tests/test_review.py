"""RND-4: the coordinator's read-only results page for an Open or Closed round."""

from datetime import UTC, datetime
from unittest import mock

import pytest
from django.db import OperationalError, connection, transaction
from django.db.models.query import QuerySet
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.html import escape

from accounts.models import User
from rounds import services
from rounds import views as round_views
from rounds.models import (
    Build,
    BuildCase,
    Case,
    CaseCriterion,
    Criterion,
    Result,
    Round,
)

from .conftest import (
    DENIED,
    IMG_TAG,
    MARKUP,
    NOT_FOUND,
    PASSWORD,
    SCRIPT_TAG,
    UNAVAILABLE,
    csrf_token,
    detail,
    page,
    signed_in,
)
from .test_result_services import snapshot

pytestmark = pytest.mark.django_db

FSI, PDI = "\u2068", "\u2069"
LINK = "Review results"
EMPTY = "No results for this build yet."
CONFLICT = "This action is not available while the round is {}."
T1 = datetime(2026, 10, 29, 1, 2, 3, tzinfo=UTC)
T2 = datetime(2026, 10, 30, 4, 5, 6, tzinfo=UTC)
T3 = datetime(2026, 10, 31, 7, 8, 9, tzinfo=UTC)


def results_url(round_id):
    """The intended results path, named before its route exists."""
    return f"/coordinator/rounds/{round_id}/results/"


def title_tag(html):
    return html.split("<title>", 1)[1].split("</title>", 1)[0]


def span(text):
    """One line of user text as the per-line rendering filter shows it."""
    return f'<span dir="auto">{escape(text)}</span>'


def no_store(response):
    assert "no-store" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def lock_and(round_, action, *args):
    """Run a round service under the round lock, as its view does."""
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=round_.pk)
        return action(locked, *args)


def submit(tester, case, build, at=T1, outcome="pass", observation=""):
    """Store a submitted result directly (RES-2 owns the real submission)."""
    return Result.objects.create(
        tester=tester,
        case=case,
        build=build,
        outcome=outcome,
        observation=observation,
        submitted_at=at,
    )


class Review:
    """An Open round with two linked cases on build Synthetic 1.0."""

    def __init__(self, make_round, title="Synthetic review round"):
        self.round = make_round(title)
        self.first_criterion = Criterion.objects.create(
            round=self.round, text="Synthetic criterion one"
        )
        self.second_criterion = Criterion.objects.create(
            round=self.round, text="Synthetic criterion two"
        )
        self.case = self.add_case("Synthetic case A", self.second_criterion)
        CaseCriterion.objects.create(case=self.case, criterion=self.first_criterion)
        self.other_case = self.add_case("Synthetic case B", self.first_criterion)
        self.build = lock_and(self.round, services.publish, "Synthetic 1.0")
        self.round.refresh_from_db()

    def add_case(self, title, criterion):
        case = Case.objects.create(
            round=self.round,
            title=title,
            steps="Synthetic steps",
            expected_result="Synthetic expected",
        )
        CaseCriterion.objects.create(case=case, criterion=criterion)
        return case

    def retest(self, label, *cases):
        return lock_and(
            self.round, services.request_retest, label, [c.pk for c in cases]
        )

    def close(self):
        lock_and(self.round, services.close)
        self.round.refresh_from_db()


@pytest.fixture
def review(make_round):
    return Review(make_round)


@pytest.fixture
def second_tester(workspace):
    return User.objects.create_user(
        "tester2-rnd10001", PASSWORD, workspace=workspace, role="tester"
    )


def section(html, case_title, until=None):
    """The part of the results page for one case, up to the next case."""
    start = html.index(f"<h2>{span(case_title)}</h2>")
    end = html.index(until or "Back to round", start + 1)
    return html[start:end]


def result_lines(username, outcome, observation, at, build=None):
    """The lines one result shows, as RND-4 lists them."""
    lines = [f"<p>Build: {span(build)}</p>"] if build else []
    shown = span(observation) if observation else "No observation."
    lines += [
        f"<p>Tester: {span(username)}</p>",
        f"<p>Outcome: {outcome}</p>",
        f"<p>Observation: {shown}</p>",
        f"<p>Submitted at: {at:%Y-%m-%d %H:%M:%S} UTC</p>",
    ]
    return "\n".join(lines)


# RND-4.1


@pytest.mark.ac("RND-4.1", "RND-4.6")
@pytest.mark.parametrize("state", ["open", "closed"])
def test_round_page_links_to_results_under_its_state(coord_client, review, state):
    if state == "closed":
        review.close()
    html = page(coord_client.get(detail(review.round.pk)))
    label = state.capitalize()
    link = f'<p><a href="{results_url(review.round.pk)}">{LINK}</a></p>'
    assert f"<p>State: {label}</p>\n{link}" in html
    assert html.count(LINK) == 1


@pytest.mark.ac("RND-4.6")
def test_draft_round_page_has_no_results_link(coord_client, make_round):
    html = page(coord_client.get(detail(make_round().pk)))
    assert LINK not in html and "/results/" not in html


@pytest.mark.ac("RND-4.1")
def test_results_page_lists_cases_and_current_build_results_newest_first(
    coord_client, review, tester, second_tester
):
    older = submit(tester, review.case, review.build, T1, "fail", "Synthetic older")
    newer = submit(second_tester, review.case, review.build, T2, "pass", "")
    response = coord_client.get(results_url(review.round.pk))
    assert response.status_code == 200
    assert reverse("rounds:results", args=[review.round.pk]) == results_url(
        review.round.pk
    )
    html = page(response)
    assert title_tag(html) == f"Results: {FSI}Synthetic review round{PDI}"
    assert f"<h1>Results: {span('Synthetic review round')}</h1>" in html
    assert html.index("</h1>") < html.index("<p>State: Open</p>")
    first = section(html, "Synthetic case A", "<h2>")
    assert (
        "<h3>Linked acceptance criteria</h3>\n<ul>"
        f"<li>{span('Synthetic criterion one')}</li>"
        f"<li>{span('Synthetic criterion two')}</li></ul>"
    ) in first
    assert f"<h3>Current build</h3>\n<p>{span('Synthetic 1.0')}</p>" in first
    lines = [
        result_lines(second_tester.username, "Pass", "", T2),
        result_lines(tester.username, "Fail", "Synthetic older", T1),
    ]
    assert "<h3>Results for this build</h3>" in first
    assert first.index(lines[0]) < first.index(lines[1])
    assert EMPTY not in first and "Earlier builds" not in first
    second = section(html, "Synthetic case B")
    assert f"<li>{span('Synthetic criterion one')}</li></ul>" in second
    assert "Synthetic criterion two" not in second and EMPTY in second
    assert html.index("Synthetic case A") < html.index("Synthetic case B")
    back = f'<p><a href="{detail(review.round.pk)}">Back to round</a></p>'
    assert back in html
    assert {older.pk, newer.pk} == set(Result.objects.values_list("pk", flat=True))


@pytest.mark.ac("RND-4.1")
def test_equal_submission_times_show_the_later_created_result_first(
    coord_client, review, tester, second_tester
):
    submit(tester, review.case, review.build, T1, observation="Synthetic first")
    submit(second_tester, review.case, review.build, T1, observation="Synthetic next")
    html = page(coord_client.get(results_url(review.round.pk)))
    assert html.index("Synthetic next") < html.index("Synthetic first")


@pytest.mark.ac("RND-4.1")
def test_a_closed_rounds_results_stay_listed(coord_client, review, tester):
    submit(tester, review.case, review.build, T1, "fail", "Synthetic kept")
    open_html = page(coord_client.get(results_url(review.round.pk)))
    review.close()
    response = coord_client.get(results_url(review.round.pk))
    assert response.status_code == 200
    closed_html = page(response)
    assert "<p>State: Closed</p>" in closed_html
    lines = result_lines(tester.username, "Fail", "Synthetic kept", T1)
    assert lines in open_html and lines in closed_html
    assert closed_html.replace("State: Closed", "State: Open") == open_html


@pytest.mark.ac("RND-4.1")
def test_submission_time_stays_utc_under_a_local_timezone(coord_client, review, tester):
    submit(tester, review.case, review.build, T1)
    with timezone.override("Asia/Singapore"):
        html = page(coord_client.get(results_url(review.round.pk)))
    assert "Submitted at: 2026-10-29 01:02:03 UTC" in html
    assert "09:02:03" not in html


# RND-4.2


@pytest.mark.ac("RND-4.2")
def test_a_round_without_results_shows_the_empty_message_for_every_case(
    coord_client, review
):
    html = page(coord_client.get(results_url(review.round.pk)))
    assert html.count(EMPTY) == 2 and "Earlier builds" not in html
    assert "Tester:" not in html


@pytest.mark.ac("RND-4.2", "RND-4.3")
def test_earlier_build_results_do_not_count_for_the_current_build(
    coord_client, review, tester
):
    submit(tester, review.case, review.build, T1, "fail", "Synthetic earlier")
    review.retest("Synthetic 2.0", review.case)
    html = page(coord_client.get(results_url(review.round.pk)))
    first = section(html, "Synthetic case A", "<h2>")
    assert f"<h3>Current build</h3>\n<p>{span('Synthetic 2.0')}</p>" in first
    current = first[: first.index("<h3>Earlier builds</h3>")]
    assert f"<h3>Results for this build</h3>\n<p>{EMPTY}</p>" in current
    assert "Synthetic earlier" not in current
    earlier = first[first.index("<h3>Earlier builds</h3>") :]
    expected = result_lines(
        tester.username, "Fail", "Synthetic earlier", T1, "Synthetic 1.0"
    )
    assert expected in earlier


@pytest.mark.ac("RND-4.2")
def test_an_empty_observation_shows_no_observation(coord_client, review, tester):
    submit(tester, review.case, review.build, T1, "pass", "")
    html = page(coord_client.get(results_url(review.round.pk)))
    assert "<p>Observation: No observation.</p>" in html


@pytest.mark.ac("RND-4.2")
@pytest.mark.parametrize("earlier", ["none", "draft"])
def test_a_retested_case_without_earlier_submissions_has_no_earlier_builds(
    coord_client, review, tester, earlier
):
    if earlier == "draft":
        Result.objects.create(
            tester=tester,
            case=review.case,
            build=review.build,
            outcome="pass",
            observation="Synthetic earlier draft",
        )
    review.retest("Synthetic 2.0", review.case)
    review.retest("Synthetic 3.0", review.case, review.other_case)
    html = page(coord_client.get(results_url(review.round.pk)))
    for title in ("Synthetic case A", "Synthetic case B"):
        part = section(html, title, "<h2>" if title.endswith("A") else None)
        assert f"<h3>Results for this build</h3>\n<p>{EMPTY}</p>" in part
    assert "Earlier builds" not in html and "Synthetic earlier draft" not in html


# RND-4.3


@pytest.mark.ac("RND-4.3")
def test_retests_move_selected_results_to_earlier_builds_unchanged(
    coord_client, review, tester, second_tester
):
    on_first = submit(tester, review.case, review.build, T1, "fail", "Synthetic 1")
    untouched = submit(
        tester, review.other_case, review.build, T1, "pass", "Synthetic other"
    )
    second_build = review.retest("Synthetic 2.0", review.case)
    on_second = submit(
        second_tester, review.case, second_build, T2, "pass", "Synthetic 2"
    )
    review.retest("Synthetic 3.0", review.case)
    rows = list(Result.objects.order_by("pk").values())
    html = page(coord_client.get(results_url(review.round.pk)))
    first = section(html, "Synthetic case A", "<h2>")
    current = first[: first.index("<h3>Earlier builds</h3>")]
    earlier = first[first.index("<h3>Earlier builds</h3>") :]
    assert f"<p>{span('Synthetic 3.0')}</p>" in current and EMPTY in current
    newest = result_lines(
        second_tester.username, "Pass", "Synthetic 2", T2, "Synthetic 2.0"
    )
    oldest = result_lines(tester.username, "Fail", "Synthetic 1", T1, "Synthetic 1.0")
    assert earlier.index(newest) < earlier.index(oldest)
    other = section(html, "Synthetic case B")
    assert result_lines(tester.username, "Pass", "Synthetic other", T1) in other
    assert "Earlier builds" not in other
    assert list(Result.objects.order_by("pk").values()) == rows
    assert {on_first.pk, untouched.pk, on_second.pk} == {r["id"] for r in rows}


@pytest.mark.ac("RND-4.3")
def test_a_result_for_the_new_build_shows_under_it(coord_client, review, tester):
    submit(tester, review.case, review.build, T1, observation="Synthetic old")
    new_build = review.retest("Synthetic 2.0", review.case)
    submit(tester, review.case, new_build, T2, observation="Synthetic new")
    first = section(
        page(coord_client.get(results_url(review.round.pk))), "Synthetic case A", "<h2>"
    )
    current = first[: first.index("<h3>Earlier builds</h3>")]
    assert "Synthetic new" in current and "Synthetic old" not in current


# RND-4.4


@pytest.mark.ac("RND-4.4")
def test_drafts_and_rows_outside_the_rounds_covering_builds_never_appear(
    coord_client, review, tester, make_round, other_workspace
):
    Result.objects.create(
        tester=tester,
        case=review.case,
        build=review.build,
        outcome="pass",
        observation="Synthetic draft",
    )
    other = Review(make_round, "Synthetic other round")
    foreign = Review(lambda title: make_round(title, owner=other_workspace))
    # The link tables do not tie a covered case or a linked criterion to the
    # case's round, so these rows can exist only if stored outside the services.
    Build.objects.filter(pk=other.build.pk).update(label="Synthetic forged build")
    BuildCase.objects.create(build=other.build, case=review.case)
    alien = Criterion.objects.create(round=foreign.round, text="Synthetic alien")
    CaseCriterion.objects.create(case=review.case, criterion=alien)
    submit(tester, review.case, other.build, T1, observation="Synthetic other build")
    uncovered = review.retest("Synthetic 2.0", review.other_case)
    submit(tester, review.case, uncovered, T1, observation="Synthetic uncovered")
    outsider = User.objects.create_user(
        "tester-rnd10002", PASSWORD, workspace=other_workspace, role="tester"
    )
    submit(outsider, review.case, review.build, T1, observation="Synthetic outsider")
    submit(tester, other.case, other.build, T1, observation="Synthetic sibling")
    submit(tester, foreign.case, foreign.build, T1, observation="Synthetic foreign")
    second = User.objects.create_user(
        "tester3-rnd10001", PASSWORD, workspace=tester.workspace, role="tester"
    )
    shown = submit(second, review.case, review.build, T2, observation="Synthetic shown")
    response = coord_client.get(
        results_url(review.round.pk),
        {"tester": tester.pk, "result": shown.pk + 1, "build": other.build.pk},
    )
    html = page(response)
    assert "Synthetic shown" in html and second.username in html
    # The valid result lists under the case's own current build, which is
    # this round's build, so a foreign covering build changes nothing.
    first = section(html, "Synthetic case A", "<h2>")
    assert f"<h3>Current build</h3>\n<p>{span('Synthetic 1.0')}</p>" in first
    assert "Synthetic shown" in first and "Earlier builds" not in first
    for hidden in (
        "Synthetic forged build",
        "Synthetic alien",
        "Synthetic draft",
        "Synthetic other build",
        "Synthetic uncovered",
        "Synthetic outsider",
        "Synthetic sibling",
        "Synthetic foreign",
        "Synthetic other round",
        outsider.username,
    ):
        assert hidden not in html, hidden
    assert html.count("Tester:") == 1


@pytest.mark.ac("RND-4.4")
def test_the_page_offers_no_controls_and_changes_nothing(coord_client, review, tester):
    submit(tester, review.case, review.build, T1, observation="Synthetic read")
    before = snapshot()
    response = coord_client.get(results_url(review.round.pk))
    assert response.status_code == 200
    html = page(response)
    for control in ("<form", "<button", "<input", "<textarea", "<select"):
        assert control not in html, control
    assert "Record result" not in html and "/result/" not in html
    assert snapshot() == before


@pytest.mark.ac("RND-4.4")
def test_committed_changes_show_on_the_next_request(coord_client, review, tester):
    url = results_url(review.round.pk)
    assert "Synthetic later" not in page(coord_client.get(url))
    submit(tester, review.case, review.build, T1, observation="Synthetic later")
    assert "Synthetic later" in page(coord_client.get(url))
    review.retest("Synthetic 2.0", review.case)
    assert "<h3>Earlier builds</h3>" in page(coord_client.get(url))


@pytest.mark.ac("RND-4.4")
def test_query_count_does_not_grow_with_cases_or_results(
    coord_client, review, tester, second_tester
):
    url = results_url(review.round.pk)

    def queries():
        with CaptureQueriesContext(connection) as captured:
            assert coord_client.get(url).status_code == 200
        return len(captured)

    small = queries()
    for n in range(3):
        case = review.add_case(f"Synthetic extra {n}", review.first_criterion)
        BuildCase.objects.create(build=review.build, case=case)
        submit(tester, case, review.build, T1)
        submit(second_tester, case, review.build, T2)
    review.retest("Synthetic 2.0", review.case)
    assert queries() == small


# RND-4.5


@pytest.mark.ac("RND-4.5")
def test_user_text_is_escaped_and_each_line_isolated(
    coord_client, make_round, workspace
):
    text = MARKUP + "\u202e\nSynthetic line\u200b"
    review = Review(make_round, text)
    for record, field in (
        (review.case, "title"),
        (review.first_criterion, "text"),
        (review.second_criterion, "text"),
        (review.build, "label"),
    ):
        setattr(record, field, text)
        record.save(update_fields=[field])
    author = User.objects.create_user(
        text, PASSWORD, workspace=workspace, role="tester"
    )
    submit(author, review.case, review.build, T1, "fail", text)
    # Case A moves to a plain build, so its result shows "Build: <text>".
    review.retest("Synthetic plain build", review.case)
    response = coord_client.get(results_url(review.round.pk))
    html = page(response)
    lines = (
        f'<span dir="auto">{escape(MARKUP)}\u202e</span><br>'
        '<span dir="auto">Synthetic line\u200b</span>'
    )
    # Heading; case A's title; criterion one under case A and under case B;
    # criterion two; case B's current build; the earlier result's build,
    # username and observation.
    assert html.count(lines) == 9
    assert f"<h1>Results: {lines}</h1>" in html
    assert f"<p>Build: {lines}</p>" in html
    assert f"<p>Tester: {lines}</p>" in html
    assert f"<p>Observation: {lines}</p>" in html
    assert SCRIPT_TAG not in html and IMG_TAG not in html
    assert html.count("\u202e") == 9
    assert title_tag(html) == (
        f"Results: {FSI}{escape(MARKUP)} Synthetic line\u200b{PDI}"
    )
    assert "unicode-bidi" not in html


@pytest.mark.ac("RND-4.5")
def test_page_title_drops_direction_controls_even_after_a_stray_pop(
    coord_client, make_round
):
    review = Review(make_round, "Synthetic \u2069\u202eReversed\u2066x")
    title = title_tag(page(coord_client.get(results_url(review.round.pk))))
    assert title == f"Results: {FSI}Synthetic Reversedx{PDI}"
    assert title.count(FSI) == 1 and title.count(PDI) == 1


@pytest.mark.ac("RND-4.5")
@pytest.mark.parametrize("separator", ["\r\n", "\u2028", "\u2029", "\x85"])
def test_every_line_separator_splits_an_observation(
    coord_client, review, tester, separator
):
    submit(tester, review.case, review.build, T1, observation=f"One{separator}Two")
    html = page(coord_client.get(results_url(review.round.pk)))
    assert f"{span('One')}<br>{span('Two')}" in html
    assert separator not in html


# RND-4.6


@pytest.mark.ac("RND-4.6")
@pytest.mark.parametrize("signed", [True, False])
@pytest.mark.parametrize(
    "method", ["head", "post", "put", "patch", "delete", "options", "trace"]
)
def test_other_methods_get_405_uncached(coordinator, review, signed, method):
    client = signed_in(coordinator) if signed else Client()
    before = snapshot()
    response = getattr(client, method)(results_url(review.round.pk))
    assert response.status_code == 405
    assert response["Allow"] == "GET"
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RND-4.6")
@pytest.mark.parametrize("origin", [None, "https://attacker.example"])
def test_csrf_refusal_comes_before_405(coordinator, review, origin):
    client = signed_in(coordinator, enforce_csrf_checks=True)
    data = {"csrfmiddlewaretoken": csrf_token(client)} if origin else {}
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    response = client.post(results_url(review.round.pk), data, **extra)
    assert response.status_code == 403 and DENIED in page(response)


@pytest.mark.ac("RND-4.6")
def test_signed_out_and_tester_are_refused_before_any_lookup(
    review, tester, coordinator
):
    with mock.patch.object(
        round_views, "workspace_records", side_effect=AssertionError("lookup")
    ):
        for round_id in (review.round.pk, 2_000_000_001):
            response = Client().get(results_url(round_id))
            assert (response.status_code, response["Location"]) == (302, "/sign-in/")
            no_store(response)
        first = signed_in(tester).get(results_url(review.round.pk))
        second = signed_in(tester).get(results_url(2_000_000_001))
    assert first.status_code == second.status_code == 403
    assert first.content == second.content and DENIED in page(first)
    assert review.round.title not in page(first)


@pytest.mark.ac("RND-4.6")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_other_workspace_round_gets_the_same_404_in_every_state(
    coord_client, review, other_workspace, tester, state
):
    submit(tester, review.case, review.build, T1, observation="Synthetic private")
    Round.objects.filter(pk=review.round.pk).update(
        state=state, workspace=other_workspace
    )
    response = coord_client.get(results_url(review.round.pk))
    missing = coord_client.get(results_url(2_000_000_001))
    assert response.status_code == 404 and response.content == missing.content
    html = page(response)
    assert NOT_FOUND in html
    for secret in ("Synthetic review round", "Synthetic private", "Synthetic case"):
        assert secret not in html


@pytest.mark.ac("RND-4.6")
def test_a_draft_round_gets_409_uncached(coord_client, make_round):
    draft = make_round("Synthetic draft round")
    before = snapshot()
    response = coord_client.get(results_url(draft.pk))
    assert response.status_code == 409
    html = page(response)
    assert f"<h1>{CONFLICT.format('Draft')}</h1>" in html
    assert "Synthetic draft round" not in html
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RND-4.6")
def test_successful_page_is_never_cached(coord_client, review):
    no_store(coord_client.get(results_url(review.round.pk)))


@pytest.mark.ac("RND-4.6")
@pytest.mark.parametrize(
    "failure",
    ["lazy-user", "lookup", "cases", "criteria", "builds", "results", "render"],
)
def test_storage_failures_give_the_uncached_503_without_results(
    coordinator, review, tester, failure, caplog
):
    submit(tester, review.case, review.build, T1, observation="Synthetic secret")
    path = results_url(review.round.pk)
    match = resolve(path)
    request = RequestFactory().get(path)
    request.user = coordinator
    error = OperationalError("synthetic storage failure")
    models = {"cases": Case, "criteria": Criterion, "builds": Build, "results": Result}
    before = snapshot()
    if failure == "lazy-user":

        def fail_user():
            raise error

        request.user = SimpleLazyObject(fail_user)
        response = match.func(request, **match.kwargs)
    elif failure == "lookup":
        with mock.patch.object(round_views, "workspace_records", side_effect=error):
            response = match.func(request, **match.kwargs)
    elif failure == "render":
        real = round_views.render

        def fail_render(request, template, *args, **kwargs):
            if template == "rounds/results.html":
                raise error
            return real(request, template, *args, **kwargs)

        with mock.patch.object(round_views, "render", fail_render):
            response = match.func(request, **match.kwargs)
    else:
        real_fetch = QuerySet._fetch_all

        def fail_fetch(query):
            if query.model is models[failure]:
                raise error
            return real_fetch(query)

        with mock.patch.object(QuerySet, "_fetch_all", fail_fetch):
            response = match.func(request, **match.kwargs)
    assert response.status_code == 503
    html = page(response)
    assert UNAVAILABLE in html
    for partial in ("Synthetic secret", "Synthetic case", "Synthetic review round"):
        assert partial not in html
    assert "Synthetic secret" not in caplog.text
    assert "A round request failed in storage." in caplog.text
    no_store(response)
    assert snapshot() == before
