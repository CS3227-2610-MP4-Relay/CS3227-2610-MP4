# Slice 25: Authorization test matrix for every current route (#25, part 1)

Goal: one data-driven test module that checks every route of the root URLconf against every caller, method, forged identifier and denied state, as the [security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control) asks, failing when a route has no entry.

Tier: High (role and workspace permissions), so the verifier and security reviewer both run. Base: `01f9a24`, branch `25-route-access-matrix`. Owner: zheng-jj. Refers to #25 without closing it: the RES and AI slices add their routes' rows. Budget: test-only plus one spec sentence; no change under `src/` outside tests.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27 ("just do everything that can be done"), scoped by the coordinator: build the matrix for `/`, the accounts routes and the rounds routes; no product behaviour changes. If the matrix finds an authorization defect, stop and report it with evidence; it is not fixed in this slice.

Builder's design within that scope:

- **No criterion added or changed.** The matrix checks existing criteria; each row carries the criterion IDs it checks with `@pytest.mark.ac`. SECURITY-SPEC gains one sentence naming the module and that RES and AI slices add rows.
- **Home:** `src/relay_tests/test_access_matrix.py`, a cross-app module. It defines its own fixtures and imports only plain helpers (`signed_in`, `csrf_token`, `PASSWORD`, message constants) from `rounds/tests/conftest.py`, so a later move of `relay_tests` (#70) carries it whole.
- **Completeness:** a test walks the root URLconf recursively (`get_resolver()`, as `rounds/tests/test_routes.py` does for one app) and asserts its route names equal the matrix's keys, so a new route fails until it has a row, and a row for a removed route fails too.
- **Expectations come from the specs:** the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action) in their order, the [accounts](../specs/product/accounts.md) criteria, PLT-1.1 and 1.2, and the [routes tables](../specs/TECHNICAL-SPEC.md#accounts-routes). One function derives a rounds route's outcome from the route's row by that rule order; accounts routes are an explicit table, as their rules differ per route.
- **Assumption, from the routes tables:** a route accepts only the methods its table lists. The rounds routes say HEAD gets 405 where only GET is listed; the accounts table lists HEAD only for `/`, so HEAD on the other accounts routes is expected to be 405 too.

## Matrix design

**Callers:** anonymous visitor; Test Coordinator of workspace A (`coord_a`); Beta Tester of workspace A (`tester_a`); Test Coordinator of workspace B (`coord_b`). One client per caller, with `enforce_csrf_checks=True`.

**World, rebuilt per test:** in A, the target round in the state under test (Draft; Open after publishing on "Synthetic 1.0"; Closed after closing) with a linked criterion, a spare unlinked criterion and a case linked to the first; a sibling Draft round in A with its own criterion and case; in B, a Draft round with a criterion and case. Every text is a unique synthetic marker.

**Requests on each row** (unsafe requests carry a valid CSRF token and the route's valid payload unless stated):

| Column | Request |
| --- | --- |
| GET, HEAD | plain |
| POST | valid token and payload |
| no-token | POST without a token |
| foreign-Origin | POST with a valid token and `Origin: https://evil.example` |
| PUT | valid token, a method no route accepts |

**Rounds outcomes**, per the rule order, for the target round's own IDs:

| Request | anonymous | `tester_a` | `coord_b` (A's IDs) | `coord_a` |
| --- | --- | --- | --- | --- |
| no-token, foreign-Origin | 403 | 403 | 403 | 403 |
| method not listed (PUT; HEAD; GET on POST-only) | 405 | 405 | 405 | 405 |
| listed method | 302 to `/sign-in/` | 403 page | 404 page, in every state | state allowed: 200 for GET, 302 to the round page for POST; otherwise 409 naming the state |

States allowed, from the rounds routes table: `new` none needed; `detail` any; `edit`, `criterion-new`/`-edit`/`-delete`, `case-new`/`-edit`/`-delete`, `publish` Draft; `retest` and `close` Open. `coord_b` on `new` creates in B, so it gets `coord_a`'s outcome.

**Forged identifiers**, `coord_a` with GET (or POST on POST-only routes) and POST, for every state of the target round (so 404 is shown before 409); `tester_a` gets 403 and the anonymous visitor the redirect for each, as in RND-1.6:

| Variant | Round slot | Record slot |
| --- | --- | --- |
| missing | an unused ID | an unused ID under the target round |
| other workspace | B's round | B's record under the target round |
| other round | — | the sibling round's record under the target round |
| overflow | `99999999999999999999` | same, under the target round |
| malformed | `abc` (no pattern matches) | `abc` |

All give the 404 page; malformed IDs give it from the resolver.

**Accounts outcomes** (redirects to own home are `/coordinator/` or `/tester/`):

| Route | Request | anonymous | `coord_a` | `tester_a` | `coord_b` |
| --- | --- | --- | --- | --- | --- |
| `/` | GET, HEAD | 200 | 302 own home | 302 own home | 302 own home |
| `/` | POST, no-token, PUT | 405 (CSRF-exempt, PLT-1.2) | 405 | 405 | 405 |
| `/sign-in/` | GET | 200 | 200 | 200 | 200 |
| `/sign-in/` | POST blank fields | 200 failure message | same | same | same |
| `/sign-out/` | GET | 405 | 405 | 405 | 405 |
| `/sign-out/` | POST | 302 `/sign-in/` | same | same | same |
| `/demo/` | GET | 405 | 405 | 405 | 405 |
| `/demo/` | POST | 200 "Your demo workspace" | 302 own home, creates nothing | same | same |
| `/coordinator/` | GET | 302 `/sign-in/` | 200 | 403 page | 200, no A data |
| `/tester/` | GET | 302 `/sign-in/` | 403 page | 200 | 403 page |
| any | no-token, foreign-Origin (except `/`) | 403 | 403 | 403 | 403 |
| any | PUT; HEAD except `/`; POST on GET-only homes | 405 | 405 | 405 | 405 |

**Response checks:** status; exact redirect target (`/sign-in/` with no `next`); the 403 page's "You do not have access to this page."; a 404 body byte-identical to the same client's 404 for an unresolved path; the 409 message naming the state. Every refused request (302 sign-in redirect, 403, 404, 405, 409, and ACC-2.6's redirect) leaves a snapshot of every workspace, account, round, criterion, case, link and build row unchanged. No response to `coord_b` or the anonymous visitor contains any of A's markers, with `coord_a`'s Coordinator home showing A's round title as the positive control. A successful POST runs last on each row, so earlier refusals see the unchanged world.

**Criterion marks:** `/` PLT-1.1, PLT-1.2; sign-in ACC-1.2, ACC-1.8; sign-out ACC-1.5, ACC-1.8; demo ACC-2.1, ACC-2.6, ACC-2.7; homes ACC-1.3, ACC-1.4, ACC-2.4; `new`, `detail`, `edit` RND-1.6, RND-1.7; criteria and cases RND-2.8; publish RND-3.6; retest RND-5.8; close RND-6.3, RND-6.5; forged and cross-workspace rows also ACC-2.4.

## Checkpoints

1. **Spec sentence and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/SECURITY-SPEC.md`, this plan. Check: `git diff --check`; read back.
2. **Matrix tests** (`test:`): `src/relay_tests/test_access_matrix.py`. They are a guard over built behaviour, so they are expected to pass on first run; red evidence is by mutation on temporary copies, each restored and checked with `cmp`, and each must fail the matrix: (a) remove the role check from one coordinator route; (b) remove the workspace filter from one round lookup; (c) look up a criterion or case without its round; (d) add an unlisted route. Checks: focused `pytest -q src/relay_tests/test_access_matrix.py`, Ruff, builder scope check. Full verification is the coordinator's.

Repairs after review are separate `fix:` or `test:` commits. Test expectation changes to existing tests: none.

## Open issues

- RES routes (Beta Tester results) and AI routes add their rows when built; until then #25 stays open.

## Checklist

- [ ] Checkpoint 1: spec sentence and plan.
- [ ] Checkpoint 2: matrix tests with mutation evidence.
