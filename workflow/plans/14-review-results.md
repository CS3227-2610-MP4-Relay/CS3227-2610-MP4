# Slice 14: Review submitted results (#14)

Goal: build the Test Coordinator's read-only results page for an Open or Closed round under [RND-4](../specs/product/rounds.md#rnd-4-review-submitted-results).

## Scope and decisions

- Human request (2026-11-01): build issue #14, RND-4. Tier Standard; the coordinator also runs the security-reviewer, because the slice adds a route with role and workspace authorization and a workspace-scoped query. Base `100bfbd`, branch `14-review-results`.
- Budget: at most 400 changed lines under `src/` outside tests, migrations, `src/e2e/` and conftest files; criteria changed only in RND, 8 or fewer. No dependency, model field, migration or service.
- RND-4's six criteria are reworded in place (IDs kept, none added): the provisional result fields and Pass/Fail vocabulary are settled against [RES-2](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations) and [RES-3](../specs/product/results.md#res-3-review-my-earlier-results): a result is submitted once `submitted_at` is set; drafts never appear; outcome "Pass" or "Fail"; an empty observation shows "No observation."; times as `YYYY-MM-DD HH:MM:SS UTC`. RES's "Planned work" section now points to RND-4.
- Routine choices within the request (builder, checkpoint 1): the round page's "Review results" link sits directly under "State: <state>" while Open or Closed; page title and heading "Results: <title>"; per-case labels "Linked acceptance criteria", "Current build", "Results for this build" and "Earlier builds"; result lines "Tester:", "Outcome:", "Observation:", "Submitted at:" and, for earlier builds, "Build:"; "Back to round" link. Current-build results newest submission first, earlier-build results newest build first; equal times by later-created row. "Earlier builds" appears only when the case has such results.
- Defence in depth, within the request: rows must have case and covering build in the round and a tester in its workspace, as RES-3 constrains its rows.
- Architecture in [rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes); control in [rounds, observations and history](../specs/SECURITY-SPEC.md#rounds-observations-and-history).

## Checkpoints

Only the coordinator changes Git state; the builder yields after each.

1. **Spec** (`spec:`): `workflow/specs/product/rounds.md` (RND-4), `workflow/specs/product/results.md` (pointer), `workflow/specs/TECHNICAL-SPEC.md` (route row, delivery order, RND-4 paragraph), `workflow/specs/SECURITY-SPEC.md` (review bullet). **Plan** (`plan:`): this file. Checks: read back, `git diff --check`, builder scope check.
2. **Feature and server tests** (`feat:`): `src/rounds/views.py` (`results_page`), `src/rounds/urls.py`, `src/rounds/templates/rounds/results.html` and `result_lines.html` (new), `src/rounds/templates/rounds/round.html` (link), `src/rounds/tests/test_review.py` (new), `src/relay/tests/test_access_matrix.py` (rows for `rounds:results`, and a check that a peer's draft stays hidden from the coordinator's results page). Tests marked RND-4.1–4.6: link presence/absence by state; content, order and UTC times; empty and earlier-only cases; retest and close; drafts and malformed rows excluded; no forms and no changes; fixed query count; rendering (markup, attributes, page-title isolates with a stray U+2069 then U+202E, line breaks, direction and zero-width characters) for round title, case title, criterion text, build labels, usernames and observations; rules order: 405 for HEAD/POST/PUT, CSRF 403, sign-in redirect, tester 403 before lookup, 404 for missing and other-workspace rounds in every state, 409 for Draft, no-store, 503 for each storage failure. Red first. Checks: focused `pytest src/rounds src/relay/tests/test_access_matrix.py`, targeted Ruff.
3. **Browser journey** (`test:`): `src/e2e/test_review.py` (new): a coordinator publishes, two testers submit and draft, the coordinator follows "Review results", then retests and closes. Check: the new and existing affected browser tests.
4. **User Guide and status** (`docs:`): `docs/UserGuide.md` in the product's exact words; RND status sentence in `rounds.md`. Then full verification: `ruff check . && ruff format --check . && pytest`, `manage.py check` and `makemigrations --check --dry-run` with test settings.

## Size estimate

About 80 changed application lines: view ~35, URL 1, results template ~35, round-page link ~2.

Actual: 47 insertions and 3 deletions in tracked application files (`views.py`, `urls.py`, `round.html`) plus 28 lines in the new `results.html` and `result_lines.html`, about 78 changed lines.

## Progress

- Checkpoint 1: spec `aaa77e2`, plan `5108dd5`.
- Checkpoint 2 (`2c66919`): red run 46 failed, 5 passed in `test_review.py` (the five justified as absence or missing-route 404 checks; the no-controls test gained a 200 assertion and then failed); matrix 34 failed. Green: 51 passed; `src/rounds` with the matrix 1,585 passed. Mutations (drop the submitted, coverage or tester-workspace filter; unfiltered username) each failed tests. Test change for the verifier: `test_routes.py`'s cache walk sends the results route to its Open round and expects 200.
- Checkpoint 3 (`d0d9fef`): `src/e2e/test_review.py` passed; it failed with the link removed, the draft filter dropped, or earlier rows listed as current, each restored and confirmed with `cmp`.
- Checkpoint 4: User Guide "Review results" section and links from the Open and Closed round sections; Developer Guide sentence on `results_page`; RND status sentence. Results of full verification are in the builder's handoff.

## Repair round 1 (candidate `de0a8b5`)

Verifier and security-reviewer: nothing High. Fixes are tests and comments only; no application change.

- Medium (verifier): RND-4.2's no-"Earlier builds" rule for a retested case was untested. New `test_a_retested_case_without_earlier_submissions_has_no_earlier_builds[none/draft]`. Mutant `{% if case.builds.all|length > 1 %}` in `results.html`: both fail.
- Low (both): the prefetches' round filters were untested. `test_drafts_and_rows_outside_the_rounds_covering_builds_never_appear` now gives the forged cross-round build the label "Synthetic forged build", adds a forged `CaseCriterion` to a foreign "Synthetic alien" criterion, and checks the valid result sits under case A's own current build with no "Earlier builds". Mutants dropping the `builds` filter or the `criteria` filter: that test fails for each.
- Low (verifier): RND-4.5 now retests case A so its hostile-labelled build shows as "Build: <label>"; the count stays 9 (case A's current build is now plain). Mutant `result.build.label|safe`: 3 tests fail.
- Nit (security): the 503 test asserts the seeded observation is absent from `caplog` and the wrapper's fixed log message is present.
- Nits (verifier): unused `second_tester` fixture removed; `test_routes.py` comment updated; `result_lines.html` added to checkpoint 2's paths.
- Left out by the coordinator: the shared `snapshot` import, the `-build_id` ordering note, tie-break wording, RES-2.3/RES-3.4 wording (raised with the human) and `show_round`'s unfiltered prefetches (a follow-up).

Mutants were restored from scratch copies; `git diff --exit-code -- src/rounds/views.py src/rounds/templates` was clean. Check results are in the builder's handoff.

## Follow-ups checkpoint (HEAD `3904131`)

The human asked to "resolve them all", confirming the three follow-ups left out of repair round 1, including RES criteria text.

1. **Spec** (`spec:`, no behaviour change): `workflow/specs/product/results.md` RES-2.3 and RES-3.4 now say they add no coordinator route and point to RND-4; `workflow/specs/product/rounds.md` drops the "Provisional" wording from the round-states table, its note and RND-5's intro, linking RES-2. No other provisional or later-requirement result wording remains in the specs.
2. **Fix** (`fix:`): `src/rounds/views.py` `show_round` prefetches covered cases and linked criteria constrained to the round, as `results_page` does; `docs/DeveloperGuide.md` notes it. Regression `src/rounds/tests/test_records.py::test_round_page_shows_only_its_own_rounds_linked_records[open/closed]` (RND-2.8, RND-3.6): forged `CaseCriterion` and `BuildCase` rows to a sibling round and another workspace, plus newer foreign builds covering the own case. Red before the fix: 2 failed (sibling and foreign criterion text shown). Green after: 2 passed. Mutants dropping either filter fail it again. The current-build assertion already held before the fix, because builds come only from the round; it guards against a regression that read builds through the case.
   Survey of other pages: the tester detail, tester history, RES-4 feedback and RND-4 results pages already constrain criteria and builds to the round; result entry looks builds up through `round_.builds`; the case, retest and drafting forms offer only the round's records. No other page has the defect.
3. **Plan** (`plan:`): this section.

## Open items

None.
