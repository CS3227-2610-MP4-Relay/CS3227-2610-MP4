"""RND-2: managing a round's acceptance criteria and test cases through its pages."""

import threading
import time
from unittest import mock

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client

from rounds import services
from rounds.forms import CaseForm, CriterionForm
from rounds.models import BuildCase, Case, CaseCriterion, Criterion, Round

from .conftest import (
    DENIED,
    NOT_FOUND,
    UNAVAILABLE,
    csrf_token,
    detail,
    page,
    signed_in,
)

pytestmark = pytest.mark.django_db

CONFLICT = "This action is not available while the round is {}."
NO_LINK = "Link at least one acceptance criterion."
FOREIGN = "Choose criteria from this round."
LINKED = "This criterion is linked to a test case. Unlink it first."
CRITERION_CAP = "This round has reached its limit of 20 acceptance criteria."
CASE_CAP = "This round has reached its limit of 30 test cases."
NULL_MESSAGE = "Null characters are not allowed."
CR, LF, ZWSP = chr(13), chr(10), chr(0x200B)


def url(round_id, kind, action, record_id=None):
    """A criteria or cases route; `kind` is "criteria" or "cases"."""
    middle = "new" if record_id is None else f"{record_id}/{action}"
    return f"/coordinator/rounds/{round_id}/{kind}/{middle}/"


def criterion(round_, text="Synthetic criterion"):
    return Criterion.objects.create(round=round_, text=text)


def case(round_, linked, title="Synthetic case", **fields):
    made = Case.objects.create(
        round=round_,
        title=title,
        steps=fields.get("steps", "Synthetic steps"),
        expected_result=fields.get("expected_result", "Synthetic result"),
    )
    for item in linked:
        CaseCriterion.objects.create(case=made, criterion=item)
    return made


def case_data(*linked, **fields):
    data = {
        "title": "Synthetic case",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": [item.pk for item in linked],
    }
    data.update(fields)
    return data


def stored(round_):
    """Everything stored for a round's criteria and cases."""
    return (
        list(Criterion.objects.filter(round=round_).values()),
        list(Case.objects.filter(round=round_).values()),
        list(CaseCriterion.objects.filter(case__round=round_).values()),
    )


def everything():
    return (
        list(Criterion.objects.values()),
        list(Case.objects.values()),
        list(CaseCriterion.objects.values()),
        list(Round.objects.values()),
    )


def message_next_to(html, field, message, following):
    """The message appears once, after `field`'s input and before `following`."""
    assert html.count(message) == 1
    start = html.index(f'name="{field}"')
    assert start < html.index(message) < html.index(following, start)


def redirects_to_round(response, round_):
    assert response.status_code == 302
    assert response["Location"] == detail(round_.pk)


def no_store(response):
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control and "private" in cache_control


@pytest.fixture
def draft(make_round):
    return make_round("Synthetic draft round")


# RND-2.1


@pytest.mark.ac("RND-2.1")
def test_new_criterion_page_has_text_field_and_add_button(coord_client, draft):
    html = page(coord_client.get(url(draft.pk, "criteria", "new")))
    assert "<title>New acceptance criterion</title>" in html
    assert "<h1>New acceptance criterion</h1>" in html
    assert '<label for="id_text">Text</label>' in html
    assert '<textarea name="text"' in html and 'dir="auto"' in html
    assert '<button type="submit">Add acceptance criterion</button>' in html
    assert f'<a href="{detail(draft.pk)}">Back to round</a>' in html


@pytest.mark.ac("RND-2.1")
def test_adding_criteria_shows_them_on_the_round_page_in_creation_order(
    coord_client, draft
):
    for text in ("Synthetic first", "Synthetic second"):
        response = coord_client.post(url(draft.pk, "criteria", "new"), {"text": text})
        redirects_to_round(response, draft)
    html = page(coord_client.get(detail(draft.pk)))
    first, second = Criterion.objects.filter(round=draft)
    assert first.text == "Synthetic first" and second.text == "Synthetic second"
    assert "<h2>Acceptance criteria</h2>" in html
    assert html.index("Synthetic first") < html.index("Synthetic second")
    assert html.index("<h2>Acceptance criteria</h2>") < html.index("Synthetic first")
    assert html.index("Synthetic second") < html.index("<h2>Test cases</h2>")
    assert f'<a class="action" href="{url(draft.pk, "criteria", "new")}">' in html
    assert "Add acceptance criterion</a>" in html
    for item in (first, second):
        assert (
            '<a class="action secondary" '
            f'href="{url(draft.pk, "criteria", "edit", item.pk)}">' in html
        )
        assert f'action="{url(draft.pk, "criteria", "delete", item.pk)}"' in html
    assert html.count("Edit criterion</a>") == 2
    assert (
        html.count(
            '<button class="destructive" type="submit">Delete criterion</button>'
        )
        == 2
    )
    assert "No acceptance criteria yet." not in html
    assert "No test cases yet." in html


