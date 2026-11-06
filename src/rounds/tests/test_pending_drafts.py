"""RND-6.6: disclose eligible draft existence without exposing private results."""

from unittest import mock

import pytest
from django.db import DatabaseError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import User
from rounds import results
from rounds.models import Build, Result, Round

from .conftest import detail, domain_rows, no_store, page, signed_in
from .test_close import WARNING, close_url, published

pytestmark = [pytest.mark.django_db, pytest.mark.ac("RND-6.6")]
PENDING = (
    "Saved drafts are still pending for current builds. "
    "Closing will prevent their submission."
)
LIMIT = "This reflects saved drafts at page load. Unsaved browser changes are unknown."


@pytest.fixture
def pending(make_round, tester):
    round_ = published(make_round())
    row = Result.objects.create(
        tester=tester,
        case=round_.cases.first(),
        build=round_.builds.first(),
        outcome="fail",
        observation="Synthetic private observation",
    )
    return round_, row


def test_pending_draft_warning_is_private_read_only_and_does_not_block_close(
    coord_client, pending, tester
):
    round_, row = pending
    before = domain_rows()
    with CaptureQueriesContext(connection) as queries:
        response = coord_client.get(detail(round_.pk), {"tester": 999, "result": 999})
    html = page(response)
    assert html.index(PENDING) < html.index(LIMIT) < html.index(WARNING)
    assert response.context["pending_drafts"] is True
    assert row.observation not in html and tester.username not in html
    assert "Outcome:" not in html and "Tester:" not in html
    reads = [q["sql"] for q in queries if 'FROM "rounds_result"' in q["sql"]]
    assert len(reads) == 1 and reads[0].startswith("SELECT 1 AS")
    assert '"observation"' not in reads[0] and '"outcome"' not in reads[0]
    no_store(response)
    assert domain_rows() == before
    assert coord_client.post(close_url(round_.pk)).status_code == 302
    assert list(Result.objects.values()) == before[Result]
    assert PENDING not in page(coord_client.get(detail(round_.pk)))


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "submitted",
        "earlier",
        "uncovered",
        "foreign_case",
        "foreign_build",
        "foreign_tester",
        "coordinator",
    ],
)
def test_ineligible_results_do_not_trigger_warning(
    coord_client, pending, make_round, other_workspace, coordinator, kind
):
    round_, row = pending
    if kind == "none":
        row.delete()
    else:
        if kind == "submitted":
            row.submitted_at = timezone.now()
        elif kind == "earlier":
            newer = Build.objects.create(round=round_, label="Synthetic new", key="new")
            newer.cases.add(row.case)
        elif kind == "uncovered":
            row.build.cases.remove(row.case)
        elif kind in ("foreign_case", "foreign_build"):
            foreign = published(make_round(owner=other_workspace))
            if kind == "foreign_case":
                row.case = foreign.cases.first()
                row.build.cases.add(row.case)
            else:
                row.build = foreign.builds.first()
                row.build.cases.add(row.case)
        elif kind == "foreign_tester":
            row.tester = User.objects.create_user(
                "Synthetic foreign tester",
                None,
                workspace=other_workspace,
                role="tester",
            )
        elif kind == "coordinator":
            row.tester = coordinator
        row.save()
    html = page(coord_client.get(detail(round_.pk)))
    assert PENDING not in html and LIMIT not in html
    assert WARNING in html


def test_reload_tracks_multiple_drafts_submissions_and_partial_retest(
    coord_client, pending, tester
):
    round_, first = pending
    second = Result.objects.create(
        tester=tester, case=round_.cases.last(), build=first.build, outcome="pass"
    )
    other = User.objects.create_user(
        "Synthetic second tester", None, workspace=tester.workspace, role="tester"
    )
    third = Result.objects.create(
        tester=other, case=first.case, build=first.build, outcome="pass"
    )
    newer = Build.objects.create(round=round_, label="Synthetic retest", key="retest")
    newer.cases.add(first.case)
    assert PENDING in page(coord_client.get(detail(round_.pk)))
    second.submitted_at = timezone.now()
    second.save()
    assert PENDING not in page(coord_client.get(detail(round_.pk)))
    third.build = newer
    third.save()
    assert PENDING in page(coord_client.get(detail(round_.pk)))


@pytest.mark.parametrize("state", [Round.State.DRAFT, Round.State.CLOSED])
def test_non_open_pages_skip_draft_query(coord_client, pending, state):
    round_, _ = pending
    round_.state = state
    round_.save()
    with mock.patch.object(results, "covered_results", side_effect=AssertionError):
        response = coord_client.get(detail(round_.pk))
    assert response.status_code == 200
    assert PENDING not in page(response)


def test_authorization_precedes_draft_query(
    coord_client, pending, tester, make_round, other_workspace
):
    round_, _ = pending
    foreign = make_round(owner=other_workspace)
    with mock.patch.object(results, "covered_results", side_effect=AssertionError):
        assert Client().get(detail(round_.pk)).status_code == 302
        assert signed_in(tester).get(detail(round_.pk)).status_code == 403
        for pk in (foreign.pk, 999999):
            response = coord_client.get(detail(pk))
            assert response.status_code == 404
            assert PENDING not in page(response)


def test_draft_read_storage_failure_is_fixed_and_never_cached(coord_client, pending):
    round_, row = pending
    with mock.patch.object(results, "covered_results", side_effect=DatabaseError):
        response = coord_client.get(detail(round_.pk))
    assert response.status_code == 503
    assert "Relay is temporarily unavailable. Try again later." in page(response)
    assert row.observation not in page(response) and PENDING not in page(response)
    no_store(response)
