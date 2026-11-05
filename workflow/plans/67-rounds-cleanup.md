# 67: Rounds cleanup

Goal: remove duplicated conflict pages, round-scoped queries and template fragments in the rounds app, behaviour-preserving, under issue #67.

Tier: High (touches round- and workspace-isolation query constraints). Base `ebd890c`. Budget: 400 non-test `src/` lines. No spec changes, dependencies or new behaviour.

## Confirmed items

- **R1** One 409 conflict page: `rounds/conflict.html` takes the message; `state_conflict`, `tester.result_entry` and `ai.feedback_views.feedback_page` render it. Delete the Closed string comparison in `result_entry` and the conflict branches of `tester_result.html` and `ai/feedback.html`. Keep 404-before-409, every message, status and the `Action not available` title. Move "Save a draft before requesting feedback." into a `feedback_views` module constant.
- **R2** Shared round-scoped reads: one helper for a round's cases with round-limited criteria and their current build (`-id` builds prefetch), one for results covered in a round (`case__round`, `build__round`, `build__cases=F("case_id")`). They go in `rounds/results.py` and are used by `views.results_page`, `tester.detail` and `tester.history`. Query counts and ordering stay the same. Optionally flatten the `result_action` ternary.
- **R6 (rounds)** Correct the `services.py` docstrings: the "every function below is Draft" comment (it does not cover `build_key`, `publish`, `close` and `request_retest`), and the `Refused` docstring (publish RND-3.3 and retest RND-5 also raise it).
- **R7** Use `services.create_round`/`services.RoundLimitReached` in `views.py`. Have `record_form` and `retest_round` call `form_page`. Give the results page an explicit flag in `contents_links.html`. Move the PLT-4.13 observation placeholder into one include, used by `result_lines.html`, `tester_history.html`, `tester_result.html` and `ai/feedback.html`, with the same `isolated_lines` escaping.
- **A11** `page_navigation.html` picks Tester home or Coordinator home from `user.role` (auth context processor) instead of a `tester` flag. Drop the four `tester=True` flags (`tester_round`, `tester_history`, `tester_result`, `ai/feedback`). The sweep said five; there are four.

## Commit checkpoints

1. `plan: Plan rounds cleanup (#67)`: this file.
2. `refactor: Render one conflict page (#67)`: `rounds/templates/rounds/conflict.html`, `rounds/views.py` (`state_conflict`), `rounds/tester.py`, `rounds/templates/rounds/tester_result.html`, `ai/feedback_views.py`, `ai/templates/ai/feedback.html`. Focused checks: `src/rounds/tests`, `src/ai/tests/test_feedback_views.py`, `src/relay/tests/test_access_matrix.py`, plus the e2e modules that assert conflicts (`test_results`, `test_feedback`, `test_round_lifecycle`). Mutation: change the message variable in `conflict.html` and confirm `test_conflicts_precede_invalid_form_and_preserve_rows` fails.
3. `refactor: Share round-scoped result queries (#67)`: `rounds/results.py`, `rounds/views.py`, `rounds/tester.py`. Focused checks: `src/rounds/tests`, the access matrix, and the e2e review, results and history modules. Mutation: drop each filter term in the covered-results helper and name a failing isolation test for each.
4. `refactor: Tidy round templates and views (#67)`: `rounds/views.py`, `rounds/services.py`, `rounds/templates/rounds/{contents_links,results,result_lines,tester_history,tester_result,tester_round}.html`, a new observation include, `relay/templates/page_navigation.html`, `ai/templates/ai/feedback.html`. Focused checks: `src/rounds/tests`, `src/ai/tests/test_feedback_views.py`, the access matrix, and the e2e navigation, presentation and feedback modules. Mutations: swap the role test in `page_navigation.html`, and drop `isolated_lines` from the observation include.
5. Final: full verification, then record the result here.

## Decisions

- Helpers go in `rounds/results.py`. It already imports only models and `accounts`, so `views.py` and `tester.py` can import it without a cycle.
- For the A11 role check I'll compare against the stored value `"tester"`. I won't add an accounts helper, because `accounts/` is outside this slice's paths.
- The feedback 409 page now renders `conflict.html`, so it drops the inert `pending_forms` script; there is no form on that page for it to act on. The orchestrator accepted this (option a). No test asserts the script on a 409 page.
- `conflict_page(request, message)` lives in `rounds/views.py` beside `state_conflict`. `tester.py` and `ai/feedback_views.py` import it from there. The state refusal text has one home, `results.state_message(round_)`.

## Review

- Candidate `1956c09`: the verifier found no High or Medium findings, and the security reviewer found nothing.
- Informational notes, none requiring a change:
  - the new `case__round` regression test covers only the tester history page;
  - `conflict.html` autoescapes its message but does not isolate its direction, and every message it shows is fixed text;
  - `page_navigation.html` compares the role with the literal `"tester"`;
  - the wording at TECHNICAL-SPEC lines 118 and 122 is still accurate;
  - templates rendered without a request (unit renders) now show "Coordinator home".
- Repair round 1: the `rounds/results.py` module docstring now covers the round-scoped reads, and the checkpoint 4 path list no longer names `contents.html`, which the candidate never changed.
- Verifier and security recheck of `1956c09..db6bc7e`: Lows 1 and 3 resolved; security assessment unchanged. Accepted as is: commit `1956c09` combines R7, A11 and R6 as planned in checkpoint 4 (no history rewrite; for the human reviewer to judge), and the `results.py` docstring names the review and history pages but not the tester round page, which also uses the read helpers.

