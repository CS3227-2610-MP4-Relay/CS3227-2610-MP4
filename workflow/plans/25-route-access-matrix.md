# Slice 25: Authorization test matrix for every current route (#25, part 1)

Goal: one data-driven test module that checks every route of the root URLconf against every caller, method, forged identifier and denied state, as the [security spec](../specs/SECURITY-SPEC.md#sign-in-and-access-control) asks, failing when a route has no entry.

Tier: High (role and workspace permissions), so the verifier and security reviewer both run. Base: `01f9a24`, branch `25-route-access-matrix`. Owner: zheng-jj. Refers to #25 without closing it: later slices (RND-4's results route, RES, AI) add their routes' rows. Budget: test-only plus one spec sentence; no change under `src/` outside tests.

## Decisions

Confirmed by the human (zheng-jj) on 2026-10-27 ("just do everything that can be done"), scoped by the coordinator: build the matrix for `/`, the accounts routes and the rounds routes; no product behaviour changes. If the matrix finds an authorization defect, stop and report it with evidence; it is not fixed in this slice.

Builder's design within that scope:

- **No criterion added or changed.** The matrix checks existing criteria; each row carries the criterion IDs it checks with `@pytest.mark.ac`. SECURITY-SPEC gains one sentence naming the module and that later slices add rows for their routes.
- **Home:** `src/relay/tests/test_access_matrix.py` (moved from `src/relay_tests/` when #75 moved the project tests for #70), a cross-app module. It defines its own fixtures and imports only plain helpers (`signed_in`, `csrf_token`, `PASSWORD`, message constants) from `rounds/tests/conftest.py`, so it moved whole and unchanged with the project tests.
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

## Review round 0 (candidate `0f6322a`) and repair round 1

Verifier and security reviewer findings, decided by the coordinator on 2026-10-27; no product defect was found. All repairs are test-only, except the R9 wording.

- **R1 (security M1):** leaks are checked in both directions. `B_MARK` is absent from every response to the visitor, `coord_a` and `tester_a`; the sibling round has its own marker, absent from every page about the target round (every rounds route but `new`); `coord_b`'s Coordinator home shows B's marker as a positive control.
- **R2 (verifier M1, security L4):** marker checks are case-insensitive, so A's usernames and workspace name are covered; the positive control checks them on A's pages; the module docstring says so.
- **R3 (verifier M2, security L2):** a successful write is confined to the caller: rows of the other workspace and of the sibling round stay unchanged; routes with IDs redirect exactly to the target's round page; `rounds:new` creates its round in the caller's workspace. Mutation: `new_round` creating in another workspace fails it.
- **R4 (security L3):** a forged-body-ID test for the IDs a form submits (the case form's `criteria` on case-new and case-edit, retest's `cases`), with another workspace's, the sibling round's, missing, overflow, malformed and zero IDs: 200 with the field's message ("Choose criteria from this round." or "Choose test cases from this round.") and an unchanged snapshot. Security reviewer's check: the retest form's queryset widened to `Case.objects.all()` fails it.
- **R5 (security L5):** per route and state, the "missing" and "other workspace" 404 responses are identical in status, body and headers apart from `Date`.
- **R6 (verifier L3):** every 405's `Allow` header lists exactly the row's methods.
- **R7 (verifier L5):** 403 pages are compared byte-for-byte with the same client's reference 403.
- **R8 (verifier L8):** forged URL IDs include `0` and `00` (the `int` converter accepts both).
- **R9 (verifier L7):** SECURITY-SPEC and this plan say later slices add rows, since RND-4's results route is not RES.
- **R10 (verifier L4):** the accounts HEAD 405 stays a recorded assumption; see open issues.
- **R11 (optional):** `rounds:new` and the malformed variant run once instead of per state; failures within a row are collected and reported together; method names and variant IDs are explicit.
- Not changed: `Session` and limit-counter rows stay out of the snapshot (verifier L6); see open issues.

Repair checkpoints, one commit each: (A) the spec wording and this plan (`spec:`, `plan:`); (B) the test repairs (`test:`) with mutation evidence for R1, R3 and R4.

## Re-review of repair round 1 and repair round 2

Re-reviews of `0f6322a..d0ad39a` and of the move found no gaps. Repair round 2, the last (coordinator, 2026-10-27), test and plan only:

- **F1 (both reviewers, Low):** the four-letter marks could match a random CSRF token or generated password case-insensitively, about a 1% false failure per run. The marks are now `mtx-a`, `mtx-b` and `mtx-s`; CSRF tokens and generated passwords are letters and digits only, and the model fields for workspace names and usernames take a hyphen.
- **F2 (security L5 rest, verifier Info):** the 404 sameness test also compares cookie names.
- **F3 (verifier nits):** `"00"` joins the body variants; body IDs come from one table shared with the URL variants and a `BodyIds` entry per route.
- **F4 (security Info):** `tester_a` has bystander rows, and a caller without any fails with a message; a successful rounds write by `coord_a` must leave A's workspace row and accounts unchanged, and one by `coord_b` B's.

## Merge of main with RES-1 (#12)

The coordinator merged `origin/main` at `c2a315b`, bringing RES-1's `accounts:tester-round` (`/tester/rounds/<round>/`, `rounds.tester.detail`); `test_every_route_has_a_matrix_entry` then failed with "Extra items in the left set: 'accounts:tester-round'". Test and plan only, expectations from RES-1.4 and 1.5, the [tester routes](../specs/TECHNICAL-SPEC.md#tester-routes) and the SECURITY-SPEC tester-availability bullet:

- **Row:** `expect_tester_round` applies the spec's order: CSRF 403, then 405 for every method but GET (HEAD included), sign-in redirect, 403 for any coordinator, then 404 unless the round is the tester's own Open or Closed round. `test_tester_round_matrix` sends every request kind for each caller and state of the target round (12 tests); `test_forged_tester_round_ids_get_the_404_page` sends the forged URL IDs and another workspace's round, moved to the same state, as `anonymous`, `tester_a` and `coord_a` (16 tests). Pages about the target must not show its sibling's mark.
- **Mutations** on temporary edits of `src/rounds/tester.py`, each restored and confirmed with `git diff --exit-code`: (a) no tester role check failed 23 (`accounts:tester` for both coordinators, the 6 coordinator rows of the detail matrix and the 15 forged rows other than malformed, where `coord_a` got past 403); (b) Draft in `available_rounds` failed 1 (`tester_a` on the Draft target); (c) `Round.objects` instead of `workspace_records` failed 2 (the Open and Closed "other workspace" rows). Mutation (c) first survived, because the foreign round stayed Draft; moving it to the row's state fixed that.
- `pytest -q -p no:cacheprovider src/relay/tests/test_access_matrix.py`: 453 passed. Ruff clean.

## Open issues

- Later routes add their rows when built: RND-4's results route, the RES (Beta Tester results) routes after RES-1 and the AI routes; until then #25 stays open.
- The accounts routes table does not say, as the rounds routes do, that a route accepts exactly the methods listed; the matrix's HEAD 405 on accounts routes other than `/` rests on the recorded assumption (kept by the coordinator, R10). Suggested later spec wording for the accounts routes: "A route accepts exactly the methods listed, so HEAD gets 405 where only GET is listed." No spec change in this slice.
- Not sent: PATCH, DELETE and OPTIONS; PUT stands for an unlisted method (verifier Info).
- CSRF variants beyond a missing token and a foreign `Origin`, such as a wrong or stale token, are left to Django's own tests (verifier Info).
- The Tester home is not checked for Draft round titles, the second half of RND-1.6; the RES slice's tester pages will need it (verifier Info).
- The snapshot leaves out `Session` and the ACC-3 limit counters (verifier L6, coordinator's decision): sign-in, sign-out and failed sign-ins change them by design, and ACC-1 and ACC-3 tests own those rows.

## Checklist

- [x] Checkpoint 1: spec sentence and plan (`0490f73`, `d53542d`). HEAD assumption confirmed by the coordinator against the code: `require_GET` gives HEAD 405.
- [x] Repair (A): spec wording and plan (`25c8c8d`, `d439c5e`).
- [x] Repair (B): `src/relay_tests/test_access_matrix.py`, 419 tests: completeness (1), positive controls for every mark (1), accounts by caller (24), rounds by caller and state (136; `rounds:new` once), forged URL IDs by route, variant and state (188; malformed once per route), identical missing and other-workspace 404s (33), forged body IDs alone and alongside an own ID (36). Requests are described by a `Kind` (method, token, Origin); a row reports every failing request. `pytest -q --durations=5 src/relay_tests/test_access_matrix.py`: 419 passed in 20.31s, slowest test 0.13s. Mutations on temporary copies, each restored and checked with `cmp`; R1 and R3 also run against the `0f6322a` matrix, which passed all 314 under each: (R1) the Coordinator home listing rounds of `workspace_id >= own` (B to A only) failed 1, `accounts:coordinator-coord_a` with `leaked ['mtxb']`; (R1) the round page listing every case of the workspace failed 3, `rounds:detail-coord_a` in each state, leaking the sibling mark; (R3) `new_round` creating in the first other workspace failed 2, `rounds:new` for `coord_a` and `coord_b`, on the created round's workspace. Security reviewer's check, `src/rounds/forms.py:125` as `Case.objects.all()`: 13 failed (the retest page's `coord_a` GET and 12 retest body-ID cases), all on the leak check, because the form then lists every case; with the leak check switched off on a temporary copy, the same mutation passes, since `services.request_retest` re-checks the cases against the round and gives the same message, and widening that service check too fails the four "other workspace" and "other round" retest cases. Ruff clean.
- [x] Merge of main (`33ea8e6`, including #75) by the coordinator: the matrix moved to `src/relay/tests/test_access_matrix.py` with identical content, and the SECURITY-SPEC path to it was updated inside that merge commit, not in a `spec:` commit; plan updated in `5da281c`.
- [x] Repair round 2: `src/relay/tests/test_access_matrix.py`, 425 tests (the 6 new "double zero" body cases). `pytest -q -p no:randomly --durations=3 src/relay/tests/test_access_matrix.py`: 425 passed in 20.64s, slowest 0.18s. F1 evidence on temporary copies with `django.middleware.csrf._get_new_csrf_string` patched to return `"mtxamtxbmtxs" + "Q" * 20`, so every CSRF mask and token holds the old marks; copies deleted afterwards: the `5da281c` matrix failed 54 of 419, each on `leaked`; the repaired matrix passed all 425. Ruff clean.
- [x] Checkpoint 2: `src/relay_tests/test_access_matrix.py`, 314 tests: route completeness (1), accounts routes by caller (24), the marker positive control (1), rounds routes by caller and state (144), forged IDs by route, state and variant (144). First run: `pytest -q -p no:randomly src/relay_tests/test_access_matrix.py` 314 passed, so no spec contradiction was found; also passed in random order. Mutations on temporary copies of `src/rounds/views.py` or `src/rounds/urls.py`, each restored and checked with `cmp`: (a) skipping the role check for `close_round` only failed 12 (the tester rows of `close` in every state, and its forged rows, where the tester got past 403); (b) `own_round` reading `Round.objects.all()` failed 54 (`coord_b` on every route naming a round, in every state, and every "other workspace" round variant); (c) `round_record` looking the record up without its round failed 24 (the "other workspace" and "other round" variants of the four criterion and case edit/delete routes, in every state); (d) an unlisted `rounds:extra` route failed `test_every_route_has_a_matrix_entry` with "Extra items in the left set: 'rounds:extra'". Ruff clean.