# RND-2.2


@pytest.mark.ac("RND-2.2")
def test_new_case_page_has_fields_in_order_and_round_criteria(coord_client, draft):
    one = criterion(draft, "Synthetic one")
    two = criterion(draft, "Synthetic two")
    html = page(coord_client.get(url(draft.pk, "cases", "new")))
    assert "<title>New test case</title>" in html
    assert "<h1>New test case</h1>" in html
    order = [
        '<label for="id_title">Title</label>',
        '<label for="id_steps">Steps</label>',
        '<label for="id_expected_result">Expected result</label>',
        "<legend>Linked acceptance criteria</legend>",
        f'value="{one.pk}"',
        f'value="{two.pk}"',
        '<button type="submit">Add test case</button>',
    ]
    positions = [html.index(marker) for marker in order]
    assert positions == sorted(positions)
    assert '<span dir="auto">Synthetic one</span>' in html
    assert html.count('type="checkbox"') == 2
    assert f'<a href="{detail(draft.pk)}">Back to round</a>' in html


@pytest.mark.ac("RND-2.2")
def test_new_case_page_without_criteria_says_so(coord_client, draft):
    html = page(coord_client.get(url(draft.pk, "cases", "new")))
    assert "No acceptance criteria yet." in html
    assert 'type="checkbox"' not in html


@pytest.mark.ac("RND-2.2")
def test_adding_a_case_shows_it_with_its_criteria(coord_client, draft):
    one = criterion(draft, "Synthetic one")
    criterion(draft, "Synthetic unlinked")
    three = criterion(draft, "Synthetic three")
    data = case_data(three, one, title="Synthetic first case")
    redirects_to_round(coord_client.post(url(draft.pk, "cases", "new"), data), draft)
    data = case_data(one, title="Synthetic second case")
    redirects_to_round(coord_client.post(url(draft.pk, "cases", "new"), data), draft)
    first, _ = Case.objects.filter(round=draft)
    assert list(first.criteria.all()) == [one, three]
    html = page(coord_client.get(detail(draft.pk)))
    section = html.split("<h2>Test cases</h2>", 1)[1]
    first_part, second_part = section.split("<h3>", 2)[1:]
    assert first_part.startswith('<span dir="auto">Synthetic first case</span></h3>')
    labels = ["<h4>Steps</h4>", "<h4>Expected result</h4>"]
    labels.append("<h4>Linked acceptance criteria</h4>")
    positions = [first_part.index(label) for label in labels]
    assert positions == sorted(positions)
    assert '<span dir="auto">Synthetic steps</span>' in first_part
    assert '<span dir="auto">Synthetic result</span>' in first_part
    linked = first_part.split("<h4>Linked acceptance criteria</h4>", 1)[1]
    assert linked.index("Synthetic one") < linked.index("Synthetic three")
    assert "Synthetic unlinked" not in first_part
    assert second_part.startswith('<span dir="auto">Synthetic second case</span>')
    assert (
        '<a class="action secondary" '
        f'href="{url(draft.pk, "cases", "edit", first.pk)}">' in first_part
    )
    assert "Edit test case</a>" in first_part
    assert f'action="{url(draft.pk, "cases", "delete", first.pk)}"' in first_part
    assert (
        '<button class="destructive" type="submit">Delete test case</button>'
        in first_part
    )
    assert "No test cases yet." not in html


# RND-2.3


@pytest.mark.ac("RND-2.3")
def test_editing_a_criterion_changes_its_text(coord_client, draft):
    item = criterion(draft, "Synthetic before")
    edit_url = url(draft.pk, "criteria", "edit", item.pk)
    html = page(coord_client.get(edit_url))
    assert "<title>Edit acceptance criterion</title>" in html
    assert "Synthetic before</textarea>" in html
    assert '<button type="submit">Save</button>' in html
    assert f'<a href="{detail(draft.pk)}">Back to round</a>' in html
    redirects_to_round(coord_client.post(edit_url, {"text": "Synthetic after"}), draft)
    item.refresh_from_db()
    assert item.text == "Synthetic after"
    assert "Synthetic after" in page(coord_client.get(detail(draft.pk)))


