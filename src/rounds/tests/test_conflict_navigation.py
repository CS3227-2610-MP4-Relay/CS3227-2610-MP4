"""PLT-4.15: coordinator round-state conflicts link home and back to the round."""

from unittest import mock

import pytest
from django.db import transaction
from django.urls import reverse

from rounds import services
from rounds.models import Criterion

from .conftest import (
    NOT_FOUND,
    assert_conflict_links,
    domain_rows,
    draft_with_case,
    locked,
    no_store,
    page,
    signed_in,
)

pytestmark = pytest.mark.django_db
CONFLICT = "This action is not available while the round is {}."

# (method, route name, record the route names besides the round)
DRAFT_ONLY = [
    ("get", "rounds:edit", None),
    ("post", "rounds:edit", None),
    ("get", "rounds:criterion-new", None),
    ("post", "rounds:criterion-new", None),
    ("get", "rounds:criterion-edit", "criterion"),
    ("post", "rounds:criterion-delete", "criterion"),
    ("get", "rounds:case-new", None),
    ("get", "rounds:case-edit", "case"),
    ("post", "rounds:case-delete", "case"),
    ("post", "rounds:publish", None),
    ("get", "ai:draft", None),
    ("post", "ai:draft", None),
    ("post", "ai:use-draft", None),
]
OPEN_ONLY = [
    ("get", "rounds:retest", None),
    ("post", "rounds:retest", None),
    ("post", "rounds:close", None),
]
REFUSALS = (
    [("Open", *route) for route in DRAFT_ONLY]
    + [("Closed", *route) for route in DRAFT_ONLY]
    + [("Draft", *route) for route in OPEN_ONLY]
    + [("Closed", *route) for route in OPEN_ONLY]
    + [("Draft", "get", "rounds:results", None)]
)


def round_in(make_round, state, owner=None):
    """A round in `state` with one criterion and one case."""
    round_ = draft_with_case(lambda: make_round(owner=owner))
    Criterion.objects.create(round=round_, text="Synthetic criterion")
    if state != "Draft":
        with transaction.atomic():
            services.publish(locked(round_), "Synthetic 1.0")
    if state == "Closed":
        with transaction.atomic():
            services.close(locked(round_))
    return round_


def route(name, round_, record):
    """The URL of `name` for `round_` and, when named, its first record."""
    args = [round_.pk]
    if record == "criterion":
        args.append(round_.criteria.get().pk)
    elif record == "case":
        args.append(round_.cases.get().pk)
    return reverse(name, args=args)


@pytest.mark.ac("PLT-4.15")
@pytest.mark.parametrize("state,method,name,record", REFUSALS)
def test_round_state_conflicts_link_home_and_back_to_round(
    coordinator, make_round, state, method, name, record
):
    round_ = round_in(make_round, state)
    before = domain_rows()
    with mock.patch("ai.views.gateway.complete") as complete:
        response = getattr(signed_in(coordinator), method)(route(name, round_, record))
    assert response.status_code == 409
    body = page(response)
    assert "<title>Action not available</title>" in body
    assert f"<h1>{CONFLICT.format(state)}</h1>" in body
    no_store(response)
    assert_conflict_links(
        response,
        ("Coordinator home", reverse("accounts:coordinator")),
        ("Back to round", reverse("rounds:detail", args=[round_.pk])),
    )
    complete.assert_not_called()
    assert domain_rows() == before


@pytest.mark.ac("PLT-4.15")
@pytest.mark.parametrize(
    "state,method,name,record",
    [
        ("Open", "get", "rounds:edit", None),
        ("Open", "post", "rounds:case-delete", "case"),
        ("Closed", "post", "rounds:close", None),
        ("Draft", "get", "rounds:results", None),
        ("Open", "get", "ai:draft", None),
    ],
)
def test_foreign_round_conflicts_stay_404_without_navigation(
    coordinator, make_round, other_workspace, state, method, name, record
):
    foreign = round_in(make_round, state, owner=other_workspace)
    before = domain_rows()
    response = getattr(signed_in(coordinator), method)(route(name, foreign, record))
    assert response.status_code == 404
    body = page(response)
    assert NOT_FOUND in body
    assert "Coordinator home" not in body and "Back to round" not in body
    assert reverse("rounds:detail", args=[foreign.pk]) not in body
    assert domain_rows() == before
