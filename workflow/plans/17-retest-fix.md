# Slice 17: Retest a fix

Goal: prove that a tester can submit a new result for a coordinator-selected retest while preserving earlier results and cases outside that retest.

## Scope and decisions

- Request: `/slice 17`, tester "Retest a fix"; Standard tier. Existing requirements suffice; no new RES requirement or criterion change.
- Spec mapping: [RES-1.3](../specs/product/results.md#res-1-see-the-tests-available-to-me) covers the latest covering build; [RES-2.1, RES-2.4 and RES-2.5](../specs/product/results.md#res-2-save-and-submit-an-outcome-with-observations) cover fresh entries, separate immutable submissions and unchanged unselected entries; [RES-3.2 and RES-3.3](../specs/product/results.md#res-3-review-my-earlier-results) cover original context/history; [RND-5.1 and RND-5.5](../specs/product/rounds.md#rnd-5-request-a-retest) cover coordinator selection and repeated retests.
- Initial inspection finds the capability in `src/rounds/results.py` and `tester.py`. Existing browser history coverage submits Pass after an original draft, rather than after a submitted Fail. Extend it instead of adding a duplicate journey.
- `src/rounds/tests/test_tester.py` already covers repeated/overlapping labels with an untouched third case. Extend result lifecycle coverage only for the distinct persistence/entry gap across those selections.
- Budget: at most one changed criterion and 400 non-test/migration source lines; expected changes are tests and a short User Guide clarification. No dependencies, services, schema, authorization or recovery changes.

## Commit checkpoints

1. **Plan and existing-spec mapping** — this file only. Inspect relevant specs and tests; yield before implementation. Specs remain unchanged because the requested behavior is already specified.
2. **Retest lifecycle regression coverage** — extend `src/e2e/test_results.py`'s existing private-history journey to submit an original Fail and a fresh Pass on a selected new build, checking empty entry fields, build-associated outcomes, preserved submission/history and unchanged unselected content. Preserve draft and tester-isolation assertions. Extend `src/rounds/tests/test_result_services.py`'s existing retest test for repeated/overlapping selected cases, immutable old row fields/timestamps, fresh entries and unchanged unselected rows. Add production repair only if these expose an existing-criterion defect, keeping its regression together. Before any repair, run the focused tests; if already passing, record that this is missing integration evidence for existing behavior, with assertions capable of detecting result copying/overwriting or selecting a round-wide build. Focused checks: `ruff check` and `ruff format --check` on changed tests; `pytest src/rounds/tests/test_result_services.py src/e2e/test_results.py`. Yield for coordinator commit.
3. **Guide and final verification** — clarify `docs/UserGuide.md`'s existing result/retest paragraph: selected new builds start empty and accept a new outcome after testing the fix; earlier submissions remain in My results. Follow the maintain-docs skill when assigned. Read the section back. Run root verification with `.venv` active: `ruff check . && ruff format --check . && pytest`. Record exact outcomes and yield the integrated candidate for independent review.

## Handoff and next step

- Trigger/context: coordinator-assigned builder for issue #17; clean starting HEAD `a435cf296b39031297796672193958e61d420c86`, branch `feat/17-retest-fix`; trusted scope and relevant paths supplied by coordinator. No Git mutations or delegation by builder.
- Checkpoint 1: spec/code inspection only; no behavior checks run and no production defect established. This plan records spec-before-code evidence.
- Open issues/decisions: none. Next: coordinator scope-checks and commits this checkpoint, then supplies a fresh snapshot and assigns checkpoint 2.
- Usage: private session baseline selected by `CODEX_THREAD_ID`-matched file under the explicit `2026/10/29` session root, outside the repository; report exact measured availability in the role handoff. Effective model/effort unavailable unless runtime evidence supplies them.