@pytest.mark.ac("RND-2.3")
def test_editing_a_case_changes_its_fields_and_links(coord_client, draft):
    one, two, three = (criterion(draft, f"Synthetic {n}") for n in "abc")
    made = case(draft, [one, two], title="Synthetic before")
    edit_url = url(draft.pk, "cases", "edit", made.pk)
    html = page(coord_client.get(edit_url))
    assert "<title>Edit test case</title>" in html
    assert 'value="Synthetic before"' in html
    assert "Synthetic steps</textarea>" in html
    assert "Synthetic result</textarea>" in html
    for item, checked in ((one, True), (two, True), (three, False)):
        tag = html.split(f'value="{item.pk}"', 1)[1].split(">", 1)[0]
        assert ("checked" in tag) is checked
    assert '<button type="submit">Save</button>' in html
    data = case_data(
        three, two, title="Synthetic after", steps="New steps", expected_result="New"
    )
    redirects_to_round(coord_client.post(edit_url, data), draft)
    made.refresh_from_db()
    assert (made.title, made.steps, made.expected_result) == (
        "Synthetic after",
        "New steps",
        "New",
    )
    assert list(made.criteria.all()) == [two, three]


@pytest.mark.ac("RND-2.3")
def test_deleting_a_case_keeps_its_criteria(coord_client, draft):
    one = criterion(draft, "Synthetic kept criterion")
    made = case(draft, [one], title="Synthetic gone")
    response = coord_client.post(url(draft.pk, "cases", "delete", made.pk))
    redirects_to_round(response, draft)
    assert not Case.objects.exists()
    assert not CaseCriterion.objects.exists()
    assert list(Criterion.objects.all()) == [one]
    html = page(coord_client.get(detail(draft.pk)))
    assert "Synthetic gone" not in html and "Synthetic kept criterion" in html


@pytest.mark.ac("RND-2.3")
def test_deleting_an_unlinked_criterion_removes_it(coord_client, draft):
    gone = criterion(draft, "Synthetic gone")
    kept = criterion(draft, "Synthetic kept")
    case(draft, [kept])
    response = coord_client.post(url(draft.pk, "criteria", "delete", gone.pk))
    redirects_to_round(response, draft)
    assert list(Criterion.objects.all()) == [kept]
    assert "Synthetic gone" not in page(coord_client.get(detail(draft.pk)))


# RND-2.4

FIELDS = [
    ("criteria", "text", 500),
    ("cases", "title", 120),
    ("cases", "steps", 2000),
    ("cases", "expected_result", 1000),
]
NEXT_MARKER = {
    "text": "<button",
    "title": 'name="steps"',
    "steps": 'name="expected_result"',
    "expected_result": "<legend>",
}


def target(draft, kind, action, linked):
    """The add route, or the edit route of a new record, for `kind`."""
    if action == "new":
        return url(draft.pk, kind, "new")
    if kind == "criteria":
        record = criterion(draft, "Synthetic old")
    else:
        record = case(draft, [linked], title="Synthetic old")
    return url(draft.pk, kind, "edit", record.pk)


def submit(client, route, kind, field, value, linked):
    """Post one field's value with the other fields valid."""
    data = (
        {"text": value} if kind == "criteria" else case_data(linked, **{field: value})
    )
    return client.post(route, data)


def field_value(record, kind, field):
    model = Criterion if kind == "criteria" else Case
    return model.objects.filter(round=record).values_list(field, flat=True)


@pytest.mark.ac("RND-2.4")
@pytest.mark.parametrize("action", ["new", "edit"])
@pytest.mark.parametrize("kind, field, limit", FIELDS)
@pytest.mark.parametrize("shape", ["plain", "padded", "crlf"])
def test_each_field_at_its_maximum_is_saved(
    coord_client, draft, action, kind, field, limit, shape
):
    linked = criterion(draft, "Synthetic link")
    value = "a" * limit
    expected = value
    if shape == "padded":
        value = "  " + value + LF + " "
    elif shape == "crlf":
        value = "a" * (limit - 2) + CR + LF + "a"
        expected = "a" * (limit - 2) + LF + "a"
    route = target(draft, kind, action, linked)
    redirects_to_round(submit(coord_client, route, kind, field, value, linked), draft)
    values = list(field_value(draft, kind, field))
    if kind == "criteria":
        values.remove("Synthetic link")
    assert values == [expected]


INVALID = {
    "empty": lambda limit: "",
    "spaces": lambda limit: "   " + LF + " ",
    "invisible": lambda limit: ZWSP + chr(0x2060) + chr(0x01),
    "over": lambda limit: "a" * (limit + 1),
}


@pytest.mark.ac("RND-2.4")
@pytest.mark.parametrize("action", ["new", "edit"])
@pytest.mark.parametrize("kind, field, limit", FIELDS)
@pytest.mark.parametrize("invalid", [*INVALID, "null"])
def test_each_invalid_field_gets_its_message_next_to_it(
    coord_client, draft, action, kind, field, limit, invalid
):
    linked = criterion(draft, "Synthetic link")
    if invalid == "null":
        value, message = "Synthetic" + chr(0), NULL_MESSAGE
    else:
        value, message = INVALID[invalid](limit), f"Enter 1 to {limit} characters."
    route = target(draft, kind, action, linked)
    before = everything()
    response = submit(coord_client, route, kind, field, value, linked)
    assert response.status_code == 200
    message_next_to(page(response), field, message, NEXT_MARKER[field])
    assert everything() == before


