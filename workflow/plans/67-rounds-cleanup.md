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
4. `refactor: Tidy round templates and views (#67)`: `rounds/views.py`, `rounds/services.py`, `rounds/templates/rounds/{contents_links,contents,results,result_lines,tester_history,tester_result,tester_round}.html`, a new observation include, `relay/templates/page_navigation.html`, `ai/templates/ai/feedback.html`. Focused checks: `src/rounds/tests`, `src/ai/tests/test_feedback_views.py`, the access matrix, and the e2e navigation, presentation and feedback modules. Mutations: swap the role test in `page_navigation.html`, and drop `isolated_lines` from the observation include.
5. Final: full verification, then record the result here.

## Decisions

- Helpers go in `rounds/results.py`. It already imports only models and `accounts`, so `views.py` and `tester.py` can import it without a cycle.
- For the A11 role check I'll compare against the stored value `"tester"`. I won't add an accounts helper, because `accounts/` is outside this slice's paths.
- Open (for the orchestrator): `ai/feedback.html`'s conflict branch currently inherits the `pending_forms` script block. `conflict.html` does not, so the feedback 409 page would lose an inert script that has no form to act on. I recommend accepting that, since the page behaves the same. The alternative is to keep a feedback-specific conflict template, which defeats R1.

## Progress

- Checkpoint 1: plan written; no checks run.
