# Slice 16: Request a retest (#16)

Goal: implement [RND-5](../specs/product/rounds.md#rnd-5-request-a-retest) under the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action), the fifth rounds code slice.

Tier: Standard, as the issue says. The slice adds a second build-creating write on an Open round and its races (with itself and with a close), but no new role, workspace or permission rule: the retest route reuses `coordinator_view(methods)` and `own_round`. It adds a route, renders user text (case titles, the label in a field and in a success message) and takes form-submitted case IDs, so the [security-reviewer trigger](../skills/slice.md) for Standard applies and the security reviewer runs alongside the verifier. Base: `b4e3a85`, branch `16-request-retest`, stacked on RND-6's `18-close-round` (which contains RND-3, RND-2, RND-1, ACC-2 and ACC-1); the PR base is `18-close-round`. Owner: zheng-jj. Budget: one requirement (RND-5, 8 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** RND-5 only: the retest route and form (case selection and build label); the retest service under the round-row lock (Open re-check, 409; the cap of 10 builds counting the publish build; selected case IDs re-checked against the locked round; the duplicate label checked by `build_key` under the lock before any insert, so no `IntegrityError` detail with a label reaches the logs; distinct cases counted); the success message, singular or plural; the updated current build per case; the RND-5.7 races (two retests with one label; a retest racing a close).
- **Labels:** `build_key` stays NFC, not NFKC, as RND-3 decided; compatibility look-alikes count as distinct labels. Recorded as an accepted residual in the [security spec](../specs/SECURITY-SPEC.md#rounds-observations-and-history).
- **User text:** no label in exception messages or model reprs. The success message contains the label, which is rendered escaped and per-line isolated, with RND-5.8 rendering tests for the message.
- **From RND-6's security re-review:** the retest takes the same round-row lock and re-checks Open (409 for Draft or Closed) before writing; any path that can meet `RoundNotOpen` maps it to the 409, never a 500. Services trust their caller for workspace authorization, so the view looks the round up through `own_round` and the service re-checks the case IDs against that locked round.
- **Not included:** tester views and results (RES), the sample round (RND-7), results review (RND-4). Retest is only for Open rounds.
- **Reuse:** `coordinator_view(methods)`, `own_round`, `show_round`, `state_conflict`, the 409 page, `RoundTextField`, `Refused`, `RoundNotOpen`, `build_key`, `isolated_lines`, `title_isolate`, Django messages under the heading, the conftest `race()` helper and `test_routes.py`'s route walk.

Builder's spec details within that scope (checkpoint 1), for the coordinator to confirm:

- **Separate page, linked from the round page.** The [rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes) already give `/retest/` GET and POST with the page title "Request a retest", so the form is its own page, as RND-2's forms are, not a form on the round page. The Open round page gets a "Request a retest" link directly under the "Builds" heading (as RND-2's add links sit under their headings), which leaves RND-6's "after Builds, warning then Close round" placement unchanged. Page text is in the [RND-5 introduction](../specs/product/rounds.md#rnd-5-request-a-retest): a "Test cases to retest" checkbox group (each case's title, creation order, none selected), a "Build label" field, a "Request retest" button and "Back to round". The page title "Request a retest" has no user text.
- **Order of checks:** rules 1 to 4 (CSRF, method, sign-in and role, 404, 409 including GET); both fields validated independently (RND-5.2 and RND-5.6 next to "Test cases to retest"; RND-5.2's label message next to "Build label"); then under the lock: Open (409), cap (RND-5.4), case IDs again (RND-5.6), label uniqueness (RND-5.3), first refusal only, the cap and label messages next to "Build label". Cap before case IDs follows `add_case` (cap, then links).
- **Success message mechanism** ([retesting](../specs/TECHNICAL-SPEC.md#rounds)): `messages.success` with the full sentence and the extra tag `retest`; the round page shows a `retest` message as fixed text plus only the label, the part between "on build " and the final full stop, through `isolated_lines`. A message left unread shows only on the sign-in page after signing out, escaped but not isolated: recorded as an accepted residual in the security spec.
- **`RoundNotOpen` text:** it now refuses a retest too, so its fixed text becomes "The round is not Open." (no user text; never shown to users).
- **Specs changed:** `rounds.md` (RND-5 introduction), `TECHNICAL-SPEC.md` (a "Retesting" bullet; RND-5's delivery-order sentence), `SECURITY-SPEC.md` (one bullet: the locked checks and the two residuals). No criterion added or changed.

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, `workflow/specs/SECURITY-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Retest form and service** (`feat:`): `src/rounds/forms.py` (`RetestForm(round_, ...)`: cases as `ModelMultipleChoiceField` over `round_.cases`, checkboxes, error messages; `label` as `PublishForm`'s), `src/rounds/services.py` (`request_retest(round_, label, case_ids)`, `BUILD_LIMIT = 10`, messages; `RoundNotOpen` text), `src/rounds/tests/test_retest_services.py` (new). Tests, marked, red first (the import of `request_retest` fails):
   - RND-5.1 one and two selected cases get a new build covering exactly them; their current build is the new one, others keep theirs; a repeated ID gives one `BuildCase`.
   - RND-5.2 form: no selection gets "Select at least one test case."; labels of 100 (and padded), empty, invisible-only and 101 as RND-3.2; both invalid give both messages.
   - RND-5.3 an equal label, one differing only by U+200B, and a decomposed form of a composed label are refused with nothing written; a label differing in case, and a full-width look-alike (NFKC-equal only), are accepted; a label used in another round is accepted.
   - RND-5.4 with 9 builds (publish included) the 10th is created; with 10 the 11th is refused with nothing written.
   - RND-5.5 a case retested twice has three builds; earlier builds keep their cases; criteria, cases and links unchanged.
   - RND-5.6 form and service: a case of another round, of another workspace, a missing ID and a non-integer get "Choose test cases from this round."; the service refuses a foreign ID passed directly, nothing written.
   - RND-5.8 service: a Draft or Closed round raises `RoundNotOpen` with nothing written; no refusal or error text contains the label; `str()` of a new build has no label.
   Checks: `pytest src/rounds -q` through the shared test-database lock; Ruff.
3. **Route, retest page, round page and RND-5 tests** (`feat:`): `src/rounds/{views,urls}.py` (`request_retest` view; `retest/` route; `show_round` passes the `retest` message parts), `src/rounds/templates/rounds/retest.html` (new), `src/rounds/templates/rounds/round.html` (link under "Builds" while Open; message rendering), `src/rounds/templatetags/rounds_text.py` if the label split lives in a filter, `src/rounds/tests/test_retest.py` (new), `src/rounds/tests/test_routes.py` (the walk covers the retest route with an Open round, GET 200 and an empty POST 200, whatever the route order). Tests, each marked, red first:
   - RND-5.1 the page lists every case's title as a checkbox in creation order, none checked; requesting redirects to the round page showing "Retest requested for 2 test cases on build <label>." (and "1 test case" for one, and for one case submitted twice) once, gone on reload; the selected cases show the new current build, others the old; the "Builds" list ends with the new build and its cases.
   - RND-5.2 and 5.6 each invalid input on its own, then both fields invalid together: status 200, messages next to their fields, selections and label kept, no build.
   - RND-5.3 and 5.4 through the route: message next to "Build label", values kept, no build; an 11th build with a duplicate label gets only the cap message.
   - RND-5.5 two retests of one case: both builds listed with their cases; criteria and cases unchanged.
   - RND-5.7 threaded races with `race()`, `request_retest` paused inside the locked transaction: two retests with one label give one 302 and one 200 with the RND-5.3 message, one new build, and no `IntegrityError` logged (`caplog`); a retest then a close: both succeed, the build exists, the round Closed; a close then a retest: 302 and 409, no new build.
   - RND-5.8 rules: GET and POST 409 for Draft and Closed with the exact message, nothing written; 405 for HEAD and PUT; 403 for a missing CSRF token and a foreign `Origin`; signed-out redirect and tester 403 for existing and missing IDs; 404 "Page not found." for another workspace's round in each state, never 409; a state change between the first check and the locked write (patched) gives 409; `RoundNotOpen` from the service gives 409, not 500; `DatabaseError` in `request_retest` gives the 503 with no build; never cached. Rendering: the label in the success message (markup escaped; line breaks as per-line `<span dir="auto">`; bidi and zero-width characters inside them; the fixed text outside the spans), in the field value after a refusal, and in the round page's current build and builds list; case titles in the checkbox labels; neither in any `<title>`. The retest form's own CSRF token works under enforced CSRF. The Draft and Closed pages have no "Request a retest" link.
   Checks: focused `pytest src/rounds -q`, then full verification. Mutations: no lock, no locked Open re-check, no locked duplicate check (race must fail or log an `IntegrityError`), the label through `|safe`.
4. **Guides and status** (`docs:`): `docs/UserGuide.md` (requesting a retest, its fields, messages and the updated round page, in the product's exact words), `docs/DeveloperGuide.md` (retest service and form), the status sentences of `rounds.md`, `TECHNICAL-SPEC.md` and `SECURITY-SPEC.md`. Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

Possible test expectation changes, at checkpoint 3: the link sits after `<h2>Builds</h2>`, so RND-3 and RND-6 tests that slice the page from that heading (`test_publish.py`, `test_close.py`) may need narrowing; any change will be listed here for the verifier.

## Size estimate

Non-test, non-migration `src/` lines: forms ~20, services ~35, views ~40 (retest view ~30, message parts ~10), urls ~1, templates ~30 (retest page ~20, round page ~10); about 126 of 400. No migration: `Build` and `BuildCase` already exist.

## Open issues

- Browser check of the per-line `dir="auto"` rendering of the label in the success message: open for the human (tests check the markup only).
- Whether testers are prompted about a retest is RES's (Whimsyturtle's).

## Checklist

- [ ] Checkpoint 1: specs and plan.
- [ ] Checkpoint 2: retest form, service and tests.
- [ ] Checkpoint 3: route, retest page, round page and RND-5 tests.
- [ ] Checkpoint 4: guides and status.
- [ ] Full verification, size budget and builder scope check.