# RND-2.5


@pytest.mark.ac("RND-2.5")
def test_twentieth_criterion_is_added_and_twenty_first_refused(
    coord_client, draft, make_round
):
    other = make_round("Synthetic sibling")
    Criterion.objects.bulk_create(
        Criterion(round=other, text=f"Synthetic {n}") for n in range(20)
    )
    Criterion.objects.bulk_create(
        Criterion(round=draft, text=f"Synthetic {n}") for n in range(19)
    )
    new = url(draft.pk, "criteria", "new")
    redirects_to_round(coord_client.post(new, {"text": "Synthetic 20th"}), draft)
    response = coord_client.post(new, {"text": "Synthetic 21st"})
    assert response.status_code == 200
    message_next_to(page(response), "text", CRITERION_CAP, "<button")
    assert Criterion.objects.filter(round=draft).count() == 20
    assert not Criterion.objects.filter(text="Synthetic 21st").exists()


@pytest.mark.ac("RND-2.5")
def test_thirtieth_case_is_added_and_thirty_first_refused(coord_client, draft):
    linked = criterion(draft)
    for n in range(29):
        case(draft, [linked], title=f"Synthetic {n}")
    new = url(draft.pk, "cases", "new")
    data = case_data(linked, title="Synthetic 30th")
    redirects_to_round(coord_client.post(new, data), draft)
    before = stored(draft)
    response = coord_client.post(new, case_data(linked, title="Synthetic 31st"))
    assert response.status_code == 200
    message_next_to(page(response), "title", CASE_CAP, 'name="steps"')
    assert stored(draft) == before


@pytest.mark.ac("RND-2.5")
@pytest.mark.django_db(transaction=True)
def test_one_of_five_simultaneous_criteria_takes_the_last_place(coordinator):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    Criterion.objects.bulk_create(
        Criterion(round=draft, text=f"Synthetic {n}") for n in range(19)
    )
    clients = [signed_in(coordinator) for _ in range(5)]
    barrier = threading.Barrier(5)
    responses = [None] * 5
    real_add = services.add_criterion

    def slow_add(round_, text):
        # A pause before counting, inside the view's transaction, widens the
        # race window, so a missing round lock lets every request through.
        time.sleep(0.1)
        return real_add(round_, text)

    def add(index):
        try:
            barrier.wait()
            responses[index] = clients[index].post(
                url(draft.pk, "criteria", "new"), {"text": f"Synthetic racer {index}"}
            )
        finally:
            connection.close()

    threads = [threading.Thread(target=add, args=(i,)) for i in range(5)]
    with mock.patch.object(services, "add_criterion", slow_add):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 200, 200, 200, 302]
    for response in responses:
        if response.status_code == 200:
            message_next_to(page(response), "text", CRITERION_CAP, "<button")
    assert Criterion.objects.filter(round=draft).count() == 20


# RND-2.6


@pytest.mark.ac("RND-2.6")
@pytest.mark.parametrize("action", ["new", "edit"])
def test_a_case_without_criteria_is_refused(coord_client, draft, action):
    linked = criterion(draft)
    made = case(draft, [linked], title="Synthetic old")
    record_id = made.pk if action == "edit" else None
    before = stored(draft)
    data = case_data(title="Synthetic changed")
    response = coord_client.post(url(draft.pk, "cases", action, record_id), data)
    assert response.status_code == 200
    message_next_to(page(response), "criteria", NO_LINK, "<button")
    assert stored(draft) == before


@pytest.mark.ac("RND-2.6")
def test_deleting_a_linked_criterion_is_refused_on_the_round_page(coord_client, draft):
    linked = criterion(draft, "Synthetic linked")
    criterion(draft, "Synthetic other")
    case(draft, [linked])
    before = stored(draft)
    response = coord_client.post(url(draft.pk, "criteria", "delete", linked.pk))
    assert response.status_code == 200
    html = page(response)
    assert "<p>State: Draft</p>" in html
    assert html.count(LINKED) == 1
    message = html.index(LINKED)
    assert html.index("Synthetic linked") < message < html.index("Synthetic other")
    assert stored(draft) == before
    no_store(response)


# RND-2.7


