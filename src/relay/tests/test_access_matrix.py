"""The authorization matrix: every route, caller, method, forged ID and state.

SECURITY-SPEC (access to another role's operations, workspace's records or
tester's draft) asks for one shared matrix. Expectations come from the specs:
the rules for every round action in their order (rounds.md), the accounts
criteria, PLT-1.1 and 1.2, and the TECHNICAL-SPEC routes tables. Every route of
the root URLconf needs an entry here; later slices add rows for their routes.

Callers are an anonymous visitor, workspace A's Test Coordinator and Beta
Tester, and workspace B's Test Coordinator. Every name and text of workspace A,
including its usernames and workspace name, holds A_MARK; A's sibling round
holds SIBLING_MARK and workspace B holds B_MARK; another tester's private
result in workspace A holds PEER_MARK, which no other caller may see. Marks
are compared case-insensitively, so a page that leaks one workspace's data to
the other, to a visitor, or another round's data to a round's page, is caught.
Each mark has a hyphen, which no CSRF token or generated password contains, so
a random token cannot match a mark by chance.
"""

import re
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest
from django.conf import settings
from django.db import transaction
from django.test import Client
from django.urls import URLResolver, get_resolver, reverse
from django.utils import timezone

from accounts.models import User, Workspace
from ai.models import CallRecord, CallSlot
from rounds import services
from rounds.models import (
    Build,
    BuildCase,
    Case,
    CaseCriterion,
    Criterion,
    Result,
    Round,
)
from rounds.tests.conftest import DENIED, NOT_FOUND, PASSWORD, csrf_token, signed_in

pytestmark = pytest.mark.django_db

A_MARK, B_MARK, SIBLING_MARK, PEER_MARK = "mtx-a", "mtx-b", "mtx-s", "mtx-p"
ANON, COORD_A, TESTER_A, COORD_B = "anonymous", "coord_a", "tester_a", "coord_b"
CALLERS = (ANON, COORD_A, TESTER_A, COORD_B)
# The marks each caller must never see, wherever they look.
HIDDEN_FROM = {
    ANON: (A_MARK, SIBLING_MARK, B_MARK, PEER_MARK),
    COORD_A: (B_MARK, PEER_MARK),
    TESTER_A: (B_MARK, PEER_MARK),
    COORD_B: (A_MARK, SIBLING_MARK, PEER_MARK),
}
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
RENDERED = "200 page after a POST that saves nothing"
DEMO = "200 Your demo workspace"
SIGN_IN_FAILED = "200 sign-in failure"
FORBIDDEN = "403 page"
NOT_FOUND_PAGE = "404 page"
NOT_ALLOWED = "405"
CONFLICT = "409 page"
CHANGES = {DONE, DEMO}


@dataclass(frozen=True)
class Kind:
    """One kind of request: its HTTP method, CSRF token and Origin header."""

    label: str
    method: str
    token: bool = True
    origin: str = ""

    def fails_csrf(self):
        """Django refuses an unsafe method without a valid token or same origin."""
        unsafe = self.method not in ("GET", "HEAD")
        return unsafe and (not self.token or bool(self.origin))


GET = Kind("GET", "GET")
HEAD = Kind("HEAD", "HEAD")
PUT = Kind("PUT with token", "PUT")
NO_TOKEN = Kind("POST without token", "POST", token=False)
BAD_ORIGIN = Kind("POST from foreign Origin", "POST", origin=FOREIGN_ORIGIN)
POST = Kind("POST with token", "POST")
# Sent in this order, so the one request that may change data comes last.
KINDS = (GET, HEAD, PUT, NO_TOKEN, BAD_ORIGIN, POST)


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

    a: Workspace
    b: Workspace
    users: dict
    target: Seeded
    sibling: Seeded
    foreign: Seeded
    clients: dict = field(default_factory=dict)
    # The (case, build) of tester_a's one result a successful write may change.
    entry: tuple = ()


def seed(workspace, mark):
    """A Draft round of `workspace` with its records, all text holding `mark`."""
    round_ = Round.objects.create(workspace=workspace, title=f"Round {mark}")
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
    a = Workspace.objects.create(name=f"Demo workspace {A_MARK}0001")
    b = Workspace.objects.create(name=f"Demo workspace {B_MARK}0002")
    users = {
        COORD_A: User.objects.create_user(
            f"coord-{A_MARK}", PASSWORD, workspace=a, role="coordinator"
        ),
        TESTER_A: User.objects.create_user(
            f"tester-{A_MARK}", PASSWORD, workspace=a, role="tester"
        ),
        COORD_B: User.objects.create_user(
            f"coord-{B_MARK}", PASSWORD, workspace=b, role="coordinator"
        ),
    }
    world = World(a, b, users, seed(a, A_MARK), seed(a, SIBLING_MARK), seed(b, B_MARK))
    move_to(world.target, state)
    for caller in CALLERS:
        user = users.get(caller)
        world.clients[caller] = (
            signed_in(user, enforce_csrf_checks=True)
            if user
            else Client(enforce_csrf_checks=True)
        )
    return world


