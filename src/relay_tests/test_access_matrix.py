"""The authorization matrix: every route, caller, method, forged ID and state.

SECURITY-SPEC (access to another role's operations, workspace's records or
tester's draft) asks for one shared matrix. Expectations come from the specs:
the rules for every round action in their order (rounds.md), the accounts
criteria, PLT-1.1 and 1.2, and the TECHNICAL-SPEC routes tables. Every route of
the root URLconf needs an entry here; the RES and AI slices add their rows.

Callers are an anonymous visitor, workspace A's Test Coordinator and Beta
Tester, and workspace B's Test Coordinator. Workspace A's text all contains
A_MARK, so a page that leaks A's data to B or a visitor is caught.
"""

import re
from dataclasses import dataclass, field

import pytest
from django.conf import settings
from django.db import transaction
from django.test import Client
from django.urls import URLResolver, get_resolver, reverse

from accounts.models import User, Workspace
from rounds import services
from rounds.models import Build, BuildCase, Case, CaseCriterion, Criterion, Round
from rounds.tests.conftest import DENIED, NOT_FOUND, PASSWORD, csrf_token, signed_in

pytestmark = pytest.mark.django_db

A_MARK, B_MARK = "MTXA", "MTXB"
ANON, COORD_A, TESTER_A, COORD_B = "anonymous", "coord_a", "tester_a", "coord_b"
CALLERS = (ANON, COORD_A, TESTER_A, COORD_B)
DRAFT, OPEN, CLOSED = Round.State.DRAFT, Round.State.OPEN, Round.State.CLOSED
STATES = (DRAFT, OPEN, CLOSED)
MISSING = 2_000_000_001
HUGE = "99999999999999999999"
MALFORMED = "abc"
SENTINEL = 424242
FOREIGN_ORIGIN = "https://evil.example"
UNRESOLVED = "/matrix-no-such-page/"
FAILED = "Username or password is incorrect."
CSRF_COOKIE = settings.CSRF_COOKIE_NAME

# Outcomes, each checked by `check` below.
OK = "200 page"
SIGN_IN = "302 to /sign-in/"
OWN_HOME = "302 to own role home"
DONE = "302 to the round page after a change"
DEMO = "200 Your demo workspace"
SIGN_IN_FAILED = "200 sign-in failure"
FORBIDDEN = "403 page"
NOT_FOUND_PAGE = "404 page"
NOT_ALLOWED = "405"
CONFLICT = "409 page"
CHANGES = {DONE, DEMO}

# Request kinds, sent in this order so the one that may change data comes last.
GET, HEAD, PUT, NO_TOKEN, BAD_ORIGIN, POST = (
    "GET",
    "HEAD",
    "PUT with token",
    "POST without token",
    "POST from foreign Origin",
    "POST with token",
)
KINDS = (GET, HEAD, PUT, NO_TOKEN, BAD_ORIGIN, POST)
UNSAFE_WITHOUT_VALID_TOKEN = {NO_TOKEN, BAD_ORIGIN}


# ---------------------------------------------------------------- the world


@dataclass
class Seeded:
    """A round with a linked criterion, a spare unlinked one and a case."""

    round: Round
    linked: Criterion
    spare: Criterion
    case: Case

    def record(self, slot):
        """The record a URL slot names: the spare criterion, so it deletes."""
        return self.spare if slot == "criterion_id" else self.case


@dataclass
class World:
    """Workspaces A and B, their callers, A's target and sibling, B's round."""

    users: dict
    target: Seeded
    sibling: Seeded
    foreign: Seeded
    clients: dict = field(default_factory=dict)


def seed(workspace, title, mark):
    """A Draft round of `workspace` with its records, all text holding `mark`."""
    round_ = Round.objects.create(workspace=workspace, title=f"{title} {mark}")
    linked = Criterion.objects.create(round=round_, text=f"Linked {mark}")
    spare = Criterion.objects.create(round=round_, text=f"Spare {mark}")
    case = Case.objects.create(
        round=round_,
        title=f"Case {mark}",
        steps=f"Steps {mark}",
        expected_result=f"Result {mark}",
    )
    CaseCriterion.objects.create(case=case, criterion=linked)
    return Seeded(round_, linked, spare, case)