@pytest.mark.ac("RND-2.7")
@pytest.mark.parametrize("action", ["new", "edit"])
@pytest.mark.parametrize(
    "source", ["sibling", "other_workspace", "missing", "oversized", "text"]
)
def test_criteria_from_elsewhere_are_refused(
    coord_client, draft, make_round, other_workspace, action, source
):
    own = criterion(draft, "Synthetic own")
    made = case(draft, [own], title="Synthetic old")
    if source == "sibling":
        wrong = criterion(make_round("Synthetic sibling")).pk
    elif source == "other_workspace":
        wrong = criterion(make_round("Synthetic foreign", owner=other_workspace)).pk
    elif source == "missing":
        wrong = own.pk + 1000
    elif source == "oversized":
        wrong = "99999999999999999999"
    else:
        wrong = "abc"
    record_id = made.pk if action == "edit" else None
    before = everything()
    data = case_data(own, title="Synthetic changed")
    data["criteria"].append(wrong)
    response = coord_client.post(url(draft.pk, "cases", action, record_id), data)
    assert response.status_code == 200
    message_next_to(page(response), "criteria", FOREIGN, "<button")
    assert everything() == before


@pytest.mark.ac("RND-2.7")
def test_a_criterion_deleted_after_validation_is_refused_by_the_locked_check(
    coord_client, draft
):
    own = criterion(draft, "Synthetic own")
    doomed = criterion(draft, "Synthetic doomed")
    real_is_valid = CaseForm.is_valid

    def validate_then_delete(form):
        valid = real_is_valid(form)
        Criterion.objects.filter(pk=doomed.pk).delete()
        return valid

    with mock.patch.object(CaseForm, "is_valid", validate_then_delete):
        response = coord_client.post(
            url(draft.pk, "cases", "new"), case_data(own, doomed)
        )
    assert response.status_code == 200
    message_next_to(page(response), "criteria", FOREIGN, "<button")
    assert not Case.objects.exists()


# RND-2.8: the rules for every round action


def routes(round_id, criterion_id, case_id):
    """Every RND-2 route as (url, accepted methods)."""
    return [
        (url(round_id, "criteria", "new"), ("get", "post")),
        (url(round_id, "criteria", "edit", criterion_id), ("get", "post")),
        (url(round_id, "criteria", "delete", criterion_id), ("post",)),
        (url(round_id, "cases", "new"), ("get", "post")),
        (url(round_id, "cases", "edit", case_id), ("get", "post")),
        (url(round_id, "cases", "delete", case_id), ("post",)),
    ]


def records(round_):
    """A criterion linked to a case, and an unlinked criterion, in `round_`."""
    linked = criterion(round_, "Synthetic linked")
    free = criterion(round_, "Synthetic free")
    return linked, free, case(round_, [linked])


def valid_post(route, linked):
    """Data that would change something on the route if it were allowed."""
    if "/criteria/" in route:
        return {"text": "Synthetic changed"}
    return case_data(linked, title="Synthetic changed")


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("signed", [True, False])
def test_unaccepted_methods_get_405_uncached(coordinator, draft, signed):
    _, free, made = records(draft)
    client = signed_in(coordinator) if signed else Client()
    for route, methods in routes(draft.pk, free.pk, made.pk):
        refused = ["put", "head"] + ([] if "get" in methods else ["get"])
        for method in refused:
            response = getattr(client, method)(route)
            assert response.status_code == 405, (route, method)
            no_store(response)
    assert Criterion.objects.count() == 2 and Case.objects.count() == 1


@pytest.mark.ac("RND-2.8")
def test_signed_out_visitor_is_redirected_to_sign_in(coordinator, draft):
    linked, free, made = records(draft)
    client = Client(enforce_csrf_checks=True)
    token = csrf_token(client)
    before = everything()
    for route, methods in routes(draft.pk, free.pk, made.pk):
        for method in methods:
            data = {**valid_post(route, linked), "csrfmiddlewaretoken": token}
            response = (
                client.get(route) if method == "get" else client.post(route, data)
            )
            assert response.status_code == 302, (route, method)
            assert response["Location"] == "/sign-in/"
    assert everything() == before


