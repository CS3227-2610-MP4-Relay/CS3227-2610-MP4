import pytest
from django.test import Client
from django.urls import path


def fail(request):
    """Raise a synthetic failure to exercise Django's generic error response."""
    raise RuntimeError("synthetic-private-detail")


urlpatterns = [path("failure/", fail)]


@pytest.mark.ac("PLT-1.1")
def test_public_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    html = response.content.decode()
    for text in (
        "<title>Relay</title>",
        "<h1>Relay</h1>",
        "A beta-testing portal for small software teams.",
        "Testing workflows are coming soon.",
    ):
        assert text in html
    assert "<form" not in html
    assert "<a " not in html
    assert client.head("/").status_code == 200
    assert client.head("/").content == b""


@pytest.mark.ac("PLT-1.2")
@pytest.mark.parametrize(
    "method", ["post", "put", "patch", "delete", "options", "trace"]
)
def test_landing_page_denies_other_methods(method):
    response = getattr(Client(enforce_csrf_checks=True), method)("/")
    assert response.status_code == 405
    assert set(response["Allow"].split(", ")) == {"GET", "HEAD"}


@pytest.mark.ac("PLT-1.3")
def test_missing_page_is_generic(client):
    response = client.get("/synthetic-private-detail/?detail=synthetic-private-detail")
    assert response.status_code == 404
    assert b"Not Found" in response.content
    assert b"synthetic-private-detail" not in response.content
    assert b"Traceback" not in response.content


@pytest.mark.ac("PLT-1.3")
def test_server_failure_is_generic(client, settings):
    settings.ROOT_URLCONF = __name__
    client.raise_request_exception = False
    response = client.get("/failure/?detail=synthetic-private-detail")
    assert response.status_code == 500
    assert b"Server Error" in response.content
    for private in (b"synthetic-private-detail", b"Traceback", b"test_pages.py"):
        assert private not in response.content


@pytest.mark.ac("PLT-1.4")
def test_unrecognized_host_is_rejected(client):
    assert client.get("/", HTTP_HOST="production.invalid").status_code == 400