MODELS = (
    Workspace,
    User,
    Round,
    Criterion,
    Case,
    CaseCriterion,
    Build,
    BuildCase,
    Result,
    CallRecord,
    CallSlot,
)


def every_row():
    """Every row of the matrix's models, by model name, in primary key order."""
    return {
        model.__name__: list(model.objects.order_by("pk").values()) for model in MODELS
    }


def part(rows, rounds, workspace_id=None):
    """The rows of `rounds` (IDs), their records, links, builds and results; with
    `workspace_id`, also that workspace's row and accounts."""
    cases = {row["id"] for row in rows["Case"] if row["round_id"] in rounds}
    builds = {row["id"] for row in rows["Build"] if row["round_id"] in rounds}
    kept = {
        "Round": [row for row in rows["Round"] if row["id"] in rounds],
        "Criterion": [row for row in rows["Criterion"] if row["round_id"] in rounds],
        "Case": [row for row in rows["Case"] if row["id"] in cases],
        "CaseCriterion": [
            row for row in rows["CaseCriterion"] if row["case_id"] in cases
        ],
        "Build": [row for row in rows["Build"] if row["id"] in builds],
        "BuildCase": [row for row in rows["BuildCase"] if row["build_id"] in builds],
        "Result": [row for row in rows["Result"] if row["case_id"] in cases],
    }
    if workspace_id is not None:
        kept["Workspace"] = [r for r in rows["Workspace"] if r["id"] == workspace_id]
        kept["User"] = [r for r in rows["User"] if r["workspace_id"] == workspace_id]
    return kept


def workspace_part(rows, workspace):
    """A workspace's row, accounts and rounds' rows."""
    rounds = {r["id"] for r in rows["Round"] if r["workspace_id"] == workspace.pk}
    return part(rows, rounds, workspace.pk)


def beyond_own_result(rows, world):
    """Every row but tester_a's result for `world.entry`, the one it may write."""
    own = (world.users[TESTER_A].pk, *world.entry)
    return {
        name: [
            row
            for row in kept
            if name != "Result"
            or (row["tester_id"], row["case_id"], row["build_id"]) != own
        ]
        for name, kept in rows.items()
    }


def snapshot(world):
    """Every row, and the rows a caller's successful write must leave alone."""
    rows = every_row()
    return {
        "beyond own result": beyond_own_result(rows, world),
        "all": rows,
        "a": workspace_part(rows, world.a),
        "b": workspace_part(rows, world.b),
        "sibling": part(rows, {world.sibling.round.pk}),
        # A workspace's own row and accounts, without its rounds.
        "a accounts": part(rows, set(), world.a.pk),
        "b accounts": part(rows, set(), world.b.pk),
    }


# Each caller's successful write must leave these parts of `snapshot` unchanged.
BYSTANDERS = {
    ANON: ("a", "b"),
    COORD_A: ("b", "sibling", "a accounts"),
    TESTER_A: ("beyond own result",),
    COORD_B: ("a", "b accounts"),
}


# ----------------------------------------------------------------- requests


def send(client, kind, url, data=None):
    """Send one request of `kind`, with a valid CSRF token when it carries one."""
    extra = {}
    if kind.token:
        if CSRF_COOKIE not in client.cookies:
            csrf_token(client)
        extra["HTTP_X_CSRFTOKEN"] = client.cookies[CSRF_COOKIE].value
    if kind.origin:
        extra["HTTP_ORIGIN"] = kind.origin
    if kind.method == "GET":
        return client.get(url, **extra)
    if kind.method == "HEAD":
        return client.head(url, **extra)
    if kind.method == "PUT":
        return client.put(url, **extra)
    return client.post(url, data or {}, **extra)


def reference(client, outcome):
    """The same client's generic 403 or 404 page, for a byte comparison."""
    if outcome == FORBIDDEN:
        # A tokenless sign-out is refused by CSRF and signs no one out.
        return client.post("/sign-out/").content
    return client.get(UNRESOLVED).content


@dataclass
class Expect:
    """What one response must be, beyond its outcome."""

    outcome: str
    state: str = ""
    allow: frozenset = frozenset()
    done_at: str = ""
    scoped: bool = False
    message: str = ""
    shows: tuple = ()