@pytest.mark.ac("RND-2.8")
def test_tester_gets_the_same_403_for_existing_and_missing_records(tester, draft):
    linked, free, made = records(draft)
    client = signed_in(tester)
    before = everything()
    existing = routes(draft.pk, free.pk, made.pk)
    missing = routes(draft.pk + 1000, free.pk + 1000, made.pk + 1000)
    with mock.patch("rounds.views.get_object_or_404") as lookup:
        for (route, methods), (gone, _) in zip(existing, missing, strict=True):
            for method in methods:
                call = getattr(client, method)
                data = valid_post(route, linked) if method == "post" else None
                first, second = call(route, data), call(gone, data)
                assert first.status_code == second.status_code == 403
                assert first.content == second.content
                assert DENIED in page(first)
    lookup.assert_not_called()
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize(
    "token, origin",
    [("missing", None), ("invalid", None), ("valid", "https://attacker.example")],
)
def test_post_without_valid_csrf_or_same_origin_gets_403(
    coordinator, draft, token, origin
):
    linked, free, made = records(draft)
    client = signed_in(coordinator, enforce_csrf_checks=True)
    valid = csrf_token(client)
    before = everything()
    extra = {"HTTP_ORIGIN": origin} if origin else {}
    for route, _ in routes(draft.pk, free.pk, made.pk):
        data = valid_post(route, linked)
        if token != "missing":
            data["csrfmiddlewaretoken"] = valid if token == "valid" else "x" * 32
        response = client.post(route, data, **extra)
        assert response.status_code == 403, route
        assert DENIED in page(response)
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_another_workspaces_records_get_404_not_409(
    coord_client, make_round, other_workspace, state
):
    foreign = make_round("Synthetic foreign", state, owner=other_workspace)
    linked, free, made = records(foreign)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    for route, methods in routes(foreign.pk, free.pk, made.pk):
        for method in methods:
            data = valid_post(route, linked) if method == "post" else None
            response = getattr(coord_client, method)(route, data)
            assert response.status_code == 404, (route, method)
            assert response.content == reference.content
            assert NOT_FOUND in page(response)
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("state", ["draft", "open", "closed"])
def test_records_of_another_round_or_missing_get_404_not_409(
    coord_client, draft, make_round, state
):
    # Records of a round in the same workspace, named under the Draft round's URL.
    elsewhere = make_round("Synthetic elsewhere", state)
    linked, free, made = records(elsewhere)
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    missing_id = made.pk + free.pk + 1000
    named = [
        url(draft.pk, kind, action, record_id)
        for action in ("edit", "delete")
        for kind, record_id in (
            ("criteria", linked.pk),
            ("criteria", free.pk),
            ("cases", made.pk),
            ("criteria", missing_id),
            ("cases", missing_id),
        )
    ]
    for route in named:
        methods = ("post",) if route.endswith("delete/") else ("get", "post")
        for method in methods:
            data = valid_post(route, linked) if method == "post" else None
            response = getattr(coord_client, method)(route, data)
            assert response.status_code == 404, (route, method)
            assert response.content == reference.content
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("state, name", [("open", "Open"), ("closed", "Closed")])
def test_any_change_to_an_open_or_closed_round_gets_409(
    coord_client, make_round, state, name
):
    frozen = make_round("Synthetic frozen", state)
    linked, free, made = records(frozen)
    before = everything()
    for route, methods in routes(frozen.pk, free.pk, made.pk):
        attempts = [("get", None)] if "get" in methods else []
        attempts += [("post", valid_post(route, linked)), ("post", {})]
        for method, data in attempts:
            response = getattr(coord_client, method)(route, data)
            assert response.status_code == 409, (route, method)
            html = page(response)
            assert "<title>Action not available</title>" in html
            assert f"<h1>{CONFLICT.format(name)}</h1>" in html
            no_store(response)
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("state, name", [("open", "Open"), ("closed", "Closed")])
def test_open_or_closed_round_page_lists_records_without_controls(
    coord_client, make_round, state, name
):
    frozen = make_round("Synthetic frozen", state)
    records(frozen)
    html = page(coord_client.get(detail(frozen.pk)))
    assert f"<p>State: {name}</p>" in html
    assert "Synthetic linked" in html and "Synthetic case" in html
    for control in (
        "Add acceptance criterion",
        "Add test case",
        "Edit criterion",
        "Delete criterion",
        "Edit test case",
        "Delete test case",
        # RND-6 adds the Open round's "Close round" form; no RND-2 form remains.
        '/delete/"',
    ):
        assert control not in html


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("kind", ["criteria", "cases"])
def test_round_opened_after_the_state_check_gets_409_from_the_locked_recheck(
    coord_client, draft, kind
):
    linked = criterion(draft)
    form_class = CriterionForm if kind == "criteria" else CaseForm
    real_is_valid = form_class.is_valid

    def open_then_validate(form):
        Round.objects.filter(pk=draft.pk).update(state=Round.State.OPEN)
        return real_is_valid(form)

    before = stored(draft)
    route = url(draft.pk, kind, "new")
    with mock.patch.object(form_class, "is_valid", open_then_validate):
        response = coord_client.post(route, valid_post(route, linked))
    assert response.status_code == 409
    assert CONFLICT.format("Open") in page(response)
    assert stored(draft) == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize(
    "service, route_kind, action",
    [
        ("add_criterion", "criteria", "new"),
        ("add_case", "cases", "new"),
        ("save_case", "cases", "edit"),
        ("delete_case", "cases", "delete"),
        ("delete_criterion", "criteria", "delete"),
    ],
)
def test_storage_failure_gives_503_and_changes_nothing(
    coord_client, draft, service, route_kind, action, caplog
):
    linked, free, made = records(draft)
    if action == "new":
        record_id = None
    else:
        record_id = made.pk if route_kind == "cases" else free.pk
    route = url(draft.pk, route_kind, action, record_id)
    before = everything()
    with mock.patch.object(services, service, side_effect=DatabaseError("synthetic")):
        response = coord_client.post(route, valid_post(route, linked))
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    no_store(response)
    assert everything() == before
    logged = [record for record in caplog.records if record.name == "rounds.views"]
    assert len(logged) == 1 and logged[0].exc_info[0] is DatabaseError


