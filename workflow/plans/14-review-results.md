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
2. **Feature and server tests** (`feat:`): `src/rounds/views.py` (`results_page`), `src/rounds/urls.py`, `src/rounds/templates/rounds/results.html` (new), `src/rounds/templates/rounds/round.html` (link), `src/rounds/tests/test_review.py` (new), `src/relay/tests/test_access_matrix.py` (rows for `rounds:results`, and a check that a peer's draft stays hidden from the coordinator's results page). Tests marked RND-4.1–4.6: link presence/absence by state; content, order and UTC times; empty and earlier-only cases; retest and close; drafts and malformed rows excluded; no forms and no changes; fixed query count; rendering (markup, attributes, page-title isolates with a stray U+2069 then U+202E, line breaks, direction and zero-width characters) for round title, case title, criterion text, build labels, usernames and observations; rules order: 405 for HEAD/POST/PUT, CSRF 403, sign-in redirect, tester 403 before lookup, 404 for missing and other-workspace rounds in every state, 409 for Draft, no-store, 503 for each storage failure. Red first. Checks: focused `pytest src/rounds src/relay/tests/test_access_matrix.py`, targeted Ruff.
3. **Browser journey** (`test:`): `src/e2e/test_review.py` (new): a coordinator publishes, two testers submit and draft, the coordinator follows "Review results", then retests and closes. Check: the new and existing affected browser tests.
4. **User Guide and status** (`docs:`): `docs/UserGuide.md` in the product's exact words; RND status sentence in `rounds.md`. Then full verification: `ruff check . && ruff format --check . && pytest`, `manage.py check` and `makemigrations --check --dry-run` with test settings.

## Size estimate

About 80 changed application lines: view ~35, URL 1, results template ~35, round-page link ~2.

## Open items

None. Progress and check evidence go in the handoffs.