def check(world, caller, response, expect, before):
    """Assert one response matches `expect`, leaks nothing, changes nothing.

    `done_at` is the exact redirect after a change, or empty for a new round,
    which must then be in the caller's workspace. `scoped` marks a page about
    the target round, which must show nothing of its sibling round. A 409's
    `message` replaces the round state's conflict text. `shows` lists texts the
    page must contain.
    """
    body = response.content.decode()
    status, outcome = response.status_code, expect.outcome
    client = world.clients[caller]
    if outcome in (OK, RENDERED):
        assert status == 200
    elif outcome == SIGN_IN:
        assert (status, response["Location"]) == (302, "/sign-in/")
    elif outcome == OWN_HOME:
        role = world.users[caller].role
        home = "/coordinator/" if role == "coordinator" else "/tester/"
        assert (status, response["Location"]) == (302, home)
    elif outcome == DONE:
        assert status == 302
        if expect.done_at:
            assert response["Location"] == expect.done_at
        else:
            made = re.fullmatch(r"/coordinator/rounds/(\d+)/", response["Location"])
            assert made
            owner = Round.objects.get(pk=int(made[1])).workspace_id
            assert owner == world.users[caller].workspace_id
    elif outcome == DEMO:
        assert status == 200 and "Your demo workspace" in body
    elif outcome == SIGN_IN_FAILED:
        assert status == 200 and FAILED in body
    elif outcome == FORBIDDEN:
        assert status == 403 and DENIED in body
        assert response.content == reference(client, FORBIDDEN)
    elif outcome == NOT_FOUND_PAGE:
        assert status == 404 and NOT_FOUND in body
        assert response.content == reference(client, NOT_FOUND_PAGE)
    elif outcome == NOT_ALLOWED:
        assert status == 405
        assert set(response["Allow"].split(", ")) == set(expect.allow)
    elif outcome == CONFLICT:
        label = Round.State(expect.state).label
        message = f"This action is not available while the round is {label}."
        assert status == 409
        assert (expect.message or message) in body
    else:
        raise AssertionError(f"unknown outcome {outcome}")
    for text in expect.shows:
        assert text in body, f"missing {text!r}"
    hidden = set(HIDDEN_FROM[caller])
    if outcome == FORBIDDEN:
        # The 403 page shows no workspace data (ACC-1.4).
        hidden |= {A_MARK, SIBLING_MARK, B_MARK}
    if expect.scoped:
        hidden.add(SIBLING_MARK)
    assert not [mark for mark in hidden if mark in body.lower()], "leaked"
    after = snapshot(world)
    if outcome in CHANGES:
        assert after["all"] != before["all"], "changed nothing"
        assert caller in BYSTANDERS, f"no bystander rows recorded for {caller}"
        for part in BYSTANDERS[caller]:
            assert after[part] == before[part], f"changed {part}"
    else:
        assert after == before, "changed data"


class Failures(list):
    """Collect each request's failure, so one does not hide the others."""

    @contextmanager
    def under(self, where):
        """Record an assertion failure inside the block under `where`."""
        try:
            yield
        except AssertionError as error:
            self.append(f"{where}: {error}")

    def assert_none(self):
        """Fail with every recorded failure."""
        assert not self, "\n\n".join(self)


def exchange(world, caller, kind, url, data, expect, failures):
    """Send one request and check it, recording any failure."""
    with failures.under((url, caller, kind.label, expect.outcome)):
        before = snapshot(world)
        response = send(world.clients[caller], kind, url, data)
        check(world, caller, response, expect, before)


# ------------------------------------------------------- the routes' entries


@dataclass(frozen=True)
class RoundsRoute:
    """A rounds route's listed methods, allowed states, ID slots and payload.

    `posted` is an allowed POST's outcome: DONE for a change, or RENDERED for a
    page that saves nothing. `shows` maps a method to texts its allowed page
    must contain.
    """

    methods: frozenset
    states: frozenset
    slots: tuple
    marks: tuple
    payload: object = None
    posted: str = DONE
    shows: dict = field(default_factory=dict)

    def data(self, world):
        """A valid payload, so a wrongly allowed request would change data."""
        return self.payload(world) if self.payload else {}


def title(world):
    return {"title": "Synthetic changed title"}


def criterion(world):
    return {"text": "Synthetic changed criterion"}


def case(world):
    return {
        "title": "Synthetic changed case",
        "steps": "Synthetic steps",
        "expected_result": "Synthetic result",
        "criteria": [world.target.linked.pk],
    }


def selection(world):
    return {"criteria": [world.target.linked.pk]}


def draft(world):
    return {
        "title": "Synthetic draft title",
        "steps": "Synthetic draft steps",
        "expected_result": "Synthetic draft result",
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
RND1, RND2, RND8 = ("RND-1.6", "RND-1.7"), ("RND-2.8",), ("RND-8.7",)
DRAFTING_DISCLOSURE = (
    "The selected criteria are sent to the SoC AI service to suggest test cases."
)
UNAVAILABLE = (
    "Drafting is unavailable right now. You can still add test cases yourself."
)

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
    # Fixed test settings disable live calls, so valid drafting is unavailable.
    "ai:draft": RoundsRoute(
        BOTH,
        DRAFT_ONLY,
        R,
        RND8,
        selection,
        RENDERED,
        {"GET": (DRAFTING_DISCLOSURE,), "POST": (DRAFTING_DISCLOSURE, UNAVAILABLE)},
    ),
    "ai:use-draft": RoundsRoute(
        POST_ONLY,
        DRAFT_ONLY,
        R,
        RND8,
        draft,
        RENDERED,
        {"POST": ("Pre-filled from an AI draft. Review it before adding it.",)},
    ),
}


