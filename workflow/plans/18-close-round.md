# Slice 18: Close a round (#18)

Goal: implement [RND-6](../specs/product/rounds.md#rnd-6-close-a-round) under the [rules for every round action](../specs/product/rounds.md#rules-for-every-round-action), the fourth rounds code slice.

Tier: Standard, as the issue says. The slice adds one state transition (Open to Closed) and its race, but no new role, workspace or permission rule: the close route reuses RND-1's `coordinator_view` and `own_round`, takes no form fields, no form-submitted IDs and no build ID. Because it adds a route, the [security-reviewer trigger](../skills/slice.md) for Standard applies, so the security reviewer runs alongside the verifier. Base: `0099cf2`, branch `18-close-round`, stacked on RND-3's `11-publish-round` (which contains RND-2, RND-1, ACC-2 and ACC-1); the PR base is `11-publish-round`. Owner: zheng-jj. Budget: one requirement (RND-6, 5 existing criteria, none added or changed); at most 400 changed lines under `src/` outside tests and migrations.

## Decisions

Made by the coordinator on 2026-10-27 under the human's (zheng-jj) delegation, "make my decisions for me":

- **Scope:** RND-6 only: `Round.closed_at` and its migration; the close service (round row lock, Open re-check, Closed state and closing time); the close route as a POST button on an Open round's page with the RND-6.2 warning; "Round closed." once; the Closed round page (criteria, cases and builds visible, no controls); the RND-6.4 race test. No reopening anywhere.
- **Reuse:** RND-1/2/3's `coordinator_view(methods)`, `own_round`, `show_round`, `state_conflict`, the 409 page, RND-3's success-message pattern (Django's messages, directly under the heading) and `test_routes.py`'s route walk.
- **Not included:** retests (RND-5), tester views and results (RES), the sample round (RND-7).
- **Merge order:** RND-3's publish route and Open round page come at its checkpoint 3. This slice's checkpoint 2 stays out of `views.py`, `urls.py`, templates and view tests; checkpoint 3 starts only after the coordinator merges RND-3's checkpoint 3 into this branch.

Builder's spec details within that scope (checkpoint 1), all confirmed by the coordinator on 2026-10-27 under the same delegation, with Tier Standard and the security reviewer run, and the checkpoint 3 notes on the route walk and RND-3's no-form assertion:

- Page text in the [RND-6 introduction](../specs/product/rounds.md#rnd-6-close-a-round): while Open, the round page ends, after "Builds" and before "Coordinator home", with the paragraph "Closing makes this round read-only. It cannot be reopened." directly followed by a "Close round" button; no further confirmation (as RND-2's deletes); "Round closed." once, directly under the heading, as RND-3's message; the Closed page shows what the Open page shows (title, "State: Closed", criteria, cases with linked criteria and current build, "Builds") with no "Edit round" link, RND-2 controls, publish form, warning or close button; the closing time is stored, not shown.
- [Technical details](../specs/TECHNICAL-SPEC.md#rounds): `Round.closed_at` (empty until closing); the closing flow (no form fields; one transaction locking the round row and re-checking Open, 409 otherwise; `rounds.services.close(round_)` sets the state and `closed_at`; message after commit; redirect). One delivery-order sentence under [Rounds routes](../specs/TECHNICAL-SPEC.md#rounds-routes). As RND-3, no check constraint ties `closed_at` to the state. The security spec needs no change: its rounds section already names the one-way states and the RND-6.4 lock.
- The view locks before its only state check (as RND-2's deletes), because the route has no form to show first.
- `close()` has no state guard of its own: the view's locked re-check is the single check, matching `publish` (coordinator, 2026-10-27, at checkpoint 2).

## Checkpoints

1. **Specs and plan** (this checkpoint, `spec:`/`plan:`): `workflow/specs/product/rounds.md`, `workflow/specs/TECHNICAL-SPEC.md`, this plan. Check: `git diff --check`; read changed sections back.
2. **Closing time, migration and close service** (`feat:`): `src/rounds/models.py` (`Round.closed_at`), `src/rounds/migrations/0004_round_closed_at.py`, `src/rounds/services.py` (`close`), `src/rounds/tests/test_close_services.py` (new). `close(round_)` runs in the caller's transaction after the lock and Open re-check, sets the state to Closed and `closed_at`, and writes nothing else. Tests, marked: RND-6.1 an Open round with builds becomes Closed with `closed_at` set and `published_at`, criteria, cases, links, builds and covered cases unchanged; RND-6.2 an Open round whose cases have no results closes; unmarked: `closed_at` is empty on a new and a published round. Red first (import of `close` fails). Checks: `makemigrations --check`, `pytest src/rounds -q` through the shared test-database lock.
3. **Route, round page and RND-6 tests** (`feat:`), after RND-3's checkpoint 3 is merged: `src/rounds/{views,urls}.py` (`close_round` view, `close/` route; `show_round` passes whether the round is Open), `src/rounds/templates/rounds/round.html` (warning and button while Open; the message slot RND-3 adds), `src/rounds/tests/test_close.py` (new), `src/rounds/tests/test_routes.py` (the walk sets its round Open just before posting to the close route, so that route gets its 302 rather than a Draft 409; confirm against RND-3's final walk). Tests, each marked:
   - RND-6.1 closing an Open round redirects to its page showing "Round closed." once (gone on reload), "State: Closed", every criterion, case, linked criterion, current build and the "Builds" list, with no "Edit round", RND-2 controls, publish form, warning or "Close round" button.
   - RND-6.2 an Open round's page shows the warning directly before the "Close round" button, after "Builds" and before "Coordinator home"; a Draft round's page shows neither; an Open round with untested cases closes.
   - RND-6.3 closing a Closed round gets 409 with "This action is not available while the round is Closed." and `closed_at` unchanged; a walk of every rounds route with GET and with a CSRF-valid POST on a Closed round leaves it Closed with `closed_at` unchanged, and no route or page offers reopening.
   - RND-6.4 threaded race, as RND-3.5, with `services.close` patched to pause 0.1 s inside the locked transaction: two closes give exactly one 302 and one 409, and `closed_at` is the winner's.
   - RND-6.5 rules: 405 for GET, HEAD and PUT; 403 for a missing CSRF token and a foreign `Origin`, nothing changed; signed-out redirect and tester 403 for existing and missing round IDs alike; 404 "Page not found." for another workspace's round in Draft, Open and Closed, never 409, and a missing round; 409 for a Draft round, nothing changed; `DatabaseError` in `close` gives the 503 with the round Open and `closed_at` empty; never-cached responses. Rendering on the Closed page (the text it renders: round title in content and `<title>` with isolates incl. a stray U+2069 then U+202E, criterion and case text, build labels): markup escaped, line breaks as per-line `<span dir="auto">`, bidi and zero-width characters kept inside them; the success message holds no user text.
   Red first, recording the failures. Checks: focused `pytest src/rounds -q`, then full verification.
4. **Guides and status** (`docs:`): `docs/UserGuide.md` (closing, its warning, message and the Closed page, in the product's exact words), `docs/DeveloperGuide.md` (close service), the status sentences of `rounds.md`, `TECHNICAL-SPEC.md` and, if it names built requirements, `SECURITY-SPEC.md`. Check: read back; `git diff --check`; builder scope check.

Repairs after review are separate `fix:` commits.

Test expectation changes (for the verifier), at checkpoint 3: RND-6's "Close round" form appears on every Open round page, so two earlier assertions that an Open page has no `<form` at all are narrowed to the forms they own. `test_records.py::test_open_or_closed_round_page_lists_records_without_controls` (RND-2.8) now asserts no delete-form action (`/delete/"`); `test_publish.py::test_round_page_after_publishing_shows_the_message_once_and_the_open_view` (RND-3.1) now asserts no delete or publish action (`/delete/"`, `/publish/"`). Their text-control assertions stay. RND-6.1's own test asserts that a Closed page has no `<form` at all. `test_routes.py`'s walk posts to the close route with a separate Open round, whatever the route order, and expects its 302; its Draft round stays Draft. At checkpoint 4, RND-3's `race` helper moved from `test_publish.py` to `conftest.py`, unchanged, so test files no longer import each other.

## Size estimate

Non-test, non-migration `src/` lines: models ~1, services ~8, views ~15 (close view ~12, round-page context ~3), urls ~1, template ~6; about 31 of 400. Actual, since `98977ef`: models 1, services 10, views 13, urls 1, template 2; 27 added and 0 removed.

## Open issues

- Resolved at checkpoint 3: the RND-2 and RND-3 no-form assertions were narrowed (listed above) and the route walk covers the close route.
- `README.md` still says closing rounds remain planned; the coordinator updates it (outside the builder's scope).
- RND-5 (retest link while Open) and RND-4 (results link) will add to the Open and Closed pages later; this slice adds no placeholders.

## Checklist

- [x] Checkpoint 1: specs and plan (`9952db3` spec, `7018b74` plan).
- [x] Checkpoint 2: closing time, migration, close service and tests (`9b09d53`). Red: 3 failed on the missing `closed_at` and `close`. Green: 285 rounds tests; full suite 481 passed, 1 skipped.
- [x] Checkpoint 3: route, round page and RND-6 tests (`55b103f`). Red: 20 failed on the missing route (404s). Mutations: without the lock both RND-6.4 race tests fail; without the Open re-check 5 tests fail. Green: full suite 579 passed, 1 skipped, 85 subtests.
- [x] Checkpoint 4: guides and status, the `race` helper moved to `conftest.py` and an order-independent route walk.
- [x] Full verification (579 passed, 1 skipped, 85 subtests passed; Ruff clean), size budget (27 of 400) and builder scope check.
