# Rounds tidy (#67)

Remove duplicated round reads and stale text in `src/rounds/` without changing any observable behaviour.

## Scope and decisions

- High tier: touches workspace-isolation lookups and round-scoped link-table prefetches. Base `045c33c` (main), branch `67-rounds-tidy`. Behaviour-preserving refactor under existing criteria; no spec, criterion or template change; no existing expectation removed or weakened; template and link assertions added to two existing tests. Budget: 400 changed non-test source lines for the slice; actual +95/−75 at `10ea124`, +100/−76 after review round 1, measured with the slice skill's `git diff --shortstat` exclusions (the sweep's rough estimate was about 70). `src/ai/` is left to the AI-tidy slice.
- **F9 adopt.** `results.entry` raises `StateConflict(Conflict)` carrying the state display; `tester.result_entry` catches that subclass for `rounds/conflict.html` instead of comparing message text. `ai.feedback_views` catches the base class and still renders the same text.
- **F10 adopt.** `available_rounds` moves to `results.py`; `entry` uses it (with `select_for_update` on writes) and `tester.py` imports it by name, so `tester.available_rounds` and `rounds.results.workspace_records` patches still apply. `test_history.py`'s storage-failure case patches `rounds.tester.workspace_records`, which no longer exists there: only that target changes, to `rounds.results.workspace_records`, the same lookup.
- **F11 adopt.** One helper in `results.py`, `cases_with_current_builds(round_)`, prefetches round-scoped criteria and round-scoped builds newest first and sets `current_build`; used by `tester.detail` and `views.results_page`. Same three queries, so RND-4's query count holds. `show_round` is unchanged.
- **F15 adopt.** `tester_view` docstring states its layers (never_cache, 405, sign-in, role, 503) and why it logs without a traceback.
- **F12 adapt.** Docstrings only: `Refused` covers RND-2, RND-3.3 and RND-5 refusals; the lock comment names Draft for the RND-2 writes, with `publish`, `close` and `request_retest` stating their own state and `build_key` pure; `RoundNotOpen` says what happens (unreachable under the lock and re-check; `retest_round` maps it to 409, `close_round` does not). Whether `close_round` should catch it is a pending human decision, not changed here.
- **F14 adopt.** `form_page(request, form, title, button, round_=None)` serves all four rounds pages rendering `round_form.html`; new/edit round omit the round, so they keep the "Coordinator home" link (RND-1). `views.py` uses `services.` throughout. The AI drafting page stays inline.
- **F16 adopt.** Form `max_length`s read the model fields (all equal today: 120, 500, 120/2000/1000, 100, 2000); messages are built from the same value, so "Enter 1 to N characters." and "Enter at most 2000 characters." render unchanged.

## Commit checkpoints

1. [x] **Plan** (`68af695`): this file. Checks: readback, `git diff --check`, builder scope.
2. [x] **Result entry and tester reads (F9, F10, F11, F15)** (`ab51510`) — `refactor:`; `src/rounds/{results,tester,views}.py`, the one `test_history.py` patch target, two template assertions in `test_results.py`. Guards: `src/rounds/tests/test_{results,result_services,tester,history,review,routes}.py`, `src/relay/tests/test_access_matrix.py`, `src/ai/tests/test_feedback_views.py`, e2e `test_results.py`, `test_review.py`, `test_tester.py`.
3. [x] **Coordinator views, forms, services docstrings (F12, F14, F16)** (`8f032db`) — `refactor:`; `src/rounds/{views,forms,result_forms,services}.py`. Guards: `src/rounds/tests/test_{views,records,forms,retest,publish,close,results,routes}.py`, e2e `test_rounds.py`, `test_round_lifecycle.py`.
4. [ ] **Final review and draft PR:** coordinator; verifier and security review of the integrated candidate.

Each implementation checkpoint: ruff check/format, focused tests, collection compared with the 2703-test baseline, then mutations restored from a copy and confirmed by matching the candidate's file hashes (the candidate is uncommitted while mutating).

