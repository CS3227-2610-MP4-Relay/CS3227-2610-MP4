"""PLT-4.18: tester-account pages put their links in a top page navigation."""

import re

import pytest

from accounts.models import User
from accounts.tests.test_add_tester import LIMIT, SAVE, URL, row, seed, signed_in
from accounts.tests.test_add_tester import uncached as no_store
from accounts.tests.test_reset_tester_password import LIST, reset_url

pytestmark = pytest.mark.django_db
NAVIGATION = '<nav class="page-navigation" aria-label="Page navigation">'
HOME = ("Coordinator home", "/coordinator/")
PASSWORDS = ("Beta Tester passwords", LIST)


def assert_top_navigation(response, *links):
    """Exactly these links, once each, in a navigation before the only heading."""
    body = response.content.decode()
    assert body.count(NAVIGATION) == 1 and body.count("<h1>") == 1
    start = body.index(NAVIGATION)
    end = body.index("</nav>", start)
    assert end < body.index("<h1>")
    expected = "".join(
        f'<a class="action secondary" href="{href}">{label}</a>'
        for label, href in links
    )
    assert body[start + len(NAVIGATION) : end] == expected
    assert body.count("<a ") == len(links)
    for label, href in links:
        assert body.count(f">{label}</a>") == 1
        assert body.count(f'href="{href}"') == 1
    return body


@pytest.mark.ac("PLT-4.18", "ACC-4.1")
def test_tester_added_links_home_before_heading_and_credentials():
    workspace, coord = seed()
    response = signed_in(coord).post(URL)
    assert response.status_code == 200
    no_store(response)
    body = assert_top_navigation(response, HOME)
    role, username, _password = row(response)
    assert role == "Beta Tester"
    assert workspace.accounts.filter(username=username, role="tester").exists()
    assert "<h1>Beta Tester added</h1>" in body
    assert body.index(f"<p>Workspace: {workspace.name}</p>") < body.index("<table>")
    assert body.index("<table>") < body.index(SAVE)
    assert workspace.accounts.filter(role="tester").count() == 3


@pytest.mark.ac("PLT-4.18", "ACC-4.2")
def test_tester_limit_links_home_before_heading_and_creates_nothing():
    workspace, coord = seed(10)
    response = signed_in(coord).post(URL)
    assert response.status_code == 409
    no_store(response)
    body = assert_top_navigation(response, HOME)
    assert f"<h1>{LIMIT}</h1>" in body
    assert "<title>Tester limit reached</title>" in body
    assert workspace.accounts.filter(role="tester").count() == 10


@pytest.mark.ac("PLT-4.18", "ACC-5.1")
@pytest.mark.parametrize("count", [0, 1, 10])
def test_tester_passwords_links_home_before_heading_and_list(count):
    workspace, coord = seed(count)
    response = signed_in(coord).get(LIST)
    assert response.status_code == 200
    no_store(response)
    body = assert_top_navigation(response, HOME)
    assert "<h1>Beta Tester passwords</h1>" in body
    assert body.count(">Reset password</button>") == count
    if count == 0:
        assert "<li>This workspace has no Beta Testers.</li>" in body
    testers = workspace.accounts.filter(role="tester").order_by("pk")
    for tester in testers:
        assert body.index("</nav>") < body.index(f'action="{reset_url(tester)}"')


@pytest.mark.ac("PLT-4.18", "ACC-5.1")
def test_password_reset_links_home_then_passwords_before_heading():
    workspace, coord = seed()
    tester = workspace.accounts.filter(role="tester").order_by("pk").first()
    old = User.objects.get(pk=tester.pk).password
    response = signed_in(coord).post(reset_url(tester))
    assert response.status_code == 200
    no_store(response)
    body = assert_top_navigation(response, HOME, PASSWORDS)
    assert "<h1>Beta Tester password reset</h1>" in body
    role, username, password = row(response)
    assert (role, username) == ("Beta Tester", tester.username)
    assert re.fullmatch(r"[a-zA-Z0-9]{16}", password)
    assert body.index("<table>") < body.index(SAVE)
    assert User.objects.get(pk=tester.pk).password != old
