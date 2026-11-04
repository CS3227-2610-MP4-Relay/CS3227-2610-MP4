# #67 browser test helpers

Goal: share browser test helpers without cross-test imports, drop unasserted review screenshots and use exact single-link locators, with no product change.

Tier: Standard (test-only; verifier review). Base: `ebd890c`. Paths: `src/e2e/**` and this plan. Budget: no non-test `src/` lines; test count stays 68 browser tests (2857 passed, 254 subtests in full suite).

## Confirmed items

- **T5 duplicated helpers.** Re-checked at base: seven identical sign-in bodies (`sign_in` in test_feedback, test_results, test_presentation, test_review, test_tester; `sign_in_coordinator` in test_round_lifecycle, test_rounds); four second contexts repeating the conftest timeouts (test_results `context`, test_review `session`, inline in test_feedback and test_tester); identical tester2 `browser_accounts` override in test_results and test_review; test_navigation, test_feedback and test_rounds import from `e2e.test_presentation`, test_drafting from `e2e.test_rounds`. A scratch collection plugin listed both `test_presentation` and `e2e.test_presentation`, and both `test_rounds` and `e2e.test_rounds`, in `sys.modules`.
- **T6 review screenshots.** 12 `screenshot(...)` calls to the system temp folder with fixed names (test_presentation x9, test_navigation x2, test_feedback x1); return values unused, so no assertion depends on them.
- **T7 `.last` on single links.** PLT-4.7: result-entry and AI pages show each home/back destination once. `rounds/tester_result.html` (draft and submitted) and `ai/feedback.html` render one back link through `page_navigation.html`, so test_feedback's three "Back to result" sites and test_results' two "Back to round" sites (draft entry, entry after Save/Submit) take an exact locator. Other `.last` uses are outside the confirmed items.

## Checkpoints

1. Plan: this file.
2. T5: new `src/e2e/sessions.py` (`sign_in(page, accounts, role)`, `separate_context(page, live_server)` and the harness timeouts it shares with `conftest.py`, `second_tester_accounts(accounts)` generator used by thin `browser_accounts` overrides in test_results and test_review); new `src/e2e/presentation.py` with `contrast`, `assert_contrast`, `assert_layout`, `assert_action_link_states` moved from test_presentation. Update the 9 test modules and conftest. Checks: collection plugin shows each test module once; `pytest --collect-only -q src/e2e` still 68; dblock run of the affected modules; mutation of `second_tester_accounts`' row check fails a test_results test.
3. T6: delete the 12 screenshot calls and unused `Path`/`gettempdir` imports in test_presentation, test_navigation, test_feedback. Checks: `grep screenshot src/e2e` shows only conftest's failure capture; dblock run of the three modules.
4. T7: replace `.last.click()` with `.click()` at the five sites. Checks: dblock run of test_feedback and test_results; scratch duplicate of the back link in `page_navigation.html` makes a tightened test fail on strict mode, then reverted.
5. Final: `ruff check . && ruff format --check . && <dblock> pytest -q -p no:cacheprovider`.

## Decisions

- Helpers go in plain non-test modules (pattern of `pending.py`, `disclosures.py`), not conftest fixtures, because callers pass different pages and roles; the tester2 override stays a per-module `browser_accounts` fixture so the page fixture still tears down before its row check.
- The two no-JavaScript contexts (test_drafting, test_feedback) do not set bounded waits today; they stay unchanged since they are outside T5's confirmed list.

## Open items

- Scope hook does not run in this worktree (orchestrator holding the fix for the human); scope checked post hoc per checkpoint.

## Results

- Checkpoint 1: plan written; collection at base: 68 tests, duplicate module loads as above.
- Checkpoint 2: `sessions.py` (`bounded`, `separate_context`, `sign_in`, `second_tester_accounts`) and `presentation.py` added; conftest uses `bounded`; `sign_in_coordinator(p, a)` calls became `sign_in(p, a, "coordinator")`. Collection: 68 tests, each test module loaded once (no `e2e.test_*`). dblock `pytest src/e2e` → 68 passed (rerun after the session restart and database restart: 68 passed in 120.21s). Mutation `count() == len(expected) + 1` in `second_tester_accounts` → `test_private_draft_validation_reload_and_immutable_submission` 1 passed, 1 error (teardown assertion); reverted. Diff: 10 files +46/-232 plus 139 new lines; 0 non-test `src/` lines.
- Checkpoint 3: 12 screenshot calls and the unused `Path`/`gettempdir` imports deleted from test_presentation, test_navigation, test_feedback (35 deletions, no other change). `grep screenshot src/e2e` → only conftest's failure capture. ruff check/format pass. dblock `pytest` of the three modules → 39 passed in 79.58s.
