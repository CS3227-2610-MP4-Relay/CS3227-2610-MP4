# Slice 183: route-back navigation

Give coordinator and feedback conflicts, standalone error pages and tester-account pages visible top navigation ([PLT-4.15–PLT-4.18](../specs/product/platform.md#plt-4-shared-application-presentation)).

Why: Issue #183 found refusal and error pages with no route back, and tester-account links below long content; the User Guide tells users to press the browser's Back button.

## Scope and decisions

- Standard tier; PLT-4 is the single changed requirement: PLT-4.7 and PLT-4.14 clauses adjusted, PLT-4.15–PLT-4.18 added (six criteria). One-line prose links only in ACC-2/ACC-3/ACC-4 descriptions and round-action rule 4. Budget: at most 400 non-test source lines under `src/`.
- Human decision: defer the persistent navbar (no `base.html` navbar, no Sign out on every page).
- Human decision: 403, 404, 429 and 503 pages get one static secondary "Back to home" link to `/` before their heading, reusing the sign-in page's `page-navigation` markup. It must not evaluate `user`, session or database; signed-in users reach their role home through ACC-2.6. Messages and statuses unchanged.
- Coordinator choice (routine): feedback 409s mirror PLT-4.14 with "Tester home" and "Back to round".
- No new route, capability, dependency or control; 400/405 pages and the demo page are unchanged. All new links point to fixed, already authorized destinations, so no security review is planned unless the implementation touches authorization or queries.

## Commit checkpoints

1. `spec: Define route-back navigation for conflicts, errors and tester accounts (#183)` — `workflow/specs/product/platform.md`, `accounts.md`, `rounds.md` and this plan. Read back changed sections; run builder scope/diff checks. Yield.
2. `fix: Add navigation to round and feedback conflicts (#183)` — `src/rounds/views.py` (`state_conflict` passes `back=reverse("rounds:detail", ...)`), `src/ai/feedback_views.py` (back to `accounts:tester-round`), conflict template only if needed; tests in `src/rounds/tests/test_views.py`, `src/ai/tests/` and `src/e2e/test_navigation.py` or `test_presentation.py`. Red first: one link each before the message, exact destinations, unchanged message/status/no-store/rows, no form, no gateway call, foreign round still 404.
3. `fix: Add home links to error pages (#183)` — `src/relay/templates/{403,404,429,503}.html`; tests in `src/relay/tests/test_pages.py` and accounts tests. Red first: one "Back to home" to `/` before the `h1`; rendering with a user object that fails on access and under `assertNumQueries(0)` (or `django_assert_num_queries(0)`); CSRF 403 shows no workspace data; release smoke text `<h1>Page not found.</h1>` still matches.
4. `fix: Move tester-account links to the top (#183)` — `src/accounts/templates/accounts/{tester_passwords,tester_added,tester_password_reset,tester_limit}.html`; explicit links, not `page_navigation.html` (two pages render via `render_to_string` without a request). Tests in `src/accounts/tests/` and the existing tester-account browser journey in `src/e2e/test_accounts.py`; recapture `src/e2e/screenshots.py` images only if they show these pages. Red first: each link once, inside the top navigation before the `h1`, none after content; credentials/status/no-store unchanged.
5. `docs: Describe route-back navigation (#183)` — `docs/UserGuide.md` (replace the line ~103 browser-Back advice: a failed publish/retest shows the 503 page, whose "Back to home" reaches Coordinator home; describe conflict links) via maintain-docs; screenshots only if a captured image shows changed content.

Each code checkpoint runs focused server and browser tests red then green; checkpoint 5 is followed by `ruff check . && ruff format --check . && pytest` in the configured test environment (PostgreSQL 17 at 127.0.0.1:55432, Chromium, root `.venv`).

## Open issues and next steps

- Deferred: persistent navigation bar across pages (human decision, #183).
- TECHNICAL-SPEC rounds routes say rounds' "403 and 404 pages show fixed text only"; a static link keeps them fixed content, so no change is planned.
- Checkpoint 1 committed as bd8e323. Next: coordinator commits checkpoint 2, then assigns checkpoint 3.

## Implementation evidence

- Checkpoint 2 (Git Bash, root `.venv`, `--basetemp` in the session scratchpad because the default pytest temp directory was access-denied):
  - Red before production edits: `pytest -q src/rounds/tests/test_conflict_navigation.py src/ai/tests/test_feedback_views.py -k "conflict or eligibility or foreign or changes_during"` → 55 failed, 7 passed. Every failure was the missing "Coordinator home" (33) or "Tester home" (22) link; status, title, message and no-store assertions before it passed. The 7 passes are the foreign-workspace 404 cases, which already held.
  - Browser red: `test_round_lifecycle.py::test_coordinator_edits_retests_twice_and_closes_round` and `test_feedback.py::test_stale_feedback_tab_after_submission_refuses_without_gateway_call` → 2 failed on zero home links.
  - Green: the same server selection → 62 passed; `pytest -q src/rounds/tests src/ai/tests` → 1711 passed in 151.76s.
  - Browser green: `src/e2e/test_round_lifecycle.py` → 2 passed in 20.32s, run alone. The four tests `test_coordinator_edits_retests_twice_and_closes_round`, `test_native_validation_and_observation_limits_preserve_saved_draft`, `test_tester_result_and_feedback_long_content` and `test_stale_feedback_tab_after_submission_refuses_without_gateway_call` → 5 passed, 1 failed; the failure was the lifecycle test timing out on a navigation before any conflict, and that file then passed alone. Two wider runs of six browser files (78 passed/3 failed and 64 passed/14 failed/5 errors) overlapped other sessions' pytest runs on the shared `test_relay_test` database, which logged "database does not exist" and "accessed by other users". Rerun with exclusive database use before relying on them.
  - Coordinator rerun, 00:32–00:42 UTC, on a private test database (scratchpad settings module importing `relay.settings.test` and renaming only `TEST.NAME` to `test_relay_183`, `--ds=slice183_settings`): `pytest -q src/e2e/test_round_lifecycle.py src/e2e/test_feedback.py src/e2e/test_results.py src/e2e/test_presentation.py src/e2e/test_navigation.py src/e2e/test_drafting.py` → 81 passed in 590.06s. The contended failures above were database collisions.
- `test_shared_conflict_without_entry_context_keeps_existing_actions` is unchanged and still passes: it covers the renderer's default without `back`, which no production caller now uses.
- Checkpoint 3 (private test database `test_relay_183` via the coordinator's `slice183_settings`):
  - Red before template edits: `pytest -q src/relay/tests/test_error_pages.py` → 14 failed in 3.70s, each on the missing "Back to home" link after its status assertion passed. Browser red: the templates were temporarily restored to their HEAD versions as working-tree files, with no Git operation, and `test_existing_error_pages_share_the_error_treatment` → 2 failed on zero links.
  - Green: the same server file → 14 passed in 3.50s. `pytest -q src/accounts src/relay/tests/test_access_matrix.py src/relay/tests/test_pages.py src/relay/tests/test_release.py` → 1215 passed in 447.55s. `test_presentation.py -k "error_pages or sign_in_returns"` → 4 passed in 28.58s.
  - Another run, `pytest -q src/rounds/tests/test_views.py src/ai/tests/test_views.py src/relay/tests/{test_error_pages,test_site,test_readiness,test_database}.py`, gave 1 failed and 215 passed. The failure is `test_database.py::test_postgresql_synthetic_roundtrip`, which asserts the default name `test_relay_test` and therefore fails only under the private-database settings.
  - The existing reference-equality and "only its message" assertions still hold; no expectation changed.
- Checkpoint 4 (private test database):
  - Red before template edits: `pytest -q src/accounts/tests/test_tester_account_navigation.py` → 6 failed in 10.83s, each on the missing top navigation after its status and no-store checks passed. The two `src/e2e/test_accounts.py` journeys → 2 failed in 23.82s: the page navigation had no links.
  - Green: `pytest -q src/accounts/tests/test_tester_account_navigation.py src/accounts/tests/test_add_tester.py src/accounts/tests/test_reset_tester_password.py` → 55 passed in 12.41s. `src/e2e/test_accounts.py` → 8 passed in 59.18s, including the 10-tester passwords page at 320×568 with Coordinator home inside the first viewport.
  - `pytest -q src/accounts src/relay/tests/test_access_matrix.py` → 1052 passed in 251.76s.
  - No existing link-position expectation existed; the existing link assertions hold unchanged.
  - Screenshots `docs/images/beta-tester-added.png` and `beta-tester-passwords.png` (from `src/e2e/screenshots.py::account_management`) show these pages with the old bottom link; recapture them in the docs checkpoint.