def rounds_outcome(route, caller, kind, state, *, names_a_record=True):
    """A rounds request's outcome, by the rules for every round action in order.

    `names_a_record` is False when the URL's IDs do not resolve to the
    caller's own records: missing, another workspace's or another round's.
    """
    if kind.fails_csrf():
        return FORBIDDEN
    if kind.method not in route.methods:
        return NOT_ALLOWED
    if caller == ANON:
        return SIGN_IN
    if caller == TESTER_A:
        return FORBIDDEN
    if route.slots and (caller == COORD_B or not names_a_record):
        return NOT_FOUND_PAGE
    if state not in route.states:
        return CONFLICT
    return OK if kind.method == "GET" else route.posted


def rounds_expect(name, world, caller, kind, state, *, names_a_record=True):
    """The full expectation for one rounds request."""
    route = ROUNDS[name]
    outcome = rounds_outcome(route, caller, kind, state, names_a_record=names_a_record)
    done_at = f"/coordinator/rounds/{world.target.round.pk}/" if route.slots else ""
    shows = route.shows.get(kind.method, ()) if outcome in (OK, RENDERED) else ()
    return Expect(
        outcome, state, route.methods, done_at, scoped=bool(route.slots), shows=shows
    )


@dataclass(frozen=True)
class AccountsRoute:
    """An accounts route's path, listed methods, criteria and outcomes."""

    path: str
    methods: frozenset
    marks: tuple
    outcomes: dict


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