def move_to(seeded, state):
    """Publish, and for Closed also close, the round through its services."""
    if state == DRAFT:
        return
    with transaction.atomic():
        locked = Round.objects.select_for_update().get(pk=seeded.round.pk)
        services.publish(locked, "Synthetic 1.0")
        if state == CLOSED:
            services.close(locked)
    seeded.round.refresh_from_db()


def build_world(state):
    """The matrix's records, with A's target round in `state`."""
    a = Workspace.objects.create(name=f"Demo workspace {A_MARK.lower()}0001")
    b = Workspace.objects.create(name=f"Demo workspace {B_MARK.lower()}0002")
    users = {
        COORD_A: User.objects.create_user(
            f"coord-{A_MARK.lower()}", PASSWORD, workspace=a, role="coordinator"
        ),
        TESTER_A: User.objects.create_user(
            f"tester-{A_MARK.lower()}", PASSWORD, workspace=a, role="tester"
        ),
        COORD_B: User.objects.create_user(
            f"coord-{B_MARK.lower()}", PASSWORD, workspace=b, role="coordinator"
        ),
    }
    world = World(
        users,
        seed(a, "Target round", A_MARK),
        seed(a, "Sibling round", A_MARK),
        seed(b, "Foreign round", B_MARK),
    )
    move_to(world.target, state)
    for caller in CALLERS:
        user = users.get(caller)
        world.clients[caller] = (
            signed_in(user, enforce_csrf_checks=True)
            if user
            else Client(enforce_csrf_checks=True)
        )
    return world


def snapshot():
    """Every workspace, account, round, record, link and build row."""
    models = (Workspace, User, Round, Criterion, Case, CaseCriterion, Build)
    rows = {
        model.__name__: list(model.objects.order_by("pk").values()) for model in models
    }
    rows["BuildCase"] = list(BuildCase.objects.order_by("pk").values())
    return rows


# ----------------------------------------------------------------- requests


def send(client, kind, url, data=None):
    """Send one request kind; unsafe kinds carry a valid token unless named."""
    if CSRF_COOKIE in client.cookies:
        token = client.cookies[CSRF_COOKIE].value
    else:
        token = csrf_token(client)
    if kind == GET:
        return client.get(url)
    if kind == HEAD:
        return client.head(url)
    if kind == PUT:
        return client.put(url, HTTP_X_CSRFTOKEN=token)
    if kind == NO_TOKEN:
        return client.post(url, data or {})
    if kind == BAD_ORIGIN:
        return client.post(
            url, data or {}, HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=FOREIGN_ORIGIN
        )
    return client.post(url, data or {}, HTTP_X_CSRFTOKEN=token)


def check(world, caller, response, outcome, *, state=None, before=None, where=""):
    """Assert one response matches `outcome`, leaks nothing, changes nothing."""
    body = response.content.decode()
    status = response.status_code
    if outcome == OK:
        assert status == 200, where
    elif outcome == SIGN_IN:
        assert (status, response["Location"]) == (302, "/sign-in/"), where
    elif outcome == OWN_HOME:
        home = (
            "/coordinator/" if world.users[caller].role == "coordinator" else "/tester/"
        )
        assert (status, response["Location"]) == (302, home), where
    elif outcome == DONE:
        assert status == 302, where
        assert re.fullmatch(r"/coordinator/rounds/\d+/", response["Location"]), where
    elif outcome == DEMO:
        assert status == 200 and "Your demo workspace" in body, where
    elif outcome == SIGN_IN_FAILED:
        assert status == 200 and FAILED in body, where
    elif outcome == FORBIDDEN:
        assert status == 403 and DENIED in body, where
    elif outcome == NOT_FOUND_PAGE:
        reference = world.clients[caller].get(UNRESOLVED)
        assert status == 404 and NOT_FOUND in body, where
        assert response.content == reference.content, where
    elif outcome == NOT_ALLOWED:
        assert status == 405, where
    elif outcome == CONFLICT:
        label = Round.State(state).label
        assert status == 409, where
        message = f"This action is not available while the round is {label}."
        assert message in body, where
    else:
        raise AssertionError(f"unknown outcome {outcome}")
    # B's coordinator and a visitor never see A's data, and no 403 page shows
    # any workspace data (ACC-1.4, ACC-2.4).
    if caller in (ANON, COORD_B) or outcome == FORBIDDEN:
        assert A_MARK not in body, where
    if before is not None:
        if outcome in CHANGES:
            assert snapshot() != before, where
        else:
            assert snapshot() == before, where


