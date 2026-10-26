"""RND-2.8: unusual record IDs in criterion and case URLs get the standard 404."""

import pytest

from rounds.models import Case, CaseCriterion, Criterion, Round

from .conftest import NOT_FOUND, page

pytestmark = [pytest.mark.django_db, pytest.mark.ac("RND-2.8")]

HUGE = "99999999999999999999"


def everything():
    return (
        list(Criterion.objects.values()),
        list(Case.objects.values()),
        list(CaseCriterion.objects.values()),
        list(Round.objects.values()),
    )


def seed(round_):
    linked = Criterion.objects.create(round=round_, text="Synthetic criterion")
    made = Case.objects.create(
        round=round_, title="Synthetic", steps="Synthetic", expected_result="Synthetic"
    )
    CaseCriterion.objects.create(case=made, criterion=linked)
    return linked


def post_data(kind, linked):
    if kind == "criteria":
        return {"text": "Synthetic changed"}
    return {
        "title": "Synthetic changed",
        "steps": "Synthetic",
        "expected_result": "Synthetic",
        "criteria": [linked.pk],
    }


@pytest.mark.parametrize("state", ["draft", "open", "closed"])
@pytest.mark.parametrize("record_id", ["0", "00", HUGE])
@pytest.mark.parametrize("kind", ["criteria", "cases"])
def test_zero_or_oversized_record_ids_get_404(
    coord_client, make_round, state, record_id, kind
):
    made = make_round("Synthetic round", state)
    linked = seed(made)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    base = f"/coordinator/rounds/{made.pk}/{kind}/{record_id}"
    attempts = [
        ("get", f"{base}/edit/", None),
        ("post", f"{base}/edit/", post_data(kind, linked)),
        ("post", f"{base}/delete/", None),
    ]
    for method, route, data in attempts:
        response = getattr(coord_client, method)(route, data)
        assert response.status_code == 404, (method, route)
        assert response.content == reference.content
        assert NOT_FOUND in page(response)
    assert everything() == before