@pytest.mark.ac("RND-2.8")
def test_storage_failure_editing_a_criterion_gives_503(coord_client, draft):
    item = criterion(draft, "Synthetic stored")
    with mock.patch.object(Criterion, "save", side_effect=DatabaseError("synthetic")):
        response = coord_client.post(
            url(draft.pk, "criteria", "edit", item.pk), {"text": "Synthetic changed"}
        )
    assert response.status_code == 503
    item.refresh_from_db()
    assert item.text == "Synthetic stored"


# Review round 0: choices, 404 before 409, mid-write failures, races, injection


@pytest.mark.ac("RND-2.7")
def test_case_forms_offer_only_the_url_rounds_criteria(
    coord_client, draft, make_round, other_workspace
):
    own = [criterion(draft, f"Synthetic own {n}") for n in range(2)]
    criterion(make_round("Synthetic sibling"), "Synthetic sibling criterion")
    foreign = make_round("Synthetic foreign", owner=other_workspace)
    criterion(foreign, "Synthetic foreign criterion")
    made = case(draft, own[:1])
    pages = [
        coord_client.get(url(draft.pk, "cases", "new")),
        coord_client.get(url(draft.pk, "cases", "edit", made.pk)),
        coord_client.post(url(draft.pk, "cases", "new"), case_data(own[0], title="")),
        coord_client.post(
            url(draft.pk, "cases", "edit", made.pk), case_data(own[1], title="")
        ),
    ]
    for response in pages:
        assert response.status_code == 200
        html = page(response)
        assert html.count('type="checkbox"') == 2
        for item in own:
            assert f'value="{item.pk}"' in html
            assert item.text in html
        assert "Synthetic sibling criterion" not in html
        assert "Synthetic foreign criterion" not in html


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("state", ["open", "closed"])
def test_open_or_closed_round_url_with_a_foreign_or_missing_record_gets_404(
    coord_client, make_round, state
):
    frozen = make_round("Synthetic frozen", state)
    records(frozen)
    linked, free, made = records(make_round("Synthetic elsewhere"))
    reference = coord_client.get("/coordinator/rounds/999999/")
    before = everything()
    missing = made.pk + free.pk + 1000
    for kind, record_id in (
        ("criteria", free.pk),
        ("cases", made.pk),
        ("criteria", missing),
        ("cases", missing),
    ):
        attempts = [
            ("get", url(frozen.pk, kind, "edit", record_id)),
            ("post", url(frozen.pk, kind, "edit", record_id)),
            ("post", url(frozen.pk, kind, "delete", record_id)),
        ]
        for method, route in attempts:
            data = valid_post(route, linked) if method == "post" else None
            response = getattr(coord_client, method)(route, data)
            assert response.status_code == 404, (method, route)
            assert response.content == reference.content
    assert everything() == before


@pytest.mark.ac("RND-2.8")
@pytest.mark.parametrize("action", ["new", "edit"])
def test_link_failure_mid_write_gives_503_and_changes_nothing(
    coord_client, draft, action
):
    _, free, made = records(draft)
    record_id = made.pk if action == "edit" else None
    route = url(draft.pk, "cases", action, record_id)
    before = everything()
    with mock.patch.object(
        CaseCriterion.objects, "bulk_create", side_effect=DatabaseError("synthetic")
    ):
        response = coord_client.post(route, case_data(free, title="Synthetic new"))
    assert response.status_code == 503
    assert UNAVAILABLE in page(response)
    assert everything() == before


@pytest.mark.ac("RND-2.8")
def test_case_delete_failure_after_unlinking_gives_503_and_keeps_links(
    coord_client, draft
):
    _, _, made = records(draft)
    before = everything()
    with mock.patch.object(Case, "delete", side_effect=DatabaseError("synthetic")):
        response = coord_client.post(url(draft.pk, "cases", "delete", made.pk))
    assert response.status_code == 503
    assert everything() == before


