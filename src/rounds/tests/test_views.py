import re
import threading
from unittest import mock

import pytest
from django.db import DatabaseError, connection
from django.test import Client

from accounts.models import Workspace
from rounds.forms import RoundForm
from rounds.models import Round

from .conftest import (
    DENIED,
    LIMIT_MESSAGE,
    NEW,
    NOT_FOUND,
    TITLE_MESSAGE,
    UNAVAILABLE,
    csrf_token,
    detail,
    edit,
    page,
    signed_in,
)

pytestmark = pytest.mark.django_db
NULL_MESSAGE = "Null characters are not allowed."
CONFLICT = "This action is not available while the round is {}."
INVISIBLE_TITLES = [
    "",
    "   ",
    "\t\n ",
    "\u200b",
    "\u2060\ufeff\u200d",
    "\x01\x7f",
    "\u200b \u202e ",
]


def message_next_to_title(response, message):
    """Check the message sits after the Title field and before the button."""
    html = page(response)
    assert html.count(message) == 1
    assert html.index('name="title"') < html.index(message) < html.index("<button")


def created_round(response):
    match = re.fullmatch(r"/coordinator/rounds/(\d+)/", response["Location"])
    assert response.status_code == 302 and match
    return Round.objects.get(pk=match[1])


# RND-1.1


@pytest.mark.ac("RND-1.1")
def test_new_round_page_has_title_field_and_create_button(coord_client):
    html = page(coord_client.get(NEW))
    assert "<title>New round</title>" in html
    assert "<h1>New round</h1>" in html
    assert '<label for="id_title">Title</label>' in html
    assert '<button type="submit">Create round</button>' in html
    assert '<a href="/coordinator/">Coordinator home</a>' in html


@pytest.mark.ac("RND-1.1")
def test_creating_a_round_opens_its_draft_round_page(coord_client, coordinator):
    response = coord_client.post(NEW, {"title": "Synthetic checkout round"})
    made = created_round(response)
    assert made.workspace == coordinator.workspace
    assert made.state == Round.State.DRAFT
    html = page(coord_client.get(response["Location"]))
    assert '<h1><span dir="auto">Synthetic checkout round</span></h1>' in html
    assert "<p>State: Draft</p>" in html
    assert f'<a class="action secondary" href="{edit(made.pk)}">Edit round</a>' in html
    assert '<a href="/coordinator/">Coordinator home</a>' in html
    # From RND-2, "no criteria or cases" shows as the two empty sections.
    assert "<p>No acceptance criteria yet.</p>" in html
    assert "<p>No test cases yet.</p>" in html
    assert "<li>" not in html.split('<div class="records">', 1)[1]
    assert "<h3>" not in html
    assert "alert" not in html
    home = page(coord_client.get("/coordinator/"))
    assert (
        f'<li><a href="{detail(made.pk)}"><span dir="auto">'
        "Synthetic checkout round</span></a> (Draft)</li>"
    ) in home


@pytest.mark.ac("RND-1.1")
def test_coordinator_home_lists_own_rounds_newest_first_with_state(
    coord_client, make_round, other_workspace
):
    oldest = make_round("Synthetic oldest", Round.State.CLOSED)
    middle = make_round("Synthetic middle", Round.State.OPEN)
    newest = make_round("Synthetic newest")
    make_round("Synthetic foreign", owner=other_workspace)
    html = page(coord_client.get("/coordinator/"))
    assert "<h2>Rounds</h2>" in html
    assert '<a class="action" href="/coordinator/rounds/new/">New round</a>' in html
    item = r'<li><a href="([^"]+)"><span dir="auto">([^<]+)</span></a> \((\w+)\)</li>'
    items = re.findall(item, html)
    assert items == [
        (detail(newest.pk), "Synthetic newest", "Draft"),
        (detail(middle.pk), "Synthetic middle", "Open"),
        (detail(oldest.pk), "Synthetic oldest", "Closed"),
    ]
    assert "Synthetic foreign" not in html
    assert "No rounds yet." not in html


@pytest.mark.ac("RND-1.1")
def test_coordinator_home_without_rounds(coord_client):
    html = page(coord_client.get("/coordinator/"))
    assert "<h2>Rounds</h2>" in html
    assert "<p>No rounds yet.</p>" in html
    assert '<a class="action" href="/coordinator/rounds/new/">New round</a>' in html
    # ACC-1's home content stays.
    assert "Username: coord-rnd10001" in html
    assert "Sign out" in html


# RND-1.2


