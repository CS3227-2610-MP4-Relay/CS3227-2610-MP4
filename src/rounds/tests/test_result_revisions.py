"""RES-2 stale form protection, independent of ordinary fresh-form helpers."""

from unittest.mock import patch

import pytest
from django.db import connection

from accounts.models import User
from rounds.models import Result

from .conftest import domain_rows, no_store, open_with_case, page, signed_in

pytestmark = pytest.mark.django_db
CHANGED = "Your saved draft changed. Reload the result before saving or submitting."


@pytest.fixture
def entry_case(make_round, tester):
    """Return a client and one authorized current-build result URL."""
    round_ = open_with_case(make_round)
    case, build = round_.cases.get(), round_.builds.get()
    return signed_in(tester), (
        f"/tester/rounds/{round_.pk}/cases/{case.pk}/builds/{build.pk}/result/"
    )


def fields(revision, *, action="save", outcome="pass", observation=""):
    """Keep the expected revision explicit, even when intentionally stale."""
    return {
        "revision": revision,
        "action": action,
        "outcome": outcome,
        "observation": observation,
    }


@pytest.mark.ac("PLT-1.11", "RES-2.1", "RES-2.5")
def test_previous_runtime_can_insert_without_revision_after_migration(
    make_round, tester
):
    """Use the pre-revision INSERT columns against the fully migrated database."""
    round_ = open_with_case(make_round)
    case, build = round_.cases.get(), round_.builds.get()
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO rounds_result "
            "(tester_id, case_id, build_id, outcome, observation, submitted_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            [tester.pk, case.pk, build.pk, "pass", "Synthetic old-runtime draft", None],
        )
        result_id = cursor.fetchone()[0]
    saved = Result.objects.get(pk=result_id)
    assert saved.revision == 1
    assert saved.tester_id == tester.pk and saved.case_id == case.pk
    assert saved.build_id == build.pk and saved.submitted_at is None
    assert (saved.outcome, saved.observation) == ("pass", "Synthetic old-runtime draft")


@pytest.mark.ac("RES-2.1", "RES-2.5", "RES-4.9")
@pytest.mark.parametrize("action", ["save", "submit", "feedback"])
@pytest.mark.parametrize("existing", [False, True])
def test_stale_form_cannot_replace_newer_draft(entry_case, action, existing):
    client, url = entry_case
    revision = 0
    if existing:
        assert client.post(url, fields(0)).status_code == 302
        revision = 1
    obsolete = fields(revision, action=action)
    assert (
        client.post(
            url, fields(revision, outcome="fail", observation="Synthetic newer draft")
        ).status_code
        == 302
    )
    before = domain_rows()
    response = client.post(url, obsolete)
    assert response.status_code == 409
    assert CHANGED in page(response)
    assert domain_rows() == before
    no_store(response)
    saved = Result.objects.get()
    assert (saved.outcome, saved.observation, saved.submitted_at) == (
        "fail",
        "Synthetic newer draft",
        None,
    )


@pytest.mark.ac("RES-2.5", "RES-4.9")
@pytest.mark.parametrize("action", ["save", "submit", "feedback"])
@pytest.mark.parametrize("revision", [None, "", "bad", "-1", "1.0", "01", "9" * 10000])
def test_bad_revision_is_conflict_before_field_validation(entry_case, action, revision):
    client, url = entry_case
    data = fields(revision, action=action, outcome="invalid")
    if revision is None:
        data.pop("revision")
    before = domain_rows()
    with patch("ai.feedback_views.gateway.complete") as complete:
        response = client.post(url, data)
    assert response.status_code == 409 and CHANGED in page(response)
    complete.assert_not_called()
    assert domain_rows() == before
    no_store(response)


@pytest.mark.ac("RES-2.2", "RES-2.5", "RES-2.11", "RES-4.9")
@pytest.mark.parametrize("action", ["save", "submit", "feedback"])
@pytest.mark.parametrize("existing", [False, True])
def test_invalid_rerender_retains_revision_after_concurrent_save(
    entry_case, action, existing
):
    client, url = entry_case
    if existing:
        assert client.post(url, fields(0)).status_code == 302
    revision = 1 if existing else 0
    before = domain_rows()
    response = client.post(url, fields(revision, action=action, outcome="fail"))
    assert response.status_code == 200
    assert response.context["form"]["revision"].value() == str(revision)
    assert domain_rows() == before
    assert (
        client.post(
            url, fields(revision, observation="Synthetic saved elsewhere")
        ).status_code
        == 302
    )
    before = domain_rows()
    with patch("ai.feedback_views.gateway.complete") as complete:
        # Correcting the invalid fields retains the original rendered version.
        response = client.post(
            url, fields(revision, action=action, observation="Synthetic corrected")
        )
    assert response.status_code == 409 and CHANGED in page(response)
    complete.assert_not_called()
    assert domain_rows() == before
    # Even invalid stale fields cannot silently acquire the current revision.
    response = client.post(url, fields(revision, outcome="invalid"))
    assert response.status_code == 409
    assert domain_rows() == before


@pytest.mark.ac("RES-2.1", "RES-2.5")
def test_revision_advances_even_for_identical_or_changed_back_values(entry_case):
    client, url = entry_case
    for revision, observation in enumerate(
        (
            "Synthetic original",
            "Synthetic original",
            "Synthetic changed",
            "Synthetic original",
        )
    ):
        assert (
            client.post(url, fields(revision, observation=observation)).status_code
            == 302
        )
        assert Result.objects.get().revision == revision + 1
        form = client.get(url).context["form"]
        assert form["revision"].value() == revision + 1
        assert form["revision"].field.widget.is_hidden
    before = domain_rows()
    for revision in (0, 1, 2, 3):
        assert (
            client.post(
                url, fields(revision, action="submit", observation="Synthetic original")
            ).status_code
            == 409
        )
        assert domain_rows() == before
    assert (
        client.post(
            url, fields(4, action="submit", observation="Synthetic deliberate final")
        ).status_code
        == 302
    )
    saved = Result.objects.get()
    assert saved.revision == 5 and saved.submitted_at is not None


@pytest.mark.ac("RES-2.3", "RES-2.5")
def test_revision_and_posted_identity_cannot_select_another_testers_draft(
    entry_case, tester
):
    client, url = entry_case
    assert (
        client.post(url, fields(0, observation="Synthetic own draft")).status_code
        == 302
    )
    own = Result.objects.get()
    peer = User.objects.create_user(
        "revision-peer", "Synthetic16Chars", workspace=tester.workspace, role="tester"
    )
    other = Result.objects.create(
        tester=peer,
        case=own.case,
        build=own.build,
        outcome="fail",
        observation="Synthetic private peer",
        revision=7,
    )
    before = domain_rows()
    response = client.post(url, fields(7) | {"tester": peer.pk, "result": other.pk})
    assert response.status_code == 409 and CHANGED in page(response)
    assert "Synthetic private peer" not in page(response)
    assert domain_rows() == before
    assert (
        client.post(
            url,
            fields(1, observation="Synthetic deliberate own edit")
            | {"tester": peer.pk, "result": other.pk},
        ).status_code
        == 302
    )
    other.refresh_from_db()
    own.refresh_from_db()
    assert other.observation == "Synthetic private peer" and other.revision == 7
    assert own.observation == "Synthetic deliberate own edit" and own.revision == 2