# ------------------------------------------------------- the routes' entries


@dataclass(frozen=True)
class RoundsRoute:
    """A rounds route's listed methods, allowed states, ID slots and payload."""

    methods: frozenset
    states: frozenset
    slots: tuple
    marks: tuple
    payload: object = None

    def data(self, world):
        """A valid payload, so a wrongly allowed request would change data."""
        return self.payload(world) if self.payload else {}


def title(world):
    return {"title": f"Changed title {A_MARK}"}


def criterion(world):
    return {"text": f"Changed criterion {A_MARK}"}


def case(world):
    return {
        "title": f"Changed case {A_MARK}",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": [world.target.linked.pk],
    }


def publish(world):
    return {"label": "Synthetic 1.5"}


def retest(world):
    return {"cases": [world.target.case.pk], "label": "Synthetic 2.0"}


BOTH, POST_ONLY, GET_ONLY = (
    frozenset({"GET", "POST"}),
    frozenset({"POST"}),
    frozenset({"GET"}),
)
ANY_STATE, DRAFT_ONLY, OPEN_ONLY = (
    frozenset(STATES),
    frozenset({DRAFT}),
    frozenset({OPEN}),
)
R, RC, RK = ("round_id",), ("round_id", "criterion_id"), ("round_id", "case_id")
RND1, RND2 = ("RND-1.6", "RND-1.7"), ("RND-2.8",)

# The TECHNICAL-SPEC rounds routes table: methods and the states each allows.
ROUNDS = {
    "rounds:new": RoundsRoute(BOTH, ANY_STATE, (), RND1, title),
    "rounds:detail": RoundsRoute(GET_ONLY, ANY_STATE, R, RND1),
    "rounds:edit": RoundsRoute(BOTH, DRAFT_ONLY, R, RND1, title),
    "rounds:criterion-new": RoundsRoute(BOTH, DRAFT_ONLY, R, RND2, criterion),
    "rounds:criterion-edit": RoundsRoute(BOTH, DRAFT_ONLY, RC, RND2, criterion),
    "rounds:criterion-delete": RoundsRoute(POST_ONLY, DRAFT_ONLY, RC, RND2),
    "rounds:case-new": RoundsRoute(BOTH, DRAFT_ONLY, R, RND2, case),
    "rounds:case-edit": RoundsRoute(BOTH, DRAFT_ONLY, RK, RND2, case),
    "rounds:case-delete": RoundsRoute(POST_ONLY, DRAFT_ONLY, RK, RND2),
    "rounds:publish": RoundsRoute(POST_ONLY, DRAFT_ONLY, R, ("RND-3.6",), publish),
    "rounds:retest": RoundsRoute(BOTH, OPEN_ONLY, R, ("RND-5.8",), retest),
    "rounds:close": RoundsRoute(POST_ONLY, OPEN_ONLY, R, ("RND-6.3", "RND-6.5")),
}


def rounds_outcome(route, caller, kind, state, *, names_a_record=True):
    """A rounds request's outcome, by the rules for every round action in order.

    `names_a_record` is False when the URL's IDs do not resolve to the
    caller's own records: missing, another workspace's or another round's.
    """
    method = kind.split()[0]
    if kind in UNSAFE_WITHOUT_VALID_TOKEN:
        return FORBIDDEN
    if method not in route.methods:
        return NOT_ALLOWED
    if caller == ANON:
        return SIGN_IN
    if caller == TESTER_A:
        return FORBIDDEN
    if route.slots and (caller == COORD_B or not names_a_record):
        return NOT_FOUND_PAGE
    if state not in route.states:
        return CONFLICT
    return OK if method == "GET" else DONE


