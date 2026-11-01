"""RES-2 tester result entry through real Django forms and requests."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, transaction
from django.test import RequestFactory
from django.urls import resolve, reverse
from django.utils.functional import SimpleLazyObject
from django.utils.html import escape

from accounts.models import User
from rounds import results, services
from rounds import tester as tester_views
from rounds.models import BuildCase, Result, Round

from .conftest import (
    DENIED,
    IMG_TAG,
    MARKUP,
    NOT_FOUND,
    SCRIPT_TAG,
    UNAVAILABLE,
    csrf_token,
    no_store,
    open_with_case,
    page,
    signed_in,
    snapshot,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def target(make_round):
    """A published case with an available current-build entry."""
    round_ = open_with_case(make_round)
    return round_, round_.cases.get(), round_.builds.get()


def url(target):
    """Spell the intended route before it exists for red tests."""
    round_, case, build = target
    return f"/tester/rounds/{round_.pk}/cases/{case.pk}/builds/{build.pk}/result/"


def payload(outcome="pass", observation="", action="save"):
    """One independently valid request unless a test overrides a field."""
    return {"outcome": outcome, "observation": observation, "action": action}


@pytest.mark.ac("RES-1.5", "RES-2.1", "RES-2.4")
def test_links_follow_each_current_build_and_disappear_on_close(tester, target):
    round_, case, _original = target
    client = signed_in(tester)
    detail = f"/tester/rounds/{round_.pk}/"
    body = page(client.get(detail))
    assert f'href="{url(target)}">Record result</a>' in body
    assert "<form" not in body
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=round_.pk)
        new = services.request_retest(locked, "Synthetic next", [case.pk])
    body = page(client.get(detail))
    assert url(target) not in body
    assert f'href="{url((round_, case, new))}">Record result</a>' in body
    with transaction.atomic():
        services.close(Round.objects.select_for_update().get(pk=round_.pk))
    body = page(client.get(detail))
    assert "Record result" not in body and "<form" not in body


@pytest.mark.ac("RES-2.1", "RES-2.5")
def test_save_reload_new_session_submit_and_read_only(tester, target):
    client = signed_in(tester)
    location = url(target)
    assert reverse("accounts:tester-result", args=[r.pk for r in target]) == location
    initial = client.get(location)
    no_store(initial)
    body = page(initial)
    assert "<title>Record result</title>" in body and "<h1>Record result</h1>" in body
    for text in (
        "Test case",
        "Current build",
        "Outcome",
        "Observation",
        "Back to round",
    ):
        assert text in body
    assert list(initial.context["form"].fields["outcome"].choices) == [
        ("", "---------"),
        ("pass", "Pass"),
        ("fail", "Fail"),
    ]
    assert Result.objects.count() == 0
    response = client.post(location, payload(observation=" Synthetic draft \r\nline "))
    assert response.status_code == 302 and response.url == location
    no_store(response)
    saved = Result.objects.get()
    assert saved.submitted_at is None and saved.observation == "Synthetic draft \nline"
    reloaded = signed_in(tester).get(location)
    assert "Status: Draft" in page(reloaded)
    assert reloaded.context["form"]["observation"].value() == saved.observation
    response = client.post(location, payload("fail", "Synthetic final", "submit"))
    assert response.status_code == 302 and response.url == location
    saved.refresh_from_db()
    assert saved.outcome == "fail" and saved.observation == "Synthetic final"
    assert saved.submitted_at is not None
    body = page(client.get(location))
    assert "Status: Submitted" in body and "Fail" in body and "Synthetic final" in body
    assert "<form" not in body and "<button" not in body


@pytest.mark.ac("RES-2.1", "RES-2.2")
@pytest.mark.parametrize("observation", ["", " \r\n\t "])
def test_direct_pass_submission_allows_empty_observation(tester, target, observation):
    client = signed_in(tester)
    response = client.post(
        url(target), payload(observation=observation, action="submit")
    )
    assert response.status_code == 302
    saved = Result.objects.get()
    assert saved.observation == "" and saved.submitted_at is not None
    assert "No observation." in page(client.get(url(target)))


@pytest.mark.ac("RES-2.2")
@pytest.mark.parametrize("action", ["save", "submit"])
@pytest.mark.parametrize("length", [1999, 2000, 2001])
def test_observation_length_boundaries(tester, target, action, length):
    response = signed_in(tester).post(
        url(target), payload("fail", "x" * length, action)
    )
    assert response.status_code == (302 if length <= 2000 else 200)
    if length <= 2000:
        assert len(Result.objects.get().observation) == length
    else:
        assert "Enter at most 2000 characters." in page(response)
        assert Result.objects.count() == 0


@pytest.mark.ac("RES-2.2")
@pytest.mark.parametrize("action", ["save", "submit"])
@pytest.mark.parametrize(
    "changes,field,message",
    [
        ({"outcome": ""}, "outcome", "Choose Pass or Fail."),
        ({"outcome": "unknown"}, "outcome", "Choose Pass or Fail."),
        ({"observation": ""}, "observation", "Enter an observation for Fail."),
        ({"observation": " \r\n "}, "observation", "Enter an observation for Fail."),
        ({"observation": "\u200b"}, "observation", "Enter an observation for Fail."),
        (
            {"observation": "visible\x00"},
            "observation",
            "Null characters are not allowed.",
        ),
        (
            {"observation": "visible\u202e"},
            "observation",
            "Hidden text-direction characters are not allowed.",
        ),
        ({"action": "other"}, "__all__", "Choose Save draft or Submit."),
        ({"action": ""}, "__all__", "Choose Save draft or Submit."),
    ],
)
def test_invalid_fields_independently_leave_draft_unchanged(
    tester, target, action, changes, field, message
):
    client = signed_in(tester)
    assert (
        client.post(url(target), payload(observation="Synthetic before")).status_code
        == 302
    )
    before = snapshot()
    data = payload("fail", "Synthetic valid", action) | changes
    response = client.post(url(target), data)
    assert response.status_code == 200 and message in page(response)
    assert list(response.context["form"].errors) == [field]
    assert response.context["form"]["observation"].value() == data["observation"]
    assert snapshot() == before
    no_store(response)


@pytest.mark.ac("RES-2.2")
def test_pass_invisible_only_and_missing_fields(tester, target):
    client = signed_in(tester)
    response = client.post(url(target), payload(observation="\u200b"))
    assert "Enter an observation with a visible character." in page(response)
    for missing, message in (
        ("outcome", "Choose Pass or Fail."),
        ("action", "Choose Save draft or Submit."),
    ):
        data = payload()
        data.pop(missing)
        response = client.post(url(target), data)
        assert response.status_code == 200 and message in page(response)
    data = payload()
    data.pop("observation")
    assert client.post(url(target), data).status_code == 302


@pytest.mark.ac("RES-2.2")
@pytest.mark.parametrize(
    "observation",
    ["é😊שלום\u200f\u200d", "  " + "x" * 2000 + "  ", "x\r\n" * 666 + "xx"],
)
def test_normalized_boundary_and_allowed_scripts(tester, target, observation):
    response = signed_in(tester).post(url(target), payload("fail", observation))
    assert response.status_code == 302
    assert Result.objects.get().observation == observation.replace("\r\n", "\n").strip()


@pytest.mark.ac("RES-2.3")
def test_same_workspace_identity_fields_cannot_select_another_result(tester, target):
    other = User.objects.create_user(
        "tester2-entry", "Synthetic16Chars", workspace=tester.workspace, role="tester"
    )
    owner = signed_in(tester)
    owner.post(url(target), payload(observation="Synthetic private", action="submit"))
    private = Result.objects.get()
    client = signed_in(other)
    body = page(client.get(url(target)))
    assert "Synthetic private" not in body and "Status: Submitted" not in body
    response = client.post(
        url(target),
        payload(observation="Synthetic other")
        | {
            "tester": tester.pk,
            "tester_id": tester.pk,
            "result_id": private.pk,
            "result": private.pk,
            "build_id": 999999,
            "case_id": 999999,
        },
    )
    assert response.status_code == 302
    private.refresh_from_db()
    assert (
        private.observation == "Synthetic private" and private.submitted_at is not None
    )
    assert Result.objects.get(tester=other).observation == "Synthetic other"


@pytest.mark.ac("RES-2.3")
@pytest.mark.parametrize("method", ["get", "post"])
def test_role_and_auth_precede_any_domain_lookup(coordinator, target, method):
    location = url(target)
    match = resolve(location)
    for user in (coordinator, AnonymousUser()):
        request = getattr(RequestFactory(), method)(location, payload())
        request.user = user
        with patch("rounds.results.workspace_records") as lookup:
            if user.is_authenticated:
                with pytest.raises(PermissionDenied):
                    match.func(request, **match.kwargs)
            else:
                response = match.func(request, **match.kwargs)
                assert response.status_code == 302 and response.url == "/sign-in/"
                no_store(response)
            lookup.assert_not_called()
    response = getattr(signed_in(coordinator), method)(location, payload())
    assert response.status_code == 403 and DENIED in page(response)


@pytest.mark.ac("RES-2.3", "RES-2.4")
@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "missing-case",
        "missing-build",
        "draft",
        "foreign",
        "case",
        "build",
        "coverage",
    ],
)
@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_foreign_and_cross_round_ids_are_fixed_404(
    tester, target, make_round, other_workspace, kind, method
):
    round_, case, build = target
    if kind == "missing":
        round_.pk = 2147483647
    elif kind == "missing-case":
        case.pk = 2147483647
    elif kind == "missing-build":
        build.pk = 2147483647
    elif kind == "draft":
        Round.objects.filter(pk=round_.pk).update(state=Round.State.DRAFT)
    elif kind == "foreign":
        Round.objects.filter(pk=round_.pk).update(
            workspace=other_workspace, state=Round.State.CLOSED
        )
    elif kind in ("case", "build"):
        other = open_with_case(make_round)
        Round.objects.filter(pk=round_.pk).update(state=Round.State.CLOSED)
        if kind == "case":
            case = other.cases.get()
        else:
            build = other.builds.get()
    else:
        BuildCase.objects.filter(case=case, build=build).delete()
        Round.objects.filter(pk=round_.pk).update(state=Round.State.CLOSED)
    before = snapshot()
    client = signed_in(tester)
    response = getattr(client, method)(url((round_, case, build)), payload())
    missing = client.get(
        "/tester/rounds/2147483647/cases/2147483647/builds/2147483647/result/"
    )
    assert response.status_code == 404 and response.content == missing.content
    assert NOT_FOUND in page(response)
    assert case.title not in page(response) and build.label not in page(response)
    assert snapshot() == before


@pytest.mark.ac("RES-2.4", "RES-2.5")
@pytest.mark.parametrize("conflict", ["closed", "stale", "submitted"])
def test_conflicts_precede_invalid_form_and_preserve_rows(tester, target, conflict):
    client = signed_in(tester)
    client.post(url(target), payload(action="submit"))
    round_, case, _ = target
    if conflict == "closed":
        with transaction.atomic():
            services.close(Round.objects.select_for_update().get(pk=round_.pk))
        message = "This action is not available while the round is Closed."
    elif conflict == "stale":
        with transaction.atomic():
            services.request_retest(
                Round.objects.select_for_update().get(pk=round_.pk),
                "Synthetic next",
                [case.pk],
            )
        message = results.STALE
    else:
        message = results.SUBMITTED
    before = snapshot()
    response = client.post(url(target), {})
    assert response.status_code == 409 and message in page(response)
    no_store(response)
    if conflict != "submitted":
        response = client.get(url(target))
        assert response.status_code == 409 and message in page(response)
        no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-2.7", "RES-2.6")
@pytest.mark.parametrize("method", ["head", "put", "delete", "options", "trace"])
def test_other_methods_are_uncached_405(tester, target, method):
    before = snapshot()
    response = getattr(signed_in(tester), method)(url(target))
    assert response.status_code == 405
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-2.7")
@pytest.mark.parametrize(
    "token,origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_csrf_rejects_before_any_result_write(tester, target, token, origin):
    client = signed_in(tester, enforce_csrf_checks=True)
    data = payload(action="submit")
    if token != "missing":
        data["csrfmiddlewaretoken"] = (
            csrf_token(client) if token == "valid" else "x" * 32
        )
    before = snapshot()
    response = client.post(
        url(target), data, **({"HTTP_ORIGIN": origin} if origin else {})
    )
    assert response.status_code == 403 and DENIED in page(response)
    assert snapshot() == before


@pytest.mark.ac("RES-2.7")
def test_valid_csrf_real_form_can_submit(tester, target):
    client = signed_in(tester, enforce_csrf_checks=True)
    assert client.get(url(target)).status_code == 200
    data = payload(action="submit") | {
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value
    }
    assert client.post(url(target), data).status_code == 302
    assert Result.objects.get().submitted_at is not None


@pytest.mark.ac("RES-2.6")
@pytest.mark.parametrize("failure", ["lookup", "lazy-user", "save", "render"])
def test_database_failures_are_fixed_503_without_observation_logging(
    tester, target, failure, caplog
):
    location = url(target)
    match = resolve(location)
    request = (
        RequestFactory().post(location, payload(observation="Synthetic sensitive"))
        if failure == "save"
        else RequestFactory().get(location)
    )
    request.user = tester
    before = snapshot()
    error = OperationalError("Synthetic sensitive")
    if failure == "lazy-user":

        def fail_user():
            raise error

        request.user = SimpleLazyObject(fail_user)
        response = match.func(request, **match.kwargs)
    elif failure == "render":
        original = tester_views.render

        def fail_render(request, template, *args, **kwargs):
            if template == "rounds/tester_result.html":
                raise error
            return original(request, template, *args, **kwargs)

        with patch.object(tester_views, "render", fail_render):
            response = match.func(request, **match.kwargs)
    else:
        target_patch = (
            "rounds.results.workspace_records"
            if failure == "lookup"
            else "rounds.models.Result.save"
        )
        with patch(target_patch, side_effect=error):
            response = match.func(request, **match.kwargs)
    assert response.status_code == 503 and UNAVAILABLE in page(response)
    assert (
        "Synthetic sensitive" not in caplog.text
        and "Synthetic sensitive" not in page(response)
    )
    no_store(response)
    assert snapshot() == before


@pytest.mark.ac("RES-2.6")
def test_failure_after_insert_rolls_back_at_route_boundary(tester, target):
    original = Result.save

    def fail_after_save(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise OperationalError("Synthetic failure")

    before = snapshot()
    with patch.object(Result, "save", fail_after_save):
        response = signed_in(tester).post(url(target), payload(action="submit"))
    assert response.status_code == 503
    assert snapshot() == before


@pytest.mark.ac("RES-2.8")
def test_coordinator_context_and_observation_escape_and_isolate(tester, target):
    _round, case, build = target
    case.title = MARKUP + "\nSynthetic context\u202e"
    case.save(update_fields=["title"])
    build.label = MARKUP + "\u2069"
    build.save(update_fields=["label"])
    client = signed_in(tester)
    initial = page(client.get(url(target)))
    for text in (MARKUP, "Synthetic context\u202e", MARKUP + "\u2069"):
        assert f'<span dir="auto">{escape(text)}</span>' in initial
    assert SCRIPT_TAG not in initial and IMG_TAG not in initial
    refused = client.post(url(target), payload("fail", MARKUP + "\u202e"))
    assert refused.status_code == 200
    assert escape(MARKUP) in page(refused) and SCRIPT_TAG not in page(refused)
    assert 'dir="auto"' in page(refused)
    assert (
        client.post(
            url(target), payload("fail", MARKUP + "\nSynthetic line", "submit")
        ).status_code
        == 302
    )
    # Stored values outside forms still require defensive direction isolation.
    Result.objects.update(observation=MARKUP + "\u202e\nSynthetic line\u200b")
    body = page(client.get(url(target)))
    assert (
        f'<span dir="auto">{escape(MARKUP)}\u202e</span><br>'
        '<span dir="auto">Synthetic line\u200b</span>' in body
    )
    assert SCRIPT_TAG not in body and IMG_TAG not in body and "<form" not in body
