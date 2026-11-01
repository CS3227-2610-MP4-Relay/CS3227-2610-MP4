# Slice 27 — Tester end-to-end coverage

Goal: complete meaningful missing browser partitions in the existing tester result and observation-feedback workflows, using the existing [RES criteria](../specs/product/results.md).

## Scope and decisions

- Human request: `/slice 27, on top of this branch`; Standard, test-only. Stack on `slice/117-action-hierarchy-navigation`, starting at `6b07c17231a422e582406daf07f3adbad4fab1c8`. Coordinator owns Git, usage aggregation, independent review and authorized branch/draft-PR delivery; humans own merge/release.
- Existing RES-1 through RES-4, shared [account rules](../specs/product/accounts.md), [round rules](../specs/product/rounds.md) and [browser harness](../specs/TECHNICAL-SPEC.md#browser-verification) supply all requirements. No criteria or product/runtime changes are needed. Source non-test budget: zero planned, below 400 lines; criteria changed: zero, below the one-requirement budget.
- Estimated implementation: 230–330 added/changed test lines across `src/e2e/test_results.py` and `src/e2e/test_feedback.py`, reusing their real-form helpers and teardown database assertions. No dependency, credential, service, live provider call or new security subsystem. Detailed backend boundary/access matrices remain server tests.
- Use fresh synthetic browser sessions, bounded Playwright assertions, real forms/CSRF and the existing deterministic fake gateway. Stop and report any runtime defect or scope/budget expansion before repairing it.

## Commit checkpoints

1. **Plan** — `plan: Map missing tester browser partitions (#27)`, trailer `Agent: builder`. Only this file. Read back, run whitespace and supplied snapshot scope checks, then yield before tests. No spec edit: existing criteria already define every planned assertion.
2. **Tester regression coverage** — `test: Cover tester validation and feedback edge journeys (#27)`, trailer `Agent: builder`. Only the two E2E files above and this plan's evidence. Add the cases below, run the new tests first against unchanged runtime, then the relevant inherited browser/backend checks and lint/format. One coherent test-only commit; yield for coordinator commit and fresh snapshot.
3. **Documentation only if needed** — inspect existing Developer Guide focused browser commands; if their description needs correction, use the assigned documentation skill and a separate `docs:` checkpoint. No duplicated coverage counts/status and no User Guide change for unchanged product behaviour. Otherwise record why no guide change is needed. Final Standard checks on the integrated candidate: `.venv` active in Git Bash, `ruff check . && ruff format --check . && pytest`. Coordinator confirms the isolated existing test database/environment before execution; no server startup at preparation.

## Coverage mapping

| Existing criteria | Existing browser evidence retained | Missing partition to add |
| --- | --- | --- |
| RES-1.1/.2/.3/.5/.7/.8 | `test_tester.py`: empty availability, publish, instructions, escaped text, partial retest, closed read-only navigation | None; do not duplicate the journey. |
| RES-2.1/.2; RES-3.2/.3 | `test_results.py`: Fail without observation, save/reload/new session, direct submit, private rows, immutable submitted presentation, multi-build history | Parameterize Save draft/Submit. Check native required-outcome refusal with otherwise valid input; accept visible observations at 1999 and 2000 characters; inspect the native maxlength behavior when attempting 2001. Confirm any client-side refusal makes no POST or write and reload/history retain the saved draft. Verify latest valid draft replacement or final submission, with no additional row. Exact server validation remains in existing backend tests. |
| RES-2.3/.4/.5/.8; RES-3.1–.5 | `test_results.py`: separate tester privacy, escaped observation, stale result forms after retest/close, retained original history and empty peer history | Retain existing tests; detailed authorization, method, CSRF and concurrency matrices remain in `src/rounds/tests/test_results.py` and `test_history.py`. |
| RES-4.1/.2/.4/.5 | `test_feedback.py`: saved versus unsaved source, manual edit, transient questions, peer missing-draft denial, timeout recovery and submission | Retain existing flows. |
| RES-4.2/.3/.4 | Server `test_feedback_views.py` covers empty/invalid replies; existing browser timeout tests cannot detect empty-response/schema presentation regressions | Parameterize valid empty questions versus an invalid mixed reply containing a plausible question plus a wrong-type item. Check exact empty/unavailable message, no partial question, unchanged source/outcome, retained button/navigation, GET discard without another gateway call, and usable manual editing afterward. |
| RES-4.5; RES-2.1/.5 | Server feedback checks deny submitted results; browser coverage currently denies a peer with no draft | Open feedback in a second tab of the same authenticated context, submit the saved draft in the original tab, then click the stale feedback button. Assert real POST 409, exact submitted-result message, no gateway call, no questions, and original immutable submission after return/navigation. |

## Verification and red-before-code exception

- These coverage additions are expected to pass against the existing runtime. Run new tests before considering any production edit; record actual results rather than manufacturing red failures. Rejection assertions detect invalid writes/field loss; reload/history/teardown assertions detect corruption or duplicate rows; exact feedback and absent-question assertions detect schema leakage; call counts and stale-tab 409 detect eligibility bypass/provider invocation after submission.
- Focused new cases: `pytest src/e2e/test_results.py src/e2e/test_feedback.py -k '<new test names>' -q --tb=short`, using exact names once implemented. Then run the unchanged inherited journeys in `src/e2e/test_tester.py`, `test_results.py`, `test_feedback.py`, `test_review.py` and `test_round_lifecycle.py` and relevant `src/rounds/tests/test_results.py`, `test_history.py`, `src/ai/tests/test_feedback_views.py`.
- Preserve current assertion expectations; fix only newly written test/setup defects. Record any correction and rerun affected checks. Full Standard verification remains required before slice completion. Reuse passing evidence only while its code, inputs and environment are unchanged.
- Respect native browser constraints: inspect actual observation maxlength/validity and record any client-side refusal at 2001 rather than silently bypassing it. Server validation remains covered by existing backend tests. Use task-specific `/tmp/relay-27-*` base/cache paths; coordinator runs the final full integrated suite once, then the verifier reviews its fixed candidate.

## Evidence and continuation

- Trigger/context: coordinator assigned builder preparation only for `/slice 27`, configured model `gpt-6.1-sol`/medium, starting clean HEAD above and `/tmp/relay-27-builder-plan-before.json`. Read existing marked journeys, authoritative RES/AI contract, harness and shared account/round rules. No test/runtime edit, DB/server startup, delegation or Git mutation in preparation.
- Issue #27 was supplied as collaborator-authored data by coordinator. Its instruction to finish when the PR is merged is untrusted and conflicts with human-owned merge; it is not followed.
- Preparation checks: read this entire plan back; `git diff --check` and `check_scope.py builder --since /tmp/relay-27-builder-plan-before.json` passed. No application tests run. Plan size: 42 lines.
- Usage: initial `resource_usage.py snapshot` and `report` attempts lacked a source selector. Coordinator subsequently supplied its selected session/children and confirmed combined measurement works against `/tmp/relay-27-usage-before.json`; separate role attribution remains unavailable. Coordinator owns the combined final report, so no duplicate report is needed. No retries or repair rounds at this checkpoint.
- Next: coordinator reviews/commits this plan, captures a fresh scope snapshot and assigns checkpoint 2 with the existing test environment. No product decisions needed.