def everyone(outcome):
    return dict.fromkeys(CALLERS, outcome)


def by_caller(anonymous, coord_a, tester_a, coord_b):
    return {ANON: anonymous, COORD_A: coord_a, TESTER_A: tester_a, COORD_B: coord_b}


ROLE_HOME_REFUSALS = {
    HEAD: everyone(NOT_ALLOWED),
    PUT: everyone(NOT_ALLOWED),
    NO_TOKEN: everyone(FORBIDDEN),
    BAD_ORIGIN: everyone(FORBIDDEN),
    POST: everyone(NOT_ALLOWED),
}
POST_ONLY_REFUSALS = {
    GET: everyone(NOT_ALLOWED),
    HEAD: everyone(NOT_ALLOWED),
    PUT: everyone(NOT_ALLOWED),
    NO_TOKEN: everyone(FORBIDDEN),
    BAD_ORIGIN: everyone(FORBIDDEN),
}

# The TECHNICAL-SPEC accounts routes table, with the criteria each row checks:
# route name -> (path, criterion IDs, {request kind: {caller: outcome}}).
ACCOUNTS = {
    "home": (
        "/",
        ("PLT-1.1", "PLT-1.2", "ACC-2.6"),
        {
            GET: by_caller(OK, OWN_HOME, OWN_HOME, OWN_HOME),
            HEAD: by_caller(OK, OWN_HOME, OWN_HOME, OWN_HOME),
            # CSRF-exempt, so every other method is 405, token or not.
            PUT: everyone(NOT_ALLOWED),
            NO_TOKEN: everyone(NOT_ALLOWED),
            BAD_ORIGIN: everyone(NOT_ALLOWED),
            POST: everyone(NOT_ALLOWED),
        },
    ),
    "accounts:sign-in": (
        "/sign-in/",
        ("ACC-1.2", "ACC-1.8"),
        {
            GET: everyone(OK),
            HEAD: everyone(NOT_ALLOWED),
            PUT: everyone(NOT_ALLOWED),
            NO_TOKEN: everyone(FORBIDDEN),
            BAD_ORIGIN: everyone(FORBIDDEN),
            POST: everyone(SIGN_IN_FAILED),
        },
    ),
    "accounts:sign-out": (
        "/sign-out/",
        ("ACC-1.5", "ACC-1.8"),
        {**POST_ONLY_REFUSALS, POST: everyone(SIGN_IN)},
    ),
    "accounts:demo": (
        "/demo/",
        ("ACC-2.1", "ACC-2.6", "ACC-2.7"),
        {**POST_ONLY_REFUSALS, POST: by_caller(DEMO, OWN_HOME, OWN_HOME, OWN_HOME)},
    ),
    "accounts:coordinator": (
        "/coordinator/",
        ("ACC-1.3", "ACC-1.4", "ACC-2.4"),
        {GET: by_caller(SIGN_IN, OK, FORBIDDEN, OK), **ROLE_HOME_REFUSALS},
    ),
    "accounts:tester": (
        "/tester/",
        ("ACC-1.3", "ACC-1.4", "ACC-2.4"),
        {GET: by_caller(SIGN_IN, FORBIDDEN, OK, FORBIDDEN), **ROLE_HOME_REFUSALS},
    ),
}


# ------------------------------------------------------------------- URLs


def route_names(patterns, namespace=""):
    """Every route of `patterns`, by name, or by its pattern when unnamed."""
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            inner = (
                f"{namespace}{pattern.namespace}:" if pattern.namespace else namespace
            )
            yield from route_names(pattern.url_patterns, inner)
        else:
            yield namespace + (pattern.name or str(pattern.pattern))


def url(name, ids):
    """Reverse `name` with `ids`; a malformed ID replaces a sentinel."""
    kwargs = {
        slot: SENTINEL if value == MALFORMED else int(value)
        for slot, value in ids.items()
    }
    built = reverse(name, kwargs=kwargs)
    return built.replace(f"/{SENTINEL}/", f"/{MALFORMED}/")


def own_ids(route, seeded):
    """The IDs of `seeded`'s round and record for the route's slots."""
    return {
        slot: seeded.round.pk if slot == "round_id" else seeded.record(slot).pk
        for slot in route.slots
    }