## Progress

- Checkpoint 1: plan written; no checks run.
- Checkpoint 2 (R1): 7 non-test `src` files, +25/-30. `ruff check .` and `ruff format --check .` pass. Through dblock: `src/rounds/tests`, `src/ai/tests/test_feedback_views.py`, `src/ai/tests/test_views.py` and `src/relay/tests/test_access_matrix.py` gave 1777 passed; e2e `test_results`, `test_feedback` and `test_round_lifecycle` gave 16 passed. Mutation (`{{ message }}` changed to `{{ state }}` in `conflict.html`, then reverted): 25 failures, including `test_results.py::test_conflicts_precede_invalid_form_and_preserve_rows` (6), `test_feedback_views.py::test_eligibility_refusals_make_no_call` (8) and `::test_changes_during_call_discard_success_and_failure` (8), and three `test_close.py` 409 tests.
- Checkpoint 2 rerun after the session restart (2026-11-05, same code, after the orchestrator restarted `relay-test-db`): the focused set plus e2e `test_results`, `test_feedback` and `test_round_lifecycle` gave 1793 passed in 127.24s. The backed-up conflict-page mutation gave 25 failed, 72 passed, with the same named tests; the file was restored and `cmp` matched the backup.
- Checkpoint 3 (R2): `rounds/results.py` gains `cases_with_current_build(round_)` and `covered_results(round_)`; `views.results_page`, `tester.detail` and `tester.history` use them, the `result_action` ternary is flattened, and unused imports are removed. Non-test `src` +48/-48 across 3 files. A new regression test, `test_history.py::test_forged_coverage_of_another_rounds_case_stays_hidden` (RES-3.4), covers the `case__round` term, which no existing test caught. Dropping that term survived `src/rounds/tests src/relay/tests src/accounts/tests` (2016 passed). The new test passes, and fails with the term dropped. `ruff check .` and `ruff format --check .` pass. Through dblock: `src/rounds/tests src/relay/tests/test_access_matrix.py src/e2e/test_review.py src/e2e/test_results.py src/e2e/test_navigation.py` gave 1672 passed; this includes the query-count test `test_review.py::test_query_count_does_not_grow_with_cases_or_results`. Mutations (each backed up and restored with `cmp`), run against test_review, test_history and test_tester:
  - dropping `build__round` fails `test_review.py::test_drafts_and_rows_outside_the_rounds_covering_builds_never_appear`;
  - dropping `build__cases` fails that test and `test_history.py::test_owner_round_and_coverage_scope_ignores_forged_selectors`;
  - removing the round limit on the builds prefetch fails `test_tester.py::test_malformed_related_links_do_not_disclose_other_rounds` (2) and the review test;
  - removing the round limit on the criteria prefetch fails the same tests.
- Checkpoint 4 (R7, A11, R6):
  - R7: `views.py` calls `services.create_round` and `services.RoundLimitReached`, and `record_form` and `retest_round` use `form_page`; `results.html` passes `results_contents=True`, which `contents_links.html` checks explicitly; the new include `rounds/observation.html` (no trailing newline, so the markup is byte-identical) is used in `result_lines`, `tester_history`, `tester_result` and `ai/feedback`.
  - A11: `page_navigation.html` checks `user.role == "tester"`, and the four `tester=True` flags are gone.
  - R6: the `Refused` docstring and the comment above the criterion and case writes in `services.py` are corrected.
  - Checks: `ruff check .` and `ruff format --check .` pass. Through dblock: `src/rounds/tests`, `src/ai/tests/test_feedback_views.py`, `src/ai/tests/test_views.py`, `src/relay/tests/test_access_matrix.py` and e2e `test_navigation`, `test_presentation`, `test_feedback`, `test_review`, `test_results` and `test_drafting` gave 1831 passed.
  - Mutations (each backed up and restored with `cmp`):
    - Changing the role test to `"coordinator"` fails `e2e/test_navigation.py::test_contents_reveal_records_and_keyboard_defaults` (8) and `e2e/test_tester.py::test_tester_reads_published_retested_and_closed_round`.
    - Dropping `isolated_lines` from the observation include fails 14 tests, including `test_history.py::test_only_system_observation_placeholders_are_italic` (4) and `test_review.py::test_user_text_is_escaped_and_each_line_isolated`.
    - Renaming the results branch flag fails `test_review.py::test_user_text_is_escaped_and_each_line_isolated` and `e2e/test_navigation.py::test_contents_reveal_records_and_keyboard_defaults` (2).
- Final: with `PATH` extended as instructed, `ruff check . && ruff format --check . && <dblock> pytest -q -p no:cacheprovider` gave 2858 passed and 254 subtests passed in 216.14s: the base's 2857 plus the new history regression test.
- Rerun after the reboot (2026-11-05, same code, new working folder `/Users/zheng/Desktop/mp4/.r67/`): all eight mutations reproduced the results above, each backed up and restored with `cmp`. Dropping `case__round` now fails only the new `test_forged_coverage_of_another_rounds_case_stays_hidden`. Full verification gave 2858 passed and 254 subtests passed in 284.11s, exit 0.
