# #67 cleanup: accounts views and release smoke markers

Goal: remove the accounts role-home factory, stale docstrings and a duplicated session lifetime, and tie the release smoke check's page markers to the rendered templates, without changing behaviour.

Tier: High (coordinator-home role check, session lifetime, release smoke check). Base: `ebd890c`. Branch/worktree: `67-accounts-cleanup` in `relay-67-accounts`. Budget: 400 non-test `src/` lines. Behaviour-preserving: no change to routes, status codes, messages, criteria or controls; the coordinator home keeps its specified 500 on storage failure (`src/rounds/tests/test_views.py`), so it is not moved onto `rounds.views.coordinator_view`.

## Confirmed items

- **A1** `src/accounts/views.py` `_role_home` factory and `tester_home` re-export: replace with a plain `coordinator_home` (`@never_cache` outside `@require_GET`; anonymous redirect, then 403 for the wrong role); `urls.py` uses `tester.home` directly; drop unused imports. Pinned by `src/relay/tests/test_access_matrix.py` (GET_ONLY, ROLE_HOME_REFUSALS), `test_role_homes_are_never_cached`, `test_other_role_home_is_forbidden`.
- **A2** Stale docstrings: `src/accounts/urls.py` (also holds the tester round, results, result and feedback routes); `src/accounts/limits.py` (views also call `client_key` and `peek`).
- **A3** `SESSION_LIFETIME` in `views.py` repeats `SESSION_COOKIE_AGE` (ACC-1.6, 8 hours): derive it from settings. Pinned by `src/accounts/tests/test_sign_in.py` ACC-1.6 boundary test (8 h - 1 s / 8 h / 8 h + 1 s) and cookie max-age test, and `test_models.py` settings assertion.
- **A10** `src/release.py` `_smoke` page markers inline: move to a module constant; add one test rendering `/`, `/sign-in/` and a 404 through Django's test client and checking each contains its marker. Requests and acceptance unchanged ([release verification](../specs/TECHNICAL-SPEC.md#release-verification)).

## Commit checkpoints

1. `plan:` this file.
2. `refactor:` A1 + A2 + A3 — `src/accounts/views.py`, `src/accounts/urls.py`, `src/accounts/limits.py`. Focused: `src/accounts/tests`, `src/relay/tests/test_access_matrix.py`, `src/rounds/tests/test_views.py` (dblock); mutations: drop the role check → a named test fails; change the lifetime → ACC-1.6 test fails.
3. `refactor:` A10 constant + render test — `src/release.py`, `src/relay/tests/test_release.py`. Focused: `src/relay/tests/test_release.py`; mutation: change a template heading → new test fails.
4. Final: `ruff check . && ruff format --check . && pytest` (base: 2857 passed, 254 subtests).

## Results

- Checkpoint 1: plan written (38e4b24).
- Checkpoint 2 (rerun after the session restart): ruff check/format pass; focused `src/accounts/tests src/relay/tests/test_access_matrix.py src/rounds/tests/test_views.py` → 1058 passed. Mutations (each backed up, reverted and compared): drop the coordinator role check → `test_other_role_home_is_forbidden[tester-/tester/-/coordinator/]` and `test_accounts_route_matrix[accounts:coordinator-tester_a]` fail (2 failed, 840 passed); `SESSION_COOKIE_AGE + 1` → `test_session_ends_eight_hours_after_sign_in[elapsed1-302]` fails (1 failed, 60 passed); drop `@never_cache` → `test_role_homes_are_never_cached[coordinator]` fails (1 failed, 841 passed). Non-test `src/`: 3 files, +23 −29. `accounts/home.html` stays (both role templates extend it). Committed 3a1aa22.
- Checkpoint 3 (rerun after the reboot, wrapper `/Users/zheng/Desktop/mp4/.r67/dblock.py`): `release.SMOKE_PAGES` holds the smoke paths, statuses and headings; `_smoke` iterates it unchanged. New `test_smoke_headings_match_the_rendered_pages` (PLT-1.13) renders each through the test client. `src/relay/tests/test_release.py` → 68 passed. Mutations (backed up, restored, compared): `home.html` heading → `Relay portal` → new test `[/-200-<h1>Relay</h1>]` fails (1 failed, 67 passed); constant sign-in heading changed → `test_cli_upload_and_bounded_anonymous_smoke`, `test_ready_response_at_deadline_is_too_late[599-True]` and the new test fail (3 failed, 65 passed).
- Final (rerun after the reboot): with `$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin` on PATH, `ruff check .` pass, `ruff format --check .` pass, full pytest via dblock → 2860 passed, 254 subtests passed in 216.86s (base 2857 + 3 new). Non-test `src/` total: 4 files, +32 −34.

## Review

Candidate 88d7a54: verifier and security reviewer found no High/Medium. Repair round 1 (test-only, no `src` change):

- Verifier Low 1: `test_coordinator_home_round_list_keeps_the_accounts_storage_rule` in `src/rounds/tests/test_views.py` patches `accounts.views.workspace_records` to raise `DatabaseError`; expects 500 without the 503 text. Mutation (view catches `db.Error` and renders `503.html` with 503; backed up, restored, compared) → the new test fails (1 failed, 1 passed).
- Verifier Low 2: `test_smoke_headings_match_the_rendered_pages` also asserts `len(response.content) <= 65536`. Mutation (70 000-character comment in `home.html`) → `[/-200-<h1>Relay</h1>]` fails (1 failed, 2 passed).
- Checks: ruff check/format pass; `src/rounds/tests/test_views.py src/relay/tests/test_release.py src/accounts/tests` → 346 passed; full pytest via `/Users/zheng/Desktop/mp4/.r67/dblock.py` with the brief's PATH → 2861 passed, 254 subtests passed in 233.92s. Non-test `src/` unchanged at 4 files, +32 −34.

## Decisions and open items

- Scope hook does not run in this environment (orchestrator diagnosis); scope is checked post hoc with `check_scope.py builder` per checkpoint. Hook fix held for the human.
