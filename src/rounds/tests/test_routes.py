"""Every rounds route is never cached, so a new route cannot forget it."""

from django.urls import reverse

from rounds import urls as rounds_urls

from .conftest import csrf_token, signed_in


def test_every_rounds_route_is_never_cached(coordinator, make_round):
    # Later slices whose routes name more records give them real IDs here.
    made = make_round()
    client = signed_in(coordinator, enforce_csrf_checks=True)
    token = csrf_token(client)
    assert rounds_urls.urlpatterns
    for pattern in rounds_urls.urlpatterns:
        kwargs = {name: made.pk for name in pattern.pattern.converters}
        url = reverse(f"rounds:{pattern.name}", kwargs=kwargs)
        response = client.get(url)
        if response.status_code == 405:
            response = client.post(url, HTTP_X_CSRFTOKEN=token)
        assert response.status_code < 400, url
        cache_control = response.get("Cache-Control", "")
        assert "no-store" in cache_control and "private" in cache_control, url