@pytest.mark.ac("RND-1.2")
def test_retitling_a_draft_round_shows_the_new_title(coord_client, make_round):
    made = make_round("Synthetic old title")
    form = page(coord_client.get(edit(made.pk)))
    assert "<title>Edit round</title>" in form
    assert "<h1>Edit round</h1>" in form
    assert 'value="Synthetic old title"' in form
    assert '<button type="submit">Save</button>' in form
    assert '<a href="/coordinator/">Coordinator home</a>' in form
    response = coord_client.post(edit(made.pk), {"title": "Synthetic new title"})
    assert response.status_code == 302
    assert response["Location"] == detail(made.pk)
    made.refresh_from_db()
    assert made.title == "Synthetic new title"
    for url in (detail(made.pk), "/coordinator/"):
        html = page(coord_client.get(url))
        assert "Synthetic new title" in html
        assert "Synthetic old title" not in html


# RND-1.3


@pytest.mark.ac("RND-1.3")
@pytest.mark.parametrize("action", ["create", "retitle"])
@pytest.mark.parametrize(
    "submitted, saved",
    [("a" * 120, "a" * 120), ("  " + "b" * 120 + "\n ", "b" * 120)],
    ids=["120", "120-after-trimming"],
)
def test_title_of_120_characters_is_saved(
    coord_client, make_round, action, submitted, saved
):
    if action == "create":
        made = created_round(coord_client.post(NEW, {"title": submitted}))
    else:
        made = make_round()
        assert coord_client.post(edit(made.pk), {"title": submitted}).status_code == 302
        made.refresh_from_db()
    assert made.title == saved


@pytest.mark.ac("RND-1.3")
@pytest.mark.parametrize("action", ["create", "retitle"])
@pytest.mark.parametrize(
    "submitted, message",
    [(title, TITLE_MESSAGE) for title in INVISIBLE_TITLES]
    + [("c" * 121, TITLE_MESSAGE), ("Synthetic\x00title", NULL_MESSAGE)],
)
def test_invalid_title_is_refused_next_to_the_field(
    coord_client, make_round, action, submitted, message
):
    made = make_round("Synthetic unchanged")
    url = NEW if action == "create" else edit(made.pk)
    response = coord_client.post(url, {"title": submitted})
    assert response.status_code == 200
    message_next_to_title(response, message)
    assert list(Round.objects.values_list("title", flat=True)) == [
        "Synthetic unchanged"
    ]


# RND-1.4


@pytest.mark.ac("RND-1.4")
def test_twentieth_round_is_created_and_twenty_first_refused(coord_client, make_round):
    for n in range(19):
        make_round(f"Synthetic {n}")
    created_round(coord_client.post(NEW, {"title": "Synthetic twentieth"}))
    response = coord_client.post(NEW, {"title": "Synthetic twenty-first"})
    assert response.status_code == 200
    message_next_to_title(response, LIMIT_MESSAGE)
    assert Round.objects.count() == 20
    assert not Round.objects.filter(title="Synthetic twenty-first").exists()


# RND-1.5


