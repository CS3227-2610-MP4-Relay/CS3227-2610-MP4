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

- Checkpoint 1: plan written.

## Decisions and open items

- Scope hook does not run in this environment (orchestrator diagnosis); scope is checked post hoc with `check_scope.py builder` per checkpoint. Hook fix held for the human.