@pytest.mark.ac("RND-2.5")
@pytest.mark.django_db(transaction=True)
def test_one_of_five_simultaneous_cases_takes_the_last_place(coordinator):
    draft = Round.objects.create(workspace=coordinator.workspace, title="Synthetic")
    linked = criterion(draft)
    for n in range(29):
        case(draft, [linked], title=f"Synthetic {n}")
    clients = [signed_in(coordinator) for _ in range(5)]
    barrier = threading.Barrier(5)
    responses = [None] * 5
    real_add = services.add_case

    def slow_add(round_, fields, criterion_ids):
        # Pause before counting, inside the locked transaction (as for criteria).
        time.sleep(0.1)
        return real_add(round_, fields, criterion_ids)

    def add(index):
        try:
            barrier.wait()
            data = case_data(linked, title=f"Synthetic racer {index}")
            responses[index] = clients[index].post(url(draft.pk, "cases", "new"), data)
        finally:
            connection.close()

    threads = [threading.Thread(target=add, args=(i,)) for i in range(5)]
    with mock.patch.object(services, "add_case", slow_add):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 200, 200, 200, 302]
    for response in responses:
        if response.status_code == 200:
            message_next_to(page(response), "title", CASE_CAP, 'name="steps"')
    assert Case.objects.filter(round=draft).count() == 30


@pytest.mark.ac("RND-2.8")
def test_injected_fields_are_ignored(coord_client, draft, make_round):
    sibling = make_round("Synthetic sibling")
    other_linked, _, other_case = records(sibling)
    _, free, made = records(draft)
    injected = {
        "round": sibling.pk,
        "round_id": sibling.pk,
        "id": other_case.pk,
        "case": other_case.pk,
        "criterion": other_linked.pk,
    }
    sibling_before = stored(sibling)
    new = url(draft.pk, "criteria", "new")
    redirects_to_round(
        coord_client.post(new, {"text": "Synthetic new", **injected}), draft
    )
    added = Criterion.objects.get(text="Synthetic new")
    assert added.round == draft and added.pk not in (other_linked.pk, other_case.pk)
    data = {**case_data(free, title="Synthetic edited"), **injected}
    redirects_to_round(
        coord_client.post(url(draft.pk, "cases", "edit", made.pk), data), draft
    )
    made.refresh_from_db()
    assert made.round == draft and made.title == "Synthetic edited"
    assert list(made.criteria.all()) == [free]
    assert stored(sibling) == sibling_before


def forged_links(make_round, other_workspace):
    """An Open round, plus link rows to another round's and workspace's records.

    The link tables do not tie a linked criterion or covered case to the
    round, so these rows can exist only if stored outside the services.
    """

    def published(title, owner=None):
        round_ = make_round(title, owner=owner)
        criterion = Criterion.objects.create(round=round_, text=f"{title} criterion")
        case = Case.objects.create(
            round=round_,
            title=f"{title} case",
            steps="Synthetic",
            expected_result="Synthetic",
        )
        CaseCriterion.objects.create(case=case, criterion=criterion)
        with transaction.atomic():
            locked = Round.objects.select_for_update().get(pk=round_.pk)
            build = services.publish(locked, f"{title} build")
        return round_, criterion, case, build

    own = published("Synthetic own")
    sibling = published("Synthetic sibling-mark")
    foreign = published("Synthetic foreign-mark", other_workspace)
    for _, criterion, case, build in (sibling, foreign):
        CaseCriterion.objects.create(case=own[2], criterion=criterion)
        BuildCase.objects.create(build=own[3], case=case)
        # A newer build of another round covering the own case.
        BuildCase.objects.create(build=build, case=own[2])
    return own


@pytest.mark.ac("RND-2.8", "RND-3.6")
@pytest.mark.parametrize("state", ["open", "closed"])
def test_round_page_shows_only_its_own_rounds_linked_records(
    coord_client, make_round, other_workspace, state
):
    round_ = forged_links(make_round, other_workspace)[0]
    Round.objects.filter(pk=round_.pk).update(state=state)
    html = page(coord_client.get(detail(round_.pk)))
    assert "-mark" not in html
    own_case = html.index('<h3><span dir="auto">Synthetic own case</span></h3>')
    linked = html.index("<h4>Linked acceptance criteria</h4>", own_case)
    current = html.index("<span>Current build</span>", own_case)
    section = html[linked : html.index("<h2>Builds</h2>")]
    assert '<li><span dir="auto">Synthetic own criterion</span></li></ul>' in section
    assert html.index('<span dir="auto">Synthetic own build</span>', current) < (
        html.index("<h2>Builds</h2>")
    )
    builds = html[html.index("<h2>Builds</h2>") :]
    assert '<ul><li><span dir="auto">Synthetic own case</span></li></ul>' in builds