## Mutations (each must fail a guard, then be restored)

- Helper: drop the `round=round_` filter on criteria, then on builds (cross-round link isolation in tester detail and results page).
- Helper: order builds oldest first (current build).
- F9: render the Closed `StateConflict` as `tester_result.html`; raise the base `Conflict` for the state check.
- F10: `available_rounds` includes Draft.
- F14: pass the round to new/edit round pages (Coordinator home link).
- F16: change one model-read limit by one (boundary tests).

## Evidence

- Existing passing tests are the regression evidence; a refactor has no missing behaviour to show red, so mutations stand in for red evidence. Collection matched the 2703-test baseline after each checkpoint; ruff check/format passed.
- **Checkpoint 2:** guards 1030 passed; e2e `test_results`, `test_review`, `test_tester`, `test_feedback` 7 passed. Mutations caught: criteria or builds unscoped (`test_tester.py::test_malformed_related_links_do_not_disclose_other_rounds`), builds oldest first (`test_results.py::test_links_follow_each_current_build_and_disappear_on_close`), Draft available (`test_results.py::test_missing_foreign_and_cross_round_ids_are_fixed_404[get-draft]`).
- **Test addition:** both F9 mutations first survived all 1030 guards, because `tester_result.html`'s conflict branch renders the same title and heading as `conflict.html`, so no test pinned the template TECHNICAL-SPEC requires for state conflicts. `test_conflicts_precede_invalid_form_and_preserve_rows` now also asserts the template on its POST and GET (conflict page for Closed, entry page for stale/submitted). It passed on the pre-refactor code, so it pins existing, specified behaviour; with it, both F9 mutations fail. No existing assertion changed.
- **Checkpoint 3:** guards (rounds view/form/record/lifecycle/service tests, `src/ai/tests`, e2e `test_rounds`, `test_round_lifecycle`, `test_drafting`) 1256 passed. Mutations caught: edit-round GET or new round given a round (`test_views.py` Coordinator home link), record or retest page without its round (`test_records.py`, `test_retest.py` Back to round link), each of the seven model-read limits off by one (`test_views`, `test_records`, `test_retest`, `test_results` boundary tests). F12 is docstrings only. `form_page` takes no `**extra`: no rounds caller needs one.
- Gap found: no test checked the Coordinator home link on an invalid edit-round POST re-render (mutation survived); closed in review round 1.

## Review round 1

- Candidate `045c33c..10ea124`. Verifier: 0 High, 0 Medium, 3 Low, 2 Nit, 2 Info. Security reviewer: 0 High, 0 Medium, 0 Low, 1 Nit, 1 Info.
- Fixed: `test_invalid_title_is_refused_next_to_the_field` now asserts the "Coordinator home" link and no "Back to round" on both re-renders; passing the round on the invalid edit-round re-render now fails all 9 retitle cases; `cases_with_current_builds` states `round_` must already be authorized; `results.py` module docstring and the Developer Guide line name the shared round reads; `limit` and `build_label` docstrings drop the one-home claim and the hard-coded 100; this plan records actual size, test additions and final results.
- Security Info: under the unscoped-criteria and unscoped-builds mutations, `test_review.py::test_drafts_and_rows_outside_the_rounds_covering_builds_never_appear` fails under each, so tester detail and the results page are guarded independently (with `test_tester.py::test_malformed_related_links_do_not_disclose_other_rounds`).
- Lesson (Low 3): checkpoint 3 bundled view, form and docstring changes in one commit; split such units by purpose next time.

## Status and next steps

- Final full verification at `10ea124`'s code: `ruff check .` clean; `ruff format --check .` 129 files formatted; `pytest` 2703 passed, 231 subtests passed.
- After review round 1 repairs: `test_views`, `test_review`, `test_tester` 203 passed; full verification again clean, 129 files formatted, 2703 passed, 231 subtests passed.
- The coordinator owns the draft PR.
- Open: `close_round` not catching `RoundNotOpen` remains a human decision outside this slice.