@pytest.mark.ac("RND-1.5")
@pytest.mark.django_db(transaction=True)
def test_one_of_five_simultaneous_creations_takes_the_last_place(coordinator):
    Round.objects.bulk_create(
        Round(workspace=coordinator.workspace, title=f"Synthetic {n}")
        for n in range(19)
    )
    clients = [signed_in(coordinator) for _ in range(5)]
    barrier = threading.Barrier(5)
    responses = [None] * 5

    def create(index):
        try:
            barrier.wait()
            responses[index] = clients[index].post(
                NEW, {"title": f"Synthetic racer {index}"}
            )
        finally:
            connection.close()

    threads = [threading.Thread(target=create, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 200, 200, 200, 302]
    for response in responses:
        if response.status_code == 200:
            message_next_to_title(response, LIMIT_MESSAGE)
    assert Round.objects.filter(workspace=coordinator.workspace).count() == 20


# RND-1.6


@pytest.mark.ac("RND-1.6")
@pytest.mark.parametrize(
    "route, method",
    [
        ("new", "get"),
        ("new", "post"),
        ("detail", "get"),
        ("edit", "get"),
        ("edit", "post"),
    ],
)
def test_tester_gets_the_same_403_for_existing_and_missing_rounds(
    tester, make_round, method, route
):
    made = make_round("Synthetic draft")
    missing = made.pk + 1000
    urls = {
        "new": (NEW, NEW),
        "detail": (detail(made.pk), detail(missing)),
        "edit": (edit(made.pk), edit(missing)),
    }[route]
    client = signed_in(tester)
    responses = [
        getattr(client, method)(url, {"title": "Synthetic tester title"})
        for url in urls
    ]
    for response in responses:
        assert response.status_code == 403
        assert DENIED in page(response)
        assert "Synthetic draft" not in page(response)
    assert responses[0].content == responses[1].content
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic draft"]


@pytest.mark.ac("RND-1.6")
def test_tester_home_shows_no_draft_round(tester, make_round):
    make_round("Synthetic hidden draft")
    html = page(signed_in(tester).get("/tester/"))
    assert "Synthetic hidden draft" not in html
    assert "Rounds" not in html


# RND-1.7: method, sign-in, role and CSRF


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("signed", [True, False])
@pytest.mark.parametrize(
    "route, methods",
    [
        ("new", ["put", "patch", "delete", "head"]),
        ("detail", ["post", "put", "delete", "head"]),
        ("edit", ["put", "patch", "delete", "head"]),
    ],
)
def test_unaccepted_methods_get_405(coordinator, make_round, signed, route, methods):
    made = make_round()
    url = {"new": NEW, "detail": detail(made.pk), "edit": edit(made.pk)}[route]
    client = signed_in(coordinator) if signed else Client()
    for method in methods:
        assert getattr(client, method)(url).status_code == 405, method
    assert Round.objects.count() == 1


@pytest.mark.ac("RND-1.7")
def test_signed_out_visitor_is_redirected_to_sign_in(make_round):
    made = make_round("Synthetic draft")
    client = Client(enforce_csrf_checks=True)
    token = csrf_token(client)
    for url in (NEW, detail(made.pk), edit(made.pk)):
        response = client.get(url)
        assert response.status_code == 302 and response["Location"] == "/sign-in/"
    for url in (NEW, edit(made.pk)):
        response = client.post(
            url, {"title": "Synthetic anonymous", "csrfmiddlewaretoken": token}
        )
        assert response.status_code == 302 and response["Location"] == "/sign-in/"
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic draft"]


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("route", ["new", "edit"])
@pytest.mark.parametrize(
    "token, origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_post_without_valid_csrf_or_same_origin_gets_403(
    coordinator, make_round, route, token, origin
):
    made = make_round("Synthetic draft")
    url = NEW if route == "new" else edit(made.pk)
    client = signed_in(coordinator, enforce_csrf_checks=True)
    valid = csrf_token(client)
    data = {"title": "Synthetic forged"}
    if token != "missing":
        data["csrfmiddlewaretoken"] = valid if token == "valid" else "x" * 32
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    response = client.post(url, data, **extra)
    assert response.status_code == 403
    assert DENIED in page(response)
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic draft"]
    # The same request with a valid token and no foreign Origin succeeds.
    data["csrfmiddlewaretoken"] = valid
    assert client.post(url, data).status_code == 302


# RND-1.7: workspace (404) before state (409)


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("state", ["draft", "open", "closed", "missing"])
def test_other_workspace_or_missing_round_gets_404_not_409(
    coord_client, make_round, other_workspace, state
):
    if state == "missing":
        target = make_round("Synthetic own")
        round_id = target.pk + 1000
    else:
        target = make_round("Synthetic foreign", state, owner=other_workspace)
        round_id = target.pk
    responses = [
        coord_client.get(detail(round_id)),
        coord_client.get(edit(round_id)),
        coord_client.post(edit(round_id), {"title": "Synthetic hijack"}),
    ]
    reference = coord_client.get("/coordinator/rounds/999999/")
    for response in responses:
        assert response.status_code == 404
        assert NOT_FOUND in page(response)
        assert response.content == reference.content
    target.refresh_from_db()
    assert target.title in ("Synthetic own", "Synthetic foreign")


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("state, name", [("open", "Open"), ("closed", "Closed")])
def test_retitling_an_open_or_closed_round_gets_409(
    coord_client, make_round, state, name
):
    made = make_round("Synthetic frozen", state)
    for response in (
        coord_client.get(edit(made.pk)),
        coord_client.post(edit(made.pk), {"title": "Synthetic changed"}),
        coord_client.post(edit(made.pk), {"title": ""}),
    ):
        assert response.status_code == 409
        html = page(response)
        assert "<title>Action not available</title>" in html
        assert f"<h1>{CONFLICT.format(name)}</h1>" in html
        cache_control = response["Cache-Control"]
        assert "no-store" in cache_control and "private" in cache_control
    made.refresh_from_db()
    assert made.title == "Synthetic frozen"
    html = page(coord_client.get(detail(made.pk)))
    assert f"<p>State: {name}</p>" in html
    assert "Edit round" not in html


@pytest.mark.ac("RND-1.7")
def test_round_opened_after_the_state_check_gets_409_from_the_locked_recheck(
    coord_client, make_round
):
    made = make_round("Synthetic racing")
    real_is_valid = RoundForm.is_valid

    def open_then_validate(form):
        Round.objects.filter(pk=made.pk).update(state=Round.State.OPEN)
        return real_is_valid(form)

    with mock.patch.object(RoundForm, "is_valid", open_then_validate):
        response = coord_client.post(edit(made.pk), {"title": "Synthetic changed"})
    assert response.status_code == 409
    assert CONFLICT.format("Open") in page(response)
    made.refresh_from_db()
    assert made.title == "Synthetic racing"


@pytest.mark.ac("RND-1.7")
def test_round_workspace_comes_from_the_signed_in_user(
    coord_client, coordinator, other_workspace
):
    made = created_round(
        coord_client.post(NEW, {"title": "Synthetic", "workspace": other_workspace.pk})
    )
    assert made.workspace == coordinator.workspace
    assert not Round.objects.filter(workspace=other_workspace).exists()


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("action", ["create", "retitle"])
def test_storage_failure_gives_503_and_changes_nothing(
    coord_client, make_round, action, caplog
):
    made = make_round("Synthetic stored")
    url = NEW if action == "create" else edit(made.pk)
    with mock.patch.object(Round, "save", side_effect=DatabaseError("synthetic")):
        response = coord_client.post(url, {"title": "Synthetic failed"})
    assert response.status_code == 503
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control and "private" in cache_control
    assert UNAVAILABLE in page(response)
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic stored"]
    assert Workspace.objects.count() == 1
    assert_storage_failure_logged(caplog)


def test_round_pages_are_never_cached(coord_client, make_round):
    made = make_round()
    for url in (NEW, detail(made.pk), edit(made.pk)):
        cache_control = coord_client.get(url)["Cache-Control"]
        assert "no-store" in cache_control and "private" in cache_control


def assert_storage_failure_logged(caplog):
    records = [record for record in caplog.records if record.name == "rounds.views"]
    assert len(records) == 1
    assert records[0].exc_info is not None
    assert records[0].exc_info[0] is DatabaseError


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("route", ["detail", "edit"])
def test_storage_failure_reading_a_round_gives_503(
    coord_client, make_round, route, caplog
):
    made = make_round("Synthetic stored")
    url = detail(made.pk) if route == "detail" else edit(made.pk)
    with mock.patch(
        "rounds.views.get_object_or_404", side_effect=DatabaseError("synthetic")
    ):
        response = coord_client.get(url)
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    assert "Synthetic stored" not in page(response)
    assert "no-store" in response["Cache-Control"]
    assert_storage_failure_logged(caplog)


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("route", ["new", "detail", "edit"])
def test_storage_failure_loading_the_user_gives_503_before_any_lookup(
    coord_client, make_round, route, caplog
):
    made = make_round("Synthetic stored")
    url = {"new": NEW, "detail": detail(made.pk), "edit": edit(made.pk)}[route]
    with (
        mock.patch(
            "django.contrib.auth.get_user", side_effect=DatabaseError("synthetic")
        ),
        mock.patch("rounds.views.get_object_or_404") as lookup,
    ):
        response = coord_client.get(url)
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    lookup.assert_not_called()
    assert_storage_failure_logged(caplog)


def test_coordinator_home_keeps_the_accounts_storage_rule(coord_client):
    coord_client.raise_request_exception = False
    with mock.patch(
        "django.contrib.auth.get_user", side_effect=DatabaseError("synthetic")
    ):
        response = coord_client.get("/coordinator/")
    assert response.status_code == 500
    assert UNAVAILABLE not in page(response)


# RND-1.7: CSRF and Origin come before 405 and the sign-in redirect


def csrf_client_for(user):
    return (
        signed_in(user, enforce_csrf_checks=True)
        if user
        else Client(enforce_csrf_checks=True)
    )


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("signed", [True, False])
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("route", ["new", "detail", "edit"])
def test_unsafe_request_without_a_token_gets_403_first(
    coordinator, make_round, signed, method, route
):
    made = make_round("Synthetic draft")
    url = {"new": NEW, "detail": detail(made.pk), "edit": edit(made.pk)}[route]
    client = csrf_client_for(coordinator if signed else None)
    if method == "post":
        response = client.post(url, {"title": "Synthetic forged"})
    else:
        response = getattr(client, method)(url)
    assert response.status_code == 403
    assert DENIED in page(response)
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic draft"]


@pytest.mark.ac("RND-1.7")
@pytest.mark.parametrize("signed", [True, False])
def test_unaccepted_method_with_a_valid_token_gets_405_uncached(
    coordinator, make_round, signed
):
    made = make_round("Synthetic draft")
    client = csrf_client_for(coordinator if signed else None)
    token = csrf_token(client)
    for method, url in [
        ("put", NEW),
        ("patch", NEW),
        ("post", detail(made.pk)),
        ("put", detail(made.pk)),
        ("put", edit(made.pk)),
        ("delete", edit(made.pk)),
    ]:
        response = getattr(client, method)(url, HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 405, (method, url)
        cache_control = response["Cache-Control"]
        assert "no-store" in cache_control and "private" in cache_control
    assert list(Round.objects.values_list("title", flat=True)) == ["Synthetic draft"]