# The TECHNICAL-SPEC accounts routes table, with the criteria each row checks.
ACCOUNTS = {
    "home": AccountsRoute(
        "/",
        frozenset({"GET", "HEAD"}),
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
    "accounts:sign-in": AccountsRoute(
        "/sign-in/",
        BOTH,
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
    "accounts:sign-out": AccountsRoute(
        "/sign-out/",
        POST_ONLY,
        ("ACC-1.5", "ACC-1.8"),
        {**POST_ONLY_REFUSALS, POST: everyone(SIGN_IN)},
    ),
    "accounts:demo": AccountsRoute(
        "/demo/",
        POST_ONLY,
        ("ACC-2.1", "ACC-2.6", "ACC-2.7"),
        {**POST_ONLY_REFUSALS, POST: by_caller(DEMO, OWN_HOME, OWN_HOME, OWN_HOME)},
    ),
    "accounts:coordinator": AccountsRoute(
        "/coordinator/",
        GET_ONLY,
        ("ACC-1.3", "ACC-1.4", "ACC-2.4"),
        {GET: by_caller(SIGN_IN, OK, FORBIDDEN, OK), **ROLE_HOME_REFUSALS},
    ),
    "accounts:tester": AccountsRoute(
        "/tester/",
        GET_ONLY,
        ("ACC-1.3", "ACC-1.4", "ACC-2.4"),
        {GET: by_caller(SIGN_IN, FORBIDDEN, OK, FORBIDDEN), **ROLE_HOME_REFUSALS},
    ),
}


# The TECHNICAL-SPEC tester routes: detail and history take GET only and show
# only Open and Closed rounds of the tester's own workspace (RES-1/3).
TESTER_ROUND = "accounts:tester-round"
TESTER_MARKS = ("RES-1.4", "RES-1.5")
TESTER_READ_ONLY = {
    TESTER_ROUND: TESTER_MARKS,
    "accounts:tester-results": ("RES-3.4", "RES-3.5"),
}
PUBLISHED = frozenset({OPEN, CLOSED})


def expect_tester_round(caller, kind, state, *, names_a_round=True):
    """A tester read-only request's expectation, by the tester routes' order.

    `names_a_round` is False when the URL's ID is missing or another
    workspace's: the same 404 as a Draft round.
    """
    if kind.fails_csrf():
        outcome = FORBIDDEN
    elif kind.method != "GET":
        outcome = NOT_ALLOWED
    elif caller == ANON:
        outcome = SIGN_IN
    elif caller != TESTER_A:
        outcome = FORBIDDEN
    elif not names_a_round or state not in PUBLISHED:
        outcome = NOT_FOUND_PAGE
    else:
        outcome = OK
    return Expect(outcome, allow=GET_ONLY, scoped=True)


# The TECHNICAL-SPEC tester routes and RES-2: result entry takes GET and POST,
# and only for the tester's own row of a case's current build in an Open round.
TESTER_RESULT = "accounts:tester-result"
RESULT_MARKS = ("RES-2.3", "RES-2.4", "RES-2.6", "RES-2.7")
RESULT_SLOTS = ("round_id", "case_id", "build_id")


@dataclass(frozen=True)
class Situation:
    """tester_a's entry before the requests, and the methods it refuses with 409."""

    label: str
    refused: frozenset = frozenset()
    message: str = ""
    marks: tuple = ()


FRESH = Situation("no result")
SUBMITTED = Situation(
    "submitted",
    POST_ONLY,
    "This result has already been submitted.",
    ("RES-2.5",),
)
STALE = Situation(
    "formerly current build",
    BOTH,
    "This build is no longer current. Reload the round to record a result.",
)


def result_data(world):
    return {"outcome": "pass", "observation": "Synthetic observation", "action": "save"}


def stored_build(round_, label, cases):
    """A build written directly, as no service would: one of a Draft round."""
    build = Build.objects.create(
        round=round_, label=label, key=services.build_key(label)
    )
    for case in cases:
        BuildCase.objects.create(build=build, case=case)
    return build


@dataclass
class ResultWorld:
    """The matrix world for result entry, and the IDs its URLs use."""

    world: World
    own: dict
    uncovering: Build

    def forged(self, slot, variant):
        """IDs naming no own entry: `slot` replaced, or a foreign tuple."""
        world = self.world
        if variant in FORGED_URL_IDS:
            return {**self.own, slot: FORGED_URL_IDS[variant]}
        if slot == "round_id" and variant == "other workspace":
            # A whole tuple of B's Open round, so only the workspace refuses it.
            foreign = world.foreign
            build = foreign.round.builds.get()
            return dict(
                zip(RESULT_SLOTS, (foreign.round.pk, foreign.case.pk, build.pk))
            )
        if slot == "build_id" and variant == "not covering the case":
            return {**self.own, slot: self.uncovering.pk}
        owner = world.foreign if variant == "other workspace" else world.sibling
        record = {
            "round_id": owner.round,
            "case_id": owner.case,
            "build_id": owner.round.builds.first(),
        }[slot]
        return {**self.own, slot: record.pk}


def result_world(state, situation=FRESH):
    """A matrix world whose target has two cases, a build covering both and a
    retest build covering only the second; A's sibling and B's round are Open.

    A Draft target's builds are stored directly, so only the Draft rule can
    refuse it. The link table does not tie a covered case to its build's
    round (SECURITY-SPEC), so links are stored across rounds and workspaces,
    and only the round constraint on each lookup can refuse their IDs. A
    second tester of workspace A has a draft for the own entry.
    """
    world = build_world(DRAFT)
    target = world.target
    second = Case.objects.create(
        round=target.round,
        title=f"Second case {A_MARK}",
        steps=f"Steps {A_MARK}",
        expected_result=f"Result {A_MARK}",
    )
    move_to(world.sibling, OPEN)
    move_to(world.foreign, OPEN)
    if state == DRAFT:
        first = stored_build(target.round, "Synthetic 1.0", [target.case, second])
        uncovering = stored_build(target.round, "Synthetic 2.0", [second])
    else:
        with transaction.atomic():
            locked = Round.objects.select_for_update().get(pk=target.round.pk)
            first = services.publish(locked, "Synthetic 1.0")
            uncovering = services.request_retest(locked, "Synthetic 2.0", [second.pk])
            if situation == STALE:
                services.request_retest(locked, "Synthetic 3.0", [target.case.pk])
            if state == CLOSED:
                services.close(locked)
        target.round.refresh_from_db()
    sibling_build = world.sibling.round.builds.get()
    foreign_build = world.foreign.round.builds.get()
    for build, case in (
        (first, world.sibling.case),
        (first, world.foreign.case),
        (sibling_build, target.case),
        (foreign_build, target.case),
    ):
        BuildCase.objects.create(build=build, case=case)
    if state != DRAFT:
        peer = User.objects.create_user(
            f"peer-{A_MARK}", PASSWORD, workspace=world.a, role="tester"
        )
        Result.objects.create(
            tester=peer,
            case=target.case,
            build=first,
            outcome="fail",
            observation=f"Peer {PEER_MARK}",
        )
        world.users["peer"] = peer
    if situation == SUBMITTED:
        Result.objects.create(
            tester=world.users[TESTER_A],
            case=target.case,
            build=first,
            outcome="pass",
            observation=f"Own {A_MARK}",
            submitted_at=timezone.now(),
        )
    world.entry = (target.case.pk, first.pk)
    own = dict(zip(RESULT_SLOTS, (target.round.pk, target.case.pk, first.pk)))
    return ResultWorld(world, own, uncovering)


def expect_tester_result(
    caller, kind, state, done_at, situation=FRESH, *, names_own=True
):
    """A result entry request's expectation, by RES-2's order.

    `names_own` is False when the URL's IDs do not name a case of the tester's
    own round and a build of that round covering it: the 404 comes before
    any state, build or submission conflict.
    """
    message = ""
    if kind.fails_csrf():
        outcome = FORBIDDEN
    elif kind.method not in BOTH:
        outcome = NOT_ALLOWED
    elif caller == ANON:
        outcome = SIGN_IN
    elif caller != TESTER_A:
        outcome = FORBIDDEN
    elif not names_own or state == DRAFT:
        outcome = NOT_FOUND_PAGE
    elif state == CLOSED:
        outcome = CONFLICT
    elif kind.method in situation.refused:
        outcome, message = CONFLICT, situation.message
    else:
        outcome = OK if kind.method == "GET" else DONE
    return Expect(outcome, state, BOTH, done_at, scoped=True, message=message)


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
    """Reverse `name` with integer `ids`; a text ID replaces a sentinel."""
    texts = [value for value in ids.values() if isinstance(value, str)]
    assert len(texts) <= 1
    kwargs = {
        slot: SENTINEL if isinstance(value, str) else value
        for slot, value in ids.items()
    }
    built = reverse(name, kwargs=kwargs)
    return built.replace(f"/{SENTINEL}/", f"/{texts[0]}/") if texts else built


def own_ids(route, seeded):
    """The IDs of `seeded`'s round and record for the route's slots."""
    return {
        slot: seeded.round.pk if slot == "round_id" else seeded.record(slot).pk
        for slot in route.slots
    }


# Forged IDs, in a URL (replacing its last slot, text as-is) or a form body.
FORGED_URL_IDS = {
    "missing": MISSING,
    "overflow": HUGE,
    "zero": "0",
    "double zero": "00",
    "malformed": MALFORMED,
}
STATELESS = {"malformed"}  # No pattern matches, so the state cannot matter.


def forged_variants(route):
    """A route's forged URL variants: "other round" needs a record slot."""
    variants = [*FORGED_URL_IDS, "other workspace"]
    if route.slots[-1] != "round_id":
        variants.append("other round")
    return variants


def forged_ids(route, world, variant):
    """A forged variant's IDs: none name the caller's own record in the round."""
    own = own_ids(route, world.target)
    last = route.slots[-1]
    if variant in FORGED_URL_IDS:
        return {**own, last: FORGED_URL_IDS[variant]}
    if variant == "other workspace" and last == "round_id":
        return {last: world.foreign.round.pk}
    if variant == "other workspace":
        return {**own, last: world.foreign.record(last).pk}
    assert variant == "other round"
    return {**own, last: world.sibling.record(last).pk}


def marked(name, marks, *rest):
    return pytest.param(
        name, *rest, marks=pytest.mark.ac(*marks), id="-".join([name, *rest])
    )


def get_or_post(route):
    """The listed kinds a forged ID is sent with."""
    return [kind for kind in (GET, POST) if kind.method in route.methods]


# ------------------------------------------------------------------- tests


def test_every_route_has_a_matrix_entry():
    names = list(route_names(get_resolver().url_patterns))
    assert len(names) == len(set(names))
    expected = set(ACCOUNTS) | set(ROUNDS) | set(TESTER_READ_ONLY) | {TESTER_RESULT}
    assert set(names) == expected


@pytest.mark.parametrize(
    ("name", "caller"),
    [
        marked(name, route.marks, caller)
        for name, route in ACCOUNTS.items()
        for caller in CALLERS
    ],
)
def test_accounts_route_matrix(name, caller):
    world = build_world(DRAFT)
    route = ACCOUNTS[name]
    assert set(route.outcomes) == set(KINDS)
    failures = Failures()
    for kind in KINDS:
        expect = Expect(route.outcomes[kind][caller], allow=route.methods)
        exchange(world, caller, kind, route.path, None, expect, failures)
    failures.assert_none()


def test_each_marker_shows_on_its_own_workspace_pages():
    # Positive controls: each mark does reach its own pages, so the leak
    # checks for it are not vacuous.
    world = build_world(DRAFT)
    pages = [
        (COORD_A, "/coordinator/", (f"Round {A_MARK}", f"Round {SIBLING_MARK}")),
        (COORD_A, "/coordinator/", (f"coord-{A_MARK}", f"Demo workspace {A_MARK}")),
        (TESTER_A, "/tester/", (f"tester-{A_MARK}", f"Demo workspace {A_MARK}")),
        (COORD_B, "/coordinator/", (f"Round {B_MARK}", f"coord-{B_MARK}")),
        (COORD_A, f"/coordinator/rounds/{world.target.round.pk}/", (f"Case {A_MARK}",)),
        (
            COORD_A,
            f"/coordinator/rounds/{world.sibling.round.pk}/",
            (f"Case {SIBLING_MARK}",),
        ),
    ]
    for caller, path, texts in pages:
        response = world.clients[caller].get(path)
        assert response.status_code == 200
        for text in texts:
            assert text in response.content.decode(), (caller, path, text)


@pytest.mark.parametrize(
    ("name", "caller", "state"),
    [
        marked(name, route.marks, caller, state)
        for name, route in ROUNDS.items()
        for caller in CALLERS
        # A route naming no round has no state to vary.
        for state in (STATES if route.slots else (DRAFT,))
    ],
)
def test_rounds_route_matrix(name, caller, state):
    world = build_world(state)
    route = ROUNDS[name]
    target = url(name, own_ids(route, world.target))
    failures = Failures()
    for kind in KINDS:
        expect = rounds_expect(name, world, caller, kind, state)
        exchange(world, caller, kind, target, route.data(world), expect, failures)
    failures.assert_none()


@pytest.mark.parametrize(
    ("name", "state", "variant"),
    [
        marked(name, (*route.marks, "ACC-2.4"), state, variant)
        for name, route in ROUNDS.items()
        if route.slots
        for variant in forged_variants(route)
        for state in ((DRAFT,) if variant in STATELESS else STATES)
    ],
)
def test_forged_url_ids_get_the_404_page_in_every_state(name, state, variant):
    world = build_world(state)
    route = ROUNDS[name]
    forged = url(name, forged_ids(route, world, variant))
    failures = Failures()
    for caller in (ANON, TESTER_A, COORD_A):
        for kind in get_or_post(route):
            if variant in STATELESS:
                # The resolver's 404 comes before every other rule.
                expect = Expect(NOT_FOUND_PAGE, scoped=True)
            else:
                expect = rounds_expect(
                    name, world, caller, kind, state, names_a_record=False
                )
            exchange(world, caller, kind, forged, route.data(world), expect, failures)
    failures.assert_none()


@pytest.mark.parametrize(
    ("name", "state"),
    [
        marked(name, (*route.marks, "ACC-2.4"), state)
        for name, route in ROUNDS.items()
        if route.slots
        for state in STATES
    ],
)
def test_missing_and_other_workspace_404s_are_identical(name, state):
    world = build_world(state)
    route = ROUNDS[name]
    kind = get_or_post(route)[0]

    def fetch(caller, ids):
        response = send(world.clients[caller], kind, url(name, ids), route.data(world))
        headers = {k: v for k, v in response.headers.items() if k != "Date"}
        return response.status_code, response.content, headers, sorted(response.cookies)

    missing = forged_ids(route, world, "missing")
    reference_a = fetch(COORD_A, missing)
    assert reference_a[0] == 404
    assert fetch(COORD_A, forged_ids(route, world, "other workspace")) == reference_a
    # B's coordinator: A's real IDs look exactly like missing ones.
    assert fetch(COORD_B, own_ids(route, world.target)) == fetch(COORD_B, missing)


@pytest.mark.parametrize(
    ("name", "caller", "state"),
    [
        marked(name, marks, caller, state)
        for name, marks in TESTER_READ_ONLY.items()
        for caller in CALLERS
        for state in STATES
    ],
)
def test_tester_round_matrix(name, caller, state):
    world = build_world(state)
    target = url(name, {"round_id": world.target.round.pk})
    failures = Failures()
    for kind in KINDS:
        expect = expect_tester_round(caller, kind, state)
        exchange(world, caller, kind, target, None, expect, failures)
    failures.assert_none()


@pytest.mark.parametrize(
    ("name", "state", "variant"),
    [
        marked(name, (*marks, "ACC-2.4"), state, variant)
        for name, marks in TESTER_READ_ONLY.items()
        for variant in (*FORGED_URL_IDS, "other workspace")
        for state in ((DRAFT,) if variant in STATELESS else STATES)
    ],
)
def test_forged_tester_round_ids_get_the_404_page(name, state, variant):
    world = build_world(state)
    if variant == "other workspace":
        # Foreign rounds are unavailable in every state, Open and Closed too.
        move_to(world.foreign, state)
        round_id = world.foreign.round.pk
    else:
        round_id = FORGED_URL_IDS[variant]
    forged = url(name, {"round_id": round_id})
    failures = Failures()
    for caller in (ANON, TESTER_A, COORD_A):
        if variant in STATELESS:
            expect = Expect(NOT_FOUND_PAGE, scoped=True)
        else:
            expect = expect_tester_round(caller, GET, state, names_a_round=False)
        exchange(world, caller, GET, forged, None, expect, failures)
    failures.assert_none()


# Submitted and formerly current entries run in Open rounds only: in a Closed
# round, RES-2.4's Closed conflict and RES-2.5's or the stale build's both apply
# (an open decision in the plan).
RESULT_ROWS = [
    *((state, FRESH) for state in STATES),
    (OPEN, SUBMITTED),
    (OPEN, STALE),
]

# Forged IDs in each URL position of result entry.
RESULT_VARIANTS = {
    "round_id": (*FORGED_URL_IDS, "other workspace", "other round"),
    "case_id": (*FORGED_URL_IDS, "other workspace", "other round"),
    "build_id": (
        *FORGED_URL_IDS,
        "other workspace",
        "other round",
        "not covering the case",
    ),
}


@pytest.mark.parametrize(
    ("name", "caller", "state", "situation"),
    [
        marked(TESTER_RESULT, (*RESULT_MARKS, *s.marks), c, state, s.label)
        for c in CALLERS
        for state, s in RESULT_ROWS
    ],
)
def test_tester_result_matrix(name, caller, state, situation):
    situation = next(s for _, s in RESULT_ROWS if s.label == situation)
    entry = result_world(state, situation)
    world = entry.world
    target = url(name, entry.own)
    failures = Failures()
    for kind in KINDS:
        expect = expect_tester_result(caller, kind, state, target, situation)
        exchange(world, caller, kind, target, result_data(world), expect, failures)
    failures.assert_none()


@pytest.mark.parametrize(
    ("name", "state", "slot", "variant"),
    [
        marked(TESTER_RESULT, (*RESULT_MARKS, "ACC-2.4"), state, slot, variant)
        for slot, variants in RESULT_VARIANTS.items()
        for variant in variants
        for state in ((DRAFT,) if variant in STATELESS else STATES)
    ],
)
def test_forged_tester_result_ids_get_the_404_page(name, state, slot, variant):
    entry = result_world(state)
    world = entry.world
    forged = url(name, entry.forged(slot, variant))
    failures = Failures()
    for caller in (ANON, TESTER_A, COORD_A):
        for kind in (GET, POST):
            if variant in STATELESS:
                expect = Expect(NOT_FOUND_PAGE, scoped=True)
            else:
                expect = expect_tester_result(
                    caller, kind, state, forged, names_own=False
                )
            exchange(world, caller, kind, forged, result_data(world), expect, failures)
    failures.assert_none()


@pytest.mark.ac("RES-2.3")
def test_peer_mark_shows_on_the_peers_own_entry_page():
    # Positive control: the peer's draft does reach its own entry page, so
    # the PEER_MARK leak check on tester_a's pages is not vacuous.
    entry = result_world(OPEN)
    peer = signed_in(entry.world.users["peer"])
    response = peer.get(url(TESTER_RESULT, entry.own))
    assert response.status_code == 200
    assert f"Peer {PEER_MARK}" in response.content.decode()


@dataclass(frozen=True)
class BodyIds:
    """A form field that submits record IDs, on a route of the given state."""

    field: str
    state: str
    message: str
    criterion: str

    def record(self, seeded):
        """The record of `seeded` this field names: a criterion or a case."""
        return seeded.linked if self.field == "criteria" else seeded.case


CRITERIA_FIELD = BodyIds(
    "criteria", DRAFT, "Choose criteria from this round.", "RND-2.7"
)
# Routes whose form submits record IDs.
BODY_ID_ROUTES = {
    "rounds:case-new": CRITERIA_FIELD,
    "rounds:case-edit": CRITERIA_FIELD,
    "rounds:retest": BodyIds(
        "cases", OPEN, "Choose test cases from this round.", "RND-5.6"
    ),
    "ai:draft": BodyIds(
        "criteria", DRAFT, "Choose criteria from this round.", "RND-8.8"
    ),
}
BODY_VARIANTS = (*FORGED_URL_IDS, "other workspace", "other round")


def body_id(world, body, variant):
    """A forged ID for `body`'s field: a fixed text ID or a foreign record's."""
    if variant in FORGED_URL_IDS:
        return FORGED_URL_IDS[variant]
    owner = world.foreign if variant == "other workspace" else world.sibling
    return body.record(owner).pk


@pytest.mark.parametrize(
    ("name", "variant", "with_own"),
    [
        marked(name, (BODY_ID_ROUTES[name].criterion, "ACC-2.4"), variant, alone)
        for name in BODY_ID_ROUTES
        for variant in BODY_VARIANTS
        for alone in ("alone", "with own")
    ],
)
def test_forged_body_ids_get_the_field_message(name, variant, with_own):
    body = BODY_ID_ROUTES[name]
    world = build_world(body.state)
    route = ROUNDS[name]
    data = route.data(world)
    forged = body_id(world, body, variant)
    own = [body.record(world.target).pk]
    data[body.field] = [*own, forged] if with_own == "with own" else [forged]
    target = url(name, own_ids(route, world.target))
    before = snapshot(world)
    response = send(world.clients[COORD_A], POST, target, data)
    check(world, COORD_A, response, Expect(OK, scoped=True), before)
    assert body.message in response.content.decode()
    # Refused before the gateway: no unavailable message.
    assert UNAVAILABLE not in response.content.decode()
