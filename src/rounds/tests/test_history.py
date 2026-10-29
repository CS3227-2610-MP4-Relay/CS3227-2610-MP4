"""RES-3 private read-only history and its authorization boundaries."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import OperationalError, transaction
from django.db.models.query import QuerySet
from django.test import RequestFactory
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.html import escape

from accounts.models import User
from rounds import services
from rounds import tester as tester_views
from rounds.models import BuildCase, Case, Criterion, Result, Round

from .conftest import (
    DENIED,
    IMG_TAG,
    MARKUP,
    NOT_FOUND,
    SCRIPT_TAG,
    UNAVAILABLE,
    csrf_token,
    open_with_case,
    page,
    signed_in,
)
from .test_result_services import snapshot
from .test_results import no_store

pytestmark = pytest.mark.django_db


@pytest.fixture
def target(make_round):
    """One published round with original coverage and linked criterion."""
    round_ = open_with_case(make_round)
    case = round_.cases.get()
    criterion = Criterion.objects.create(round=round_, text="Synthetic linked")
    case.criteria.add(criterion)
    return round_, case, round_.builds.get()


def url(round_):
    """Name the intended history path before its route exists."""
    return f"/tester/rounds/{round_.pk}/results/"


def save_row(tester, target, **fields):
    """Persist synthetic records, including defensive malformed-data cases."""
    _, case, build = target
    return Result.objects.create(
        tester=tester, case=case, build=build, outcome="pass", **fields
    )


@pytest.mark.ac("RES-3.1", "RES-3.2", "RES-3.5", "RES-3.6")
@pytest.mark.parametrize("closed", [False, True])
def test_navigation_and_empty_read_only_page(tester, target, closed):
    round_, _, _ = target
    if closed:
        Round.objects.filter(pk=round_.pk).update(state="closed")
    client = signed_in(tester)
    before = snapshot()
    detail = f"/tester/rounds/{round_.pk}/"
    body = page(client.get(detail))
    assert body.count(f'href="{url(round_)}">My results</a>') == 1
    response = client.get(url(round_))
    assert response.status_code == 200
    assert reverse("accounts:tester-results", args=[round_.pk]) == url(round_)
    body = page(response)
    for text in (
        "<title>My results</title>",
        "<h1>My results</h1>",
        "Round",
        round_.title,
        f"State: {'Closed' if closed else 'Open'}",
        "No results yet.",
    ):
        assert text in body
    assert f'href="{detail}">Back to round</a>' in body
    assert "<form" not in body and "<button" not in body and "Record result" not in body
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-3.2", "RES-3.3")
def test_order_original_context_and_refresh_after_save_retest_close(tester, target):
    round_, case, original = target
    first = save_row(tester, target, observation="Synthetic earlier draft")
    extra = Criterion.objects.create(round=round_, text="Synthetic second criterion")
    case.criteria.add(extra)
    second_case = Case.objects.create(
        round=round_,
        title="Synthetic second case",
        steps="Steps",
        expected_result="Expected",
    )
    BuildCase.objects.create(build=original, case=second_case)
    submitted = save_row(
        tester,
        (round_, second_case, original),
        submitted_at=datetime(2026, 10, 29, 1, 2, 3, tzinfo=UTC),
    )
    client = signed_in(tester)
    assert "Synthetic earlier draft" in page(client.get(url(round_)))
    Result.objects.filter(pk=first.pk).update(observation="Synthetic replacement")
    with transaction.atomic():
        next_build = services.request_retest(round_, "Synthetic next", [case.pk])
    response = client.get(url(round_))
    assert list(response.context["results"]) == [first, submitted]
    assert next_build.label not in page(response)
    newest = save_row(
        tester, (round_, case, next_build), observation="Synthetic newest"
    )
    for closed in (False, True):
        if closed:
            with transaction.atomic():
                services.close(round_)
        before = snapshot()
        response = client.get(url(round_))
        rows = list(response.context["results"])
        assert rows == [newest, first, submitted]
        assert list(rows[1].case.criteria.all()) == list(case.criteria.order_by("id"))
        body = page(response)
        for text in (
            "Test case",
            "Linked acceptance criteria",
            "Build",
            original.label,
            next_build.label,
            "Synthetic linked",
            extra.text,
            "Synthetic replacement",
            "Outcome",
            "Pass",
            "Observation",
            "No observation.",
            "Status: Draft",
            "Status: Submitted",
            "2026-10-29 01:02:03 UTC",
        ):
            assert text in body
        assert "Synthetic earlier draft" not in body
        assert body.count("Submitted at") == 1
        assert "Current build" not in body and "No results yet." not in body
        assert snapshot() == before


@pytest.mark.ac("RES-3.4")
def test_owner_round_and_coverage_scope_ignores_forged_selectors(
    tester, target, make_round, other_workspace
):
    round_, case, build = target
    own = save_row(tester, target, observation="Synthetic own")
    other = User.objects.create_user(
        "synthetic-history-other",
        "SyntheticHistory16",
        workspace=tester.workspace,
        role="tester",
    )
    private = save_row(other, target, observation="Synthetic private")
    another = open_with_case(make_round)
    foreign = open_with_case(lambda: make_round(owner=other_workspace))
    for other_round in (another, foreign):
        other_case, other_build = other_round.cases.get(), other_round.builds.get()
        save_row(
            tester,
            (other_round, other_case, other_build),
            observation="Synthetic other round",
        )
        save_row(
            tester, (round_, case, other_build), observation="Synthetic wrong build"
        )
        save_row(
            tester, (round_, other_case, build), observation="Synthetic wrong case"
        )
    uncovered = Case.objects.create(
        round=round_,
        title="Synthetic uncovered",
        steps="Steps",
        expected_result="Expected",
    )
    save_row(tester, (round_, uncovered, build), observation="Synthetic uncovered row")
    alien = Criterion.objects.create(round=foreign, text="Synthetic alien criterion")
    case.criteria.add(alien)
    before = snapshot()
    response = signed_in(tester).get(
        url(round_),
        {
            "tester": other.pk,
            "result": private.pk,
            "case": uncovered.pk,
            "build": build.pk,
        },
    )
    assert response.status_code == 200
    assert list(response.context["results"]) == [own]
    body = page(response)
    assert "Synthetic own" in body
    for secret in (
        "Synthetic private",
        "Synthetic other round",
        "Synthetic wrong",
        "Synthetic uncovered",
        alien.text,
    ):
        assert secret not in body
    assert snapshot() == before
    other_response = signed_in(other).get(url(round_))
    assert list(other_response.context["results"]) == [private]
    assert "Synthetic own" not in page(other_response)


@pytest.mark.ac("RES-3.4")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_unavailable_rounds_share_fixed_404(tester, target, other_workspace, state):
    round_, _, _ = target
    Round.objects.filter(pk=round_.pk).update(state=state, workspace=other_workspace)
    client = signed_in(tester)
    response = client.get(url(round_))
    missing = client.get("/tester/rounds/2147483647/results/")
    assert response.status_code == 404 and response.content == missing.content
    assert NOT_FOUND in page(response) and round_.title not in page(response)
    if state == "draft":
        Round.objects.filter(pk=round_.pk).update(workspace=tester.workspace)
        assert client.get(url(round_)).content == missing.content


@pytest.mark.ac("RES-3.4", "RES-3.6")
def test_authentication_and_role_precede_lookup(tester, coordinator, target):
    location = url(target[0])
    with patch.object(
        tester_views, "available_rounds", side_effect=AssertionError("lookup")
    ):
        request = RequestFactory().get(location)
        request.user = AnonymousUser()
        response = resolve(location).func(request, **resolve(location).kwargs)
        assert response.status_code == 302 and response.url == "/sign-in/"
        no_store(response)
        response = signed_in(coordinator).get(location)
        assert response.status_code == 403 and DENIED in page(response)


@pytest.mark.ac("RES-3.5", "RES-3.6")
@pytest.mark.parametrize(
    "method", ["post", "head", "put", "patch", "delete", "options", "trace"]
)
def test_other_methods_are_read_only_405(tester, target, method):
    before = snapshot()
    response = getattr(signed_in(tester), method)(url(target[0]))
    assert response.status_code == 405
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-3.5")
@pytest.mark.parametrize("origin", [None, "https://attacker.example"])
def test_csrf_precedes_method_refusal(tester, target, origin):
    client = signed_in(tester, enforce_csrf_checks=True)
    data = {"csrfmiddlewaretoken": csrf_token(client)} if origin else {}
    before = snapshot()
    response = client.post(
        url(target[0]), data, **({"HTTP_ORIGIN": origin} if origin else {})
    )
    assert response.status_code == 403 and DENIED in page(response)
    assert snapshot() == before


@pytest.mark.ac("RES-3.6")
@pytest.mark.parametrize(
    "failure", ["lookup", "lazy-user", "rows", "criteria", "render"]
)
def test_storage_errors_return_fixed_uncached_503(tester, target, failure, caplog):
    request = RequestFactory().get(url(target[0]))
    request.user = tester
    save_row(tester, target)
    match = resolve(request.path)
    error = OperationalError("Synthetic sensitive observation")
    before = snapshot()
    if failure == "lazy-user":

        def fail_user():
            raise error

        request.user = SimpleLazyObject(fail_user)
        response = match.func(request, **match.kwargs)
    else:
        original = tester_views.render

        def fail_render(request, template, *args, **kwargs):
            if template == "rounds/tester_history.html":
                raise error
            return original(request, template, *args, **kwargs)

        original_fetch = QuerySet._fetch_all

        def fail_fetch(query):
            if query.model is (Result if failure == "rows" else Criterion):
                raise error
            return original_fetch(query)

        path = {
            "lookup": "rounds.tester.workspace_records",
            "rows": "django.db.models.query.QuerySet._fetch_all",
            "criteria": "django.db.models.query.QuerySet._fetch_all",
            "render": "rounds.tester.render",
        }[failure]
        with patch(
            path,
            **(
                {"new": fail_render}
                if failure == "render"
                else {"new": fail_fetch}
                if failure in ("rows", "criteria")
                else {"side_effect": error}
            ),
        ):
            response = match.func(request, **match.kwargs)
    assert response.status_code == 503 and UNAVAILABLE in page(response)
    assert "Synthetic sensitive" not in page(response) + caplog.text
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-3.2")
def test_submission_time_remains_utc_with_an_active_local_timezone(tester, target):
    save_row(tester, target, submitted_at=datetime(2026, 10, 29, 1, 2, 3, tzinfo=UTC))
    with timezone.override("Asia/Singapore"):
        body = page(signed_in(tester).get(url(target[0])))
    assert "2026-10-29 01:02:03 UTC" in body
    assert "09:02:03" not in body


@pytest.mark.ac("RES-3.7")
def test_all_stored_text_is_escaped_and_line_isolated(tester, target):
    round_, case, build = target
    fields = [
        (round_, "title"),
        (case, "title"),
        (build, "label"),
        (case.criteria.get(), "text"),
    ]
    for record, field in fields:
        setattr(record, field, MARKUP + "\u202e\nSynthetic line\u200b")
        record.save(update_fields=[field])
    row = save_row(tester, target, observation=MARKUP + "\u2069\nSynthetic observation")
    Result.objects.filter(pk=row.pk).update(outcome="fail")
    body = page(signed_in(tester).get(url(round_)))
    assert (
        body.count(
            f'<span dir="auto">{escape(MARKUP)}\u202e</span><br>'
            '<span dir="auto">Synthetic line\u200b</span>'
        )
        == 4
    )
    assert (
        f'<span dir="auto">{escape(MARKUP)}\u2069</span><br>'
        '<span dir="auto">Synthetic observation</span>' in body
    )
    assert "Fail" in body and SCRIPT_TAG not in body and IMG_TAG not in body
