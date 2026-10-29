"""RES-1: read-only availability across tester and workspace boundaries."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, connection, transaction
from django.test import Client, RequestFactory
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.html import escape

from accounts.models import User
from rounds import services
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import (
    DENIED,
    IMG_TAG,
    MARKUP,
    NOT_FOUND,
    PASSWORD,
    SCRIPT_TAG,
    UNAVAILABLE,
    csrf_token,
    page,
    signed_in,
)

pytestmark = pytest.mark.django_db
HOME = "/tester/"


def detail(round_):
    """The tester detail URL, intentionally usable before its route exists."""
    return f"/tester/rounds/{round_.pk}/"


def snapshot():
    """Capture all domain data, excluding authentication/session bookkeeping."""
    return {
        model: list(model.objects.order_by("pk").values())
        for model in (Round, Case, Criterion, CaseCriterion, Build, BuildCase)
    }


@pytest.fixture
def published(make_round):
    """Publish three linked cases so partial and overlapping retests differ."""
    round_ = make_round("Synthetic available round")
    criteria = [
        Criterion.objects.create(round=round_, text=f"Synthetic criterion {index}")
        for index in range(3)
    ]
    cases = [
        Case.objects.create(
            round=round_,
            title=f"Synthetic case {index}",
            steps=f"Synthetic steps {index}",
            expected_result=f"Synthetic expected {index}",
        )
        for index in range(3)
    ]
    for case, criterion in zip(cases, criteria, strict=True):
        CaseCriterion.objects.create(case=case, criterion=criterion)
    with transaction.atomic():
        services.publish(round_, "Synthetic original")
    return round_, cases, criteria


@pytest.mark.ac("RES-1.1", "RES-1.4")
def test_home_orders_only_own_open_rounds_for_both_testers(
    tester, make_round, other_workspace
):
    older = make_round("Synthetic older", Round.State.OPEN)
    tied = make_round("Synthetic first tie", Round.State.OPEN)
    latest = make_round("Synthetic second tie", Round.State.OPEN)
    now = timezone.now()
    Round.objects.filter(pk=older.pk).update(created_at=now - timedelta(days=1))
    Round.objects.filter(pk__in=[tied.pk, latest.pk]).update(created_at=now)
    unavailable = [
        make_round("Synthetic draft"),
        make_round("Synthetic closed", Round.State.CLOSED),
        make_round("Synthetic foreign", Round.State.OPEN, other_workspace),
    ]
    second = User.objects.create_user(
        "tester2-res1", PASSWORD, workspace=tester.workspace, role="tester"
    )
    for user in (tester, second):
        response = signed_in(user).get(HOME)
        assert response.status_code == 200
        body = page(response)
        assert "Available tests" in body
        assert user.username in body and user.workspace.name in body
        assert 'action="/sign-out/"' in body
        assert list(response.context["rounds"]) == [latest, tied, older]
        for round_ in (latest, tied, older):
            assert body.count(f'href="{detail(round_)}"') == 1
        for round_ in unavailable:
            assert round_.title not in body
            assert f'href="{detail(round_)}"' not in body
    assert reverse("accounts:tester-round", args=[latest.pk]) == detail(latest)


@pytest.mark.ac("RES-1.2")
@pytest.mark.parametrize("has_unavailable", [False, True])
def test_empty_home(tester, make_round, has_unavailable):
    if has_unavailable:
        make_round("Synthetic hidden draft")
        make_round("Synthetic hidden closed", Round.State.CLOSED)
    body = page(signed_in(tester).get(HOME))
    assert "No tests available." in body
    assert 'href="/tester/rounds/' not in body


@pytest.mark.ac("RES-1.3", "RES-1.5")
def test_detail_shows_ordered_cases_links_and_latest_covering_build(tester, published):
    round_, cases, criteria = published
    client = signed_in(tester)
    initial = client.get(detail(round_))
    assert initial.status_code == 200
    assert [case.current_build.label for case in initial.context["cases"]] == [
        "Synthetic original"
    ] * 3
    # A second link is inserted in reverse order to exercise criterion ordering.
    cases[0].criteria.add(criteria[2])
    with transaction.atomic():
        services.request_retest(round_, "Synthetic partial", [cases[0].pk])
        services.request_retest(round_, "Synthetic overlap", [cases[0].pk, cases[1].pk])
        services.request_retest(round_, "Synthetic repeated", [cases[0].pk])
    before = snapshot()
    response = client.get(detail(round_))
    assert response.status_code == 200
    body = page(response)
    assert f'<h1><span dir="auto">{round_.title}</span></h1>' in body
    assert "State: Open" in body and "Test cases" in body
    assert 'href="/tester/"' in body
    shown = list(response.context["cases"])
    assert [case.pk for case in shown] == [case.pk for case in cases]
    assert [case.current_build.label for case in shown] == [
        "Synthetic repeated",
        "Synthetic overlap",
        "Synthetic original",
    ]
    assert list(shown[0].criteria.all()) == [criteria[0], criteria[2]]
    assert list(shown[1].criteria.all()) == [criteria[1]]
    for case in cases:
        assert (
            case.title in body and case.steps in body and case.expected_result in body
        )
    for heading in (
        "Steps",
        "Expected result",
        "Linked acceptance criteria",
        "Current build",
    ):
        assert body.count(f"<h4>{heading}</h4>") == 3
    for absent in (
        "Synthetic partial",
        "Builds",
        "Edit round",
        "Publish round",
        "Close round",
        "Request a retest",
    ):
        assert absent not in body
    assert "<form" not in body and "/coordinator/" not in body
    assert snapshot() == before


@pytest.mark.ac("RES-1.4")
@pytest.mark.parametrize(
    ("foreign", "state"),
    [(False, Round.State.DRAFT), (False, Round.State.CLOSED)]
    + [(True, state) for state in Round.State],
)
def test_unavailable_detail_is_indistinguishable(
    tester, make_round, other_workspace, foreign, state
):
    round_ = make_round(
        "Synthetic forbidden", state, other_workspace if foreign else None
    )
    case = Case.objects.create(
        round=round_,
        title="Synthetic hidden case",
        steps="Hidden",
        expected_result="Hidden",
    )
    criterion = Criterion.objects.create(
        round=round_, text="Synthetic hidden criterion"
    )
    case.criteria.add(criterion)
    build = Build.objects.create(
        round=round_, label="Synthetic hidden build", key="hidden"
    )
    build.cases.add(case)
    client = signed_in(tester)
    response = client.get(detail(round_))
    missing = client.get("/tester/rounds/2147483647/")
    assert response.status_code == missing.status_code == 404
    assert response.content == missing.content
    assert NOT_FOUND in page(response)
    for hidden in (round_.title, case.title, criterion.text, build.label, "State:"):
        assert hidden not in page(response)


@pytest.mark.ac("RES-1.4")
@pytest.mark.parametrize("url", [HOME, "/tester/rounds/2147483647/"])
def test_authentication_and_role_precede_round_lookup(coordinator, url):
    client = signed_in(coordinator)
    match = resolve(url)

    def refuse_read(execute, sql, params, many, context):
        raise AssertionError("Authorization must precede domain reads")

    for user in (coordinator, AnonymousUser()):
        request = RequestFactory().get(url)
        request.user = user
        with connection.execute_wrapper(refuse_read):
            if user.is_authenticated:
                with pytest.raises(PermissionDenied):
                    match.func(request, **match.kwargs)
            else:
                assert match.func(request, **match.kwargs).status_code == 302
    response = client.get(url)
    assert response.status_code == 403
    assert DENIED in page(response)
    response = Client().get(url)
    assert response.status_code == 302 and response.url == "/sign-in/"
    assert "no-store" in response["Cache-Control"]


@pytest.mark.ac("RES-1.4")
@pytest.mark.parametrize("foreign", [False, True])
def test_malformed_related_links_do_not_disclose_other_rounds(
    tester, published, make_round, other_workspace, foreign
):
    round_, cases, _ = published
    other = make_round(
        "Synthetic other", Round.State.OPEN, other_workspace if foreign else None
    )
    criterion = Criterion.objects.create(round=other, text="Synthetic unlinked secret")
    cases[0].criteria.add(criterion)
    build = Build.objects.create(
        round=other, label="Synthetic foreign label", key="foreign"
    )
    build.cases.add(cases[0])
    response = signed_in(tester).get(detail(round_))
    assert response.status_code == 200
    assert criterion.text not in page(response) and build.label not in page(response)
    assert response.context["cases"][0].current_build.label == "Synthetic original"


@pytest.mark.ac("RES-1.5", "RES-1.6")
@pytest.mark.parametrize(
    "method", ["HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]
)
@pytest.mark.parametrize("detail_page", [False, True])
def test_methods_are_read_only_and_uncached(tester, published, method, detail_page):
    round_, _, _ = published
    client = signed_in(tester, enforce_csrf_checks=True)
    token = csrf_token(client)
    before = snapshot()
    response = client.generic(
        method, detail(round_) if detail_page else HOME, HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 405
    assert response["Allow"] == "GET"
    assert (
        "private" in response["Cache-Control"]
        and "no-store" in response["Cache-Control"]
    )
    assert snapshot() == before


@pytest.mark.ac("RES-1.5")
@pytest.mark.parametrize("foreign_origin", [False, True])
@pytest.mark.parametrize("url", [HOME, "/tester/rounds/2147483647/"])
def test_csrf_precedes_method_and_lookup(tester, url, foreign_origin):
    client = signed_in(tester, enforce_csrf_checks=True)
    token = csrf_token(client)
    headers = (
        {"HTTP_X_CSRFTOKEN": token, "HTTP_ORIGIN": "https://foreign.invalid"}
        if foreign_origin
        else {}
    )
    assert client.post(url, **headers).status_code == 403


@pytest.mark.ac("RES-1.6")
@pytest.mark.parametrize("detail_page", [False, True])
def test_success_and_storage_failures_are_uncached(tester, published, detail_page):
    round_, _, _ = published
    client = signed_in(tester)
    url = detail(round_) if detail_page else HOME
    before = snapshot()
    response = client.get(url)
    assert response.status_code == 200
    assert (
        "private" in response["Cache-Control"]
        and "no-store" in response["Cache-Control"]
    )
    for target in (
        ("rounds_round", "rounds_case", "rounds_criterion", "rounds_build")
        if detail_page
        else ("rounds_round",)
    ):

        def fail(execute, sql, params, many, context, table=target):
            if f'"{table}"' in sql:
                raise OperationalError("Synthetic unavailable storage")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(fail):
            response = client.get(url)
        assert response.status_code == 503, target
        assert UNAVAILABLE in page(response) and round_.title not in page(response)
        assert (
            "private" in response["Cache-Control"]
            and "no-store" in response["Cache-Control"]
        )
    assert snapshot() == before


@pytest.mark.ac("RES-1.6")
@pytest.mark.parametrize("target", ["session", "user"])
@pytest.mark.parametrize("url", [HOME, "/tester/rounds/2147483647/"])
def test_lazy_authentication_database_failure_returns_503(tester, url, target):
    client = signed_in(tester)
    patched = "django.contrib.auth.get_user" if target == "user" else None
    if patched:
        with patch(patched, side_effect=OperationalError("Synthetic auth failure")):
            response = client.get(url)
    else:
        with patch.object(
            SessionStore,
            "load",
            side_effect=OperationalError("Synthetic session failure"),
        ):
            response = client.get(url)
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    assert "no-store" in response["Cache-Control"]


@pytest.mark.ac("RES-1.7")
@pytest.mark.parametrize(
    "field", ["round", "case", "steps", "expected", "criterion", "build"]
)
def test_coordinator_text_is_escaped_and_isolated_for_tester(tester, published, field):
    round_, cases, criteria = published
    text = MARKUP + "\n\u05e9\u05dc\u05d5\u05dd\u2069 tail\u2029last"
    model, pk, name = {
        "round": (Round, round_.pk, "title"),
        "case": (Case, cases[0].pk, "title"),
        "steps": (Case, cases[0].pk, "steps"),
        "expected": (Case, cases[0].pk, "expected_result"),
        "criterion": (Criterion, criteria[0].pk, "text"),
        "build": (Build, round_.builds.first().pk, "label"),
    }[field]
    model.objects.filter(pk=pk).update(**{name: text})
    client = signed_in(tester)
    urls = [detail(round_), HOME] if field == "round" else [detail(round_)]
    isolated = "<br>".join(
        f'<span dir="auto">{escape(line)}</span>' for line in text.splitlines()
    )
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        body = page(response)
        assert isolated in body
        assert SCRIPT_TAG not in body and IMG_TAG not in body
    if field == "round":
        body = page(client.get(detail(round_)))
        title = " ".join(text.replace("\u2069", "").splitlines())
        assert f"<title>\u2068{escape(title)}\u2069</title>" in body


@pytest.mark.ac("RES-1.1", "RES-1.8")
def test_publish_and_close_change_next_request(tester, coordinator, make_round):
    round_ = make_round("Synthetic newly published")
    case = Case.objects.create(
        round=round_, title="Synthetic case", steps="Steps", expected_result="Result"
    )
    criterion = Criterion.objects.create(round=round_, text="Synthetic criterion")
    case.criteria.add(criterion)
    client = signed_in(tester)
    coord = signed_in(coordinator)
    assert round_.title not in page(client.get(HOME))
    assert (
        coord.post(
            f"/coordinator/rounds/{round_.pk}/publish/", {"label": "Synthetic released"}
        ).status_code
        == 302
    )
    assert round_.title in page(client.get(HOME))
    assert client.get(detail(round_)).status_code == 200
    assert coord.post(f"/coordinator/rounds/{round_.pk}/close/").status_code == 302
    assert round_.title not in page(client.get(HOME))
    assert client.get(detail(round_)).status_code == 404