FORGED = ("missing", "overflow", "malformed", "other workspace", "other round")


def forged_variants(route):
    """The forged variants for a route: "other round" needs a record slot."""
    if route.slots[-1] == "round_id":
        return FORGED[:-1]
    return FORGED


def forged_ids(route, world, variant):
    """A forged variant's IDs: none name the caller's own record in the round."""
    own = own_ids(route, world.target)
    last = route.slots[-1]
    if variant == "other workspace":
        if last == "round_id":
            return {last: world.foreign.round.pk}
        return {**own, last: world.foreign.record(last).pk}
    if variant == "other round":
        return {**own, last: world.sibling.record(last).pk}
    return {**own, last: {"missing": MISSING, "overflow": HUGE}.get(variant, MALFORMED)}


def marked(name, marks, *rest):
    return pytest.param(
        name, *rest, marks=pytest.mark.ac(*marks), id="-".join([name, *rest])
    )


# ------------------------------------------------------------------- tests


def test_every_route_has_a_matrix_entry():
    names = list(route_names(get_resolver().url_patterns))
    assert len(names) == len(set(names))
    assert set(names) == set(ACCOUNTS) | set(ROUNDS)


@pytest.mark.parametrize(
    ("name", "caller"),
    [
        marked(name, marks, caller)
        for name, (_, marks, _) in ACCOUNTS.items()
        for caller in CALLERS
    ],
)
def test_accounts_route_matrix(name, caller):
    world = build_world(DRAFT)
    path, _, table = ACCOUNTS[name]
    assert set(table) == set(KINDS)
    client = world.clients[caller]
    for kind in KINDS:
        before = snapshot()
        response = send(client, kind, path)
        outcome = table[kind][caller]
        check(
            world, caller, response, outcome, before=before, where=(path, caller, kind)
        )


def test_the_marker_shows_on_its_own_workspace_pages():
    # Positive control: A's data does reach A's coordinator, so the leak
    # check on B's pages and the visitor's is not vacuous.
    world = build_world(DRAFT)
    for path in ("/coordinator/", f"/coordinator/rounds/{world.target.round.pk}/"):
        response = world.clients[COORD_A].get(path)
        assert response.status_code == 200
        assert A_MARK in response.content.decode()


@pytest.mark.parametrize(
    ("name", "caller", "state"),
    [
        marked(name, route.marks, caller, state)
        for name, route in ROUNDS.items()
        for caller in CALLERS
        for state in STATES
    ],
)
def test_rounds_route_matrix(name, caller, state):
    world = build_world(state)
    route = ROUNDS[name]
    target = url(name, own_ids(route, world.target))
    for kind in KINDS:
        before = snapshot()
        response = send(world.clients[caller], kind, target, route.data(world))
        outcome = rounds_outcome(route, caller, kind, state)
        check(
            world,
            caller,
            response,
            outcome,
            state=state,
            before=before,
            where=(target, caller, kind),
        )


@pytest.mark.parametrize(
    ("name", "state", "variant"),
    [
        marked(name, (*route.marks, "ACC-2.4"), state, variant)
        for name, route in ROUNDS.items()
        if route.slots
        for state in STATES
        for variant in forged_variants(route)
    ],
)
def test_forged_ids_get_the_404_page_in_every_state(name, state, variant):
    world = build_world(state)
    route = ROUNDS[name]
    forged = url(name, forged_ids(route, world, variant))
    kinds = [kind for kind in (GET, POST) if kind.split()[0] in route.methods]
    for caller in (ANON, TESTER_A, COORD_A):
        for kind in kinds:
            before = snapshot()
            response = send(world.clients[caller], kind, forged, route.data(world))
            if variant == "malformed":
                # No pattern matches, so the resolver's 404 comes first.
                outcome = NOT_FOUND_PAGE
            else:
                outcome = rounds_outcome(
                    route, caller, kind, state, names_a_record=False
                )
            check(
                world,
                caller,
                response,
                outcome,
                state=state,
                before=before,
                where=(forged, caller, kind),
            )
