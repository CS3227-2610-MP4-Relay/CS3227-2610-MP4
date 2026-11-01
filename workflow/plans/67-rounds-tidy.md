# Rounds tidy (#67)

Remove duplicated round reads and stale text in `src/rounds/` without changing any observable behaviour.

## Scope and decisions

- High tier: touches workspace-isolation lookups and round-scoped link-table prefetches. Base `045c33c` (main), branch `67-rounds-tidy`. Behaviour-preserving refactor under existing criteria; no spec, criterion, template or test-expectation change. Budget: about 70 changed non-test source lines, well under 400. `src/ai/` is left to the AI-tidy slice.
- **F9 adopt.** `results.entry` raises `StateConflict(Conflict)` carrying the state display; `tester.result_entry` catches that subclass for `rounds/conflict.html` instead of comparing message text. `ai.feedback_views` catches the base class and still renders the same text.
- **F10 adopt.** `available_rounds` moves to `results.py`; `entry` uses it (with `select_for_update` on writes) and `tester.py` imports it by name, so `tester.available_rounds` and `rounds.results.workspace_records` patches still apply. `test_history.py`'s storage-failure case patches `rounds.tester.workspace_records`, which no longer exists there: only that target changes, to `rounds.results.workspace_records`, the same lookup.
- **F11 adopt.** One helper in `results.py`, `cases_with_current_builds(round_)`, prefetches round-scoped criteria and round-scoped builds newest first and sets `current_build`; used by `tester.detail` and `views.results_page`. Same three queries, so RND-4's query count holds. `show_round` is unchanged.
- **F15 adopt.** `tester_view` docstring states its layers (never_cache, 405, sign-in, role, 503) and why it logs without a traceback.
- **F12 adapt.** Docstrings only: `Refused` covers RND-2, RND-3.3 and RND-5 refusals; the lock comment names Draft for the RND-2 writes, with `publish`, `close` and `request_retest` stating their own state and `build_key` pure; `RoundNotOpen` says what happens (unreachable under the lock and re-check; `retest_round` maps it to 409, `close_round` does not). Whether `close_round` should catch it is a pending human decision, not changed here.
- **F14 adopt.** `form_page(request, form, title, button, round_=None)` serves all four rounds pages rendering `round_form.html`; new/edit round omit the round, so they keep the "Coordinator home" link (RND-1). `views.py` uses `services.` throughout. The AI drafting page stays inline.
- **F16 adopt.** Form `max_length`s read the model fields (all equal today: 120, 500, 120/2000/1000, 100, 2000); messages are built from the same value, so "Enter 1 to N characters." and "Enter at most 2000 characters." render unchanged.

## Commit checkpoints

1. **Plan:** this file. Checks: readback, `git diff --check`, builder scope.
2. **Result entry and tester reads (F9, F10, F11, F15)** — `refactor:`; `src/rounds/{results,tester,views}.py`, the one `test_history.py` patch target. Guards: `src/rounds/tests/test_{results,result_services,tester,history,review,routes}.py`, `src/relay/tests/test_access_matrix.py`, `src/ai/tests/test_feedback_views.py`, e2e `test_results.py`, `test_review.py`, `test_tester.py`.
3. **Coordinator views, forms, services docstrings (F12, F14, F16)** — `refactor:`; `src/rounds/{views,forms,result_forms,services}.py`. Guards: `src/rounds/tests/test_{views,records,forms,retest,publish,close,results,routes}.py`, e2e `test_rounds.py`, `test_round_lifecycle.py`.

Each implementation checkpoint: ruff check/format, focused tests, collection compared with the 2703-test baseline, then mutations restored from a copy and confirmed with `git diff --exit-code` on the mutated file.

## Mutations (each must fail a guard, then be restored)

- Helper: drop the `round=round_` filter on criteria, then on builds (cross-round link isolation in tester detail and results page).
- Helper: order builds oldest first (current build).
- F9: render the Closed `StateConflict` as `tester_result.html`; raise the base `Conflict` for the state check.
- F10: `available_rounds` includes Draft.
- F14: pass the round to new/edit round pages (Coordinator home link).
- F16: change one model-read limit by one (boundary tests).

## Status and next steps

- Existing passing tests are the regression evidence; a refactor has no missing behaviour to show red, so mutations stand in for red evidence.
- Database tests wait for the coordinator's go-ahead (shared test database). Full verification runs on the final candidate.
- Open: `close_round` not catching `RoundNotOpen` remains a human decision outside this slice.
