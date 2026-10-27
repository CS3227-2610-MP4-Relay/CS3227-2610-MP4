"""Every rounds route is never cached, so a new route cannot forget it."""

from django.urls import reverse

from rounds import urls as rounds_urls
from rounds.models import Case, CaseCriterion, Criterion, Round

from .conftest import csrf_token, signed_in


def test_every_rounds_route_is_never_cached(coordinator, make_round):
    # Later slices whose routes name more records give them real IDs here.
    made = make_round()
    # The criterion stays linked, so its delete route is refused with a 200.
    linked = Criterion.objects.create(round=made, text="Synthetic criterion")
    case = Case.objects.create(
        round=made, title="Synthetic", steps="Synthetic", expected_result="Synthetic"
    )
    CaseCriterion.objects.create(case=case, criterion=linked)
    opened = make_round("Synthetic open", Round.State.OPEN)
    # A separate Open round for the retest page, which only an Open round has.
    retested = make_round("Synthetic retest", Round.State.OPEN)
    ids = {"round_id": made.pk, "criterion_id": linked.pk, "case_id": case.pk}
    client = signed_in(coordinator, enforce_csrf_checks=True)
    token = csrf_token(client)
    assert rounds_urls.urlpatterns
    for pattern in rounds_urls.urlpatterns:
        kwargs = {name: ids[name] for name in pattern.pattern.converters}
        if pattern.name == "close":
            # Only an Open round closes (RND-6); the Draft round stays Draft.
            kwargs["round_id"] = opened.pk
        if pattern.name == "retest":
            kwargs["round_id"] = retested.pk
        url = reverse(f"rounds:{pattern.name}", kwargs=kwargs)
        response = client.get(url)
        if response.status_code == 405:
            response = client.post(url, HTTP_X_CSRFTOKEN=token)
        assert response.status_code < 400, url
        cache_control = response.get("Cache-Control", "")
        assert "no-store" in cache_control and "private" in cache_control, url
        if pattern.name == "publish":
            # The walk posts no label, so the Draft round page comes back.
            assert response.status_code == 200, url
            assert "Enter 1 to 100 characters." in response.content.decode()
        if pattern.name == "close":
            assert response.status_code == 302, url
        if pattern.name == "retest":
            assert response.status_code == 200, url
    names = {pattern.name for pattern in rounds_urls.urlpatterns}
    assert {"close", "retest"} <= names


def test_publishing_and_the_open_round_page_are_never_cached(coordinator, make_round):
    made = make_round()
    linked = Criterion.objects.create(round=made, text="Synthetic criterion")
    case = Case.objects.create(
        round=made, title="Synthetic", steps="Synthetic", expected_result="Synthetic"
    )
    CaseCriterion.objects.create(case=case, criterion=linked)
    client = signed_in(coordinator)
    published = client.post(
        reverse("rounds:publish", args=[made.pk]), {"label": "Synthetic 1.0"}
    )
    opened = client.get(reverse("rounds:detail", args=[made.pk]))
    assert (published.status_code, opened.status_code) == (302, 200)
    for response in (published, opened):
        cache_control = response.get("Cache-Control", "")
        assert "no-store" in cache_control and "private" in cache_control
