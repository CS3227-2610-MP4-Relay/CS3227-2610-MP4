# Slice 157: result conflict navigation

Give authorized testers a route from result-entry conflicts back to their round or home ([PLT-4.14](../specs/product/platform.md#plt-4-shared-application-presentation)).

Why: A stale result submission correctly returns 409, but reloading the same URL cannot reach the current build and the refusal page currently offers no navigation.

## Scope and decisions

- Standard tier; PLT-4 is the single changed requirement, with PLT-4.7 clarified for this error-page exception and PLT-4.14 defining its navigation. Preserve RES-2.3–2.8 and existing access controls. Budget: at most 400 non-test source lines; aim for at most eight changed criteria.
- Only result-entry conflicts gain navigation. Preserve exact messages, 409 status, no-store, authorization precedence, write serialization and stored rows. No rejected-edit retention, automatic recovery, new service, credential or dependency.
- Shared renderer changes require independent verifier and security-reviewer reports on the coordinator's fixed candidate. Builder does not delegate or change Git state.

## Commit checkpoints

1. `spec: Define result conflict navigation (#157)` — product/platform.md and this plan. Read back changed sections and run builder scope/diff checks. Yield before implementation.
2. `fix: Add navigation to result entry conflicts (#157)` — src/rounds/tester.py, views.py, templates/rounds/conflict.html, src/rounds/tests/test_results.py, src/e2e/test_results.py and docs/UserGuide.md; adjust only these paths unless a necessary in-scope helper is identified. First add criterion-marked server/browser regressions and record missing-navigation failures before implementation. Then pass optional authorized navigation context to the shared renderer, reuse existing link styling, and document built labels through the maintain-docs skill. Yield with focused checks and full Standard verification.

## Verification and next steps

- Server: exercise stale/Closed GET and POST plus submitted POST; check exact destinations and single links, unchanged messages/status/cache headers and unchanged domain rows. Keep denied access fixed and other shared conflict callers unchanged.
- Browser: update the existing retest/close journey to leave each conflict using visible controls, reach the current build after retest, and return to the Closed round/home after closure. Do not use page.goto to recover from conflicts. Existing harness covers preserved earlier/unselected results; retain those assertions.
- Run focused result server and browser checks red before green, then `ruff check . && ruff format --check . && pytest` in the configured test environment. Record actual commands, results and environment limitations; no live provider calls.
- Initial candidate: f8adaad43506733793df05371dce01ecdb7c55f3, coordinator scope snapshot `%TEMP%/relay-157-builder-plan.json`. Trigger: coordinator's /slice 157 assignment; model identifier unavailable in runtime. Supplied context: confirmed narrow scope, relevant criteria, paths, tier and commit checkpoints.
- Specs/plan committed by coordinator as 686e373b8083ae88edc742a4b7ceb42f1ca53fa3; implementation authorized against `%TEMP%/relay-157-builder-code.json`. No open product decision. Builder-local usage baseline unavailable: resource_usage.py requires an explicit session JSONL source that has not been supplied; do not count missing usage as zero. Coordinator reports its 13:26:09 UTC baseline includes descendant discovery. Test environment: PostgreSQL 17 at 127.0.0.1:55432 with relay_test role/database, installed Chromium, Python 3.14.2 and root .venv. No concurrent suites or escalation used.

## Implementation evidence

- All pytest commands below ran from this worktree in Git Bash after `source /c/Users/limbe/Documents/GitHub/CS3227-2610-MP4/.venv/Scripts/activate`.
- Before production edits, the focused `test_conflicts_precede_invalid_form_and_preserve_rows` matrix failed in six cases because the expected Tester home link count was zero. The selection command was `pytest -q src/rounds/tests/test_results.py -k "conflicts_precede_invalid_form or shared_conflict_without_entry_context" src/e2e/test_results.py -k "conflicts_precede_invalid_form or shared_conflict_without_entry_context or selected_retest_and_close"`; actual output: 6 failed, 81 deselected in 4.00s.
- Explicit red browser/default-renderer check: `pytest -q src/e2e/test_results.py::test_selected_retest_and_close_refuse_stale_forms_preserving_results src/rounds/tests/test_results.py::test_shared_conflict_without_entry_context_keeps_existing_actions` -> 1 failed, 1 passed in 20.89s. Browser reached the real stale POST 409, then found zero Tester home links. The unchanged shared-renderer case passed as expected.
- After implementation, `pytest -q src/rounds/tests/test_results.py src/e2e/test_results.py::test_selected_retest_and_close_refuse_stale_forms_preserving_results` -> 88 passed in 26.54s. PLT-4.14 server coverage checks all three conflict reasons, Closed/stale GET and POST, exact single destinations before the error, no form, no-store and unchanged rows. Existing denial and result behavior checks pass. The browser follows links from both refusals and retains original, unselected and current drafts.
- Implementation only passes a reversed round URL after existing entry conflict checks; shared renderer includes existing page_navigation only when that optional destination exists. UserGuide updated using maintain-docs and read back against code/spec labels; existing section links retained. AGENTS.md edit refused as outside builder writes without mutation; native hook enforcement unverified.
- Full Standard command: `ruff check . && ruff format --check . && pytest` with the activation above -> lint passed, format check passed (147 files), 2999 passed and 5 skipped in 1361.48s. Skips concern unavailable pwsh, the POSIX hook on Windows, two Windows symlink-rights exclusions and an unavailable directory symlink; default pytest output did not include the latter's exact OS error.

## Independent review and delivery

- Frozen candidate: HEAD 686e373b8083ae88edc742a4b7ceb42f1ca53fa3 plus the implementation diff in `%TEMP%/relay-157-review.json`, against base f8adaad43506733793df05371dce01ecdb7c55f3. Reviews ran while the unchanged full suite finished; all tracked files, including this plan, stayed fixed until both reviews ended. Coordinator snapshot comparison and all role scope checks passed.
- Verifier and security-reviewer independently inspected the changed source/tests and relevant criteria; neither reported findings or requested repairs. Security review covered authorization before navigation, internal destinations/escaping, unchanged writes/cache/status and shared callers. They did not repeat database/browser tests; the verifier received the final passing full-suite evidence. Native hook enforcement and hosted runtime security were not established by this review.
- Production diff: 12 additions and 4 deletions across three files; one requirement changed. No review repair rounds. Only this evidence summary and the session log changed after candidate review; passing code/test evidence remains applicable.
- Normal slice authorization covers feature-branch push and a draft PR; its current-head checks record hosted validation. Human log review, merge and release remain pending. Session details and measured usage: [log](../../logs/Whimsyturtle/044-add-result-conflict-navigation.md).
