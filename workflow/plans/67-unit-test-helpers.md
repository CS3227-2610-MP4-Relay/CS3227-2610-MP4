# #67 cleanup: unit test helpers

Goal: share duplicated test helpers, make no-write snapshots order-independent and complete, and make the round race harness prove the second request waited for a lock held by the first.

Tier: Standard (test-only; verifier review). Base: `ebd890c`. Paths: `src/**/tests/**` and `src/**/conftest.py`, excluding `src/e2e/`. No product, spec or criterion changes; non-test `src/` budget 400 lines, expected 0.

## Confirmed items (sweep IDs)

- **T1** `rounds/tests/test_tester.py` `snapshot()` claims "all domain data" but omits `Result`; its four no-write checks would miss a tester GET that created a result.
- **T3** About 13 near-identical "rows unchanged" helpers (`everything`, per-round `snapshot`/`stored`, `test_result_services.snapshot`, `test_tester.snapshot`). Most compare `CaseCriterion`/`BuildCase` `.values()` without `order_by`; neither model has `Meta.ordering`.
- **T4** Duplicates: `no_store` (7), `locked` (4), `workspace` fixture overrides (4, differing only in the name), `title_tag` and `assert_no_raw_markup` (2 each), and helpers imported from test modules (`test_result_services.snapshot` by 7 modules, `test_configuration.probe` by 2, `test_results.no_store` by `test_history`).
- **T2** `rounds/tests/conftest.py` `race()` gives the second request a fixed 0.3 s head start; a slow second request arrives after the commit and the test still passes. `test_result_services.race` already waits on `pg_stat_activity.wait_event_type = 'Lock'`.
- **A13** `accounts/tests/test_limit_views.py` ACC-3.7 idle case asserts the server text `idle-in-transaction timeout`. Windows psycopg reports `server closed the connection unexpectedly` (logs 036/037), while the 503 assertions pass.

## Decisions

- One helper, `domain_rows(*models)` in `rounds/tests/conftest.py`: `{model: rows ordered by pk}` for `Round, Criterion, Case, CaseCriterion, Build, BuildCase, Result`, or only the named models. Tests whose action legitimately changes some rows (e.g. publishing changes `Round` and adds builds) name the models that must stay unchanged instead of slicing a tuple. Refusal checks that compared only one round's rows now compare every row, which is stricter.
- Keep a per-round helper only in `test_records.py::test_injected_fields_are_ignored`, which writes to `draft` between the snapshots and must check only the sibling's rows; it gains `order_by("pk")`.
- `no_store`, `locked`, `title_tag`, `assert_no_raw_markup` and `domain_rows` move to `rounds/tests/conftest.py`. `ai/tests` already imports from `rounds.tests.conftest`, so it reuses them there. `probe` moves to a new `relay/tests/conftest.py`, following the same `<app>.tests.conftest` import pattern.
- `workspace` (and `test_services.py`'s matching `other_workspace`) overrides are removed; the conftest fixtures differ only in the synthetic name, and no test reads those names.
- `race()` pauses the first request inside `slow` until PostgreSQL reports the second request's backend waiting on a lock, then releases it. It fails if the second never waits. (A `wait=False` opt-out was planned but had no caller and was removed in review.)
- A13: ACC-3.7 requires the 503 page, no sign-in and nothing created; it does not require any log text. The idle case will accept the server's reason or the client's connection-loss text, because the only injected fault is a 0.5 s pause under a 100 ms idle timeout. All behaviour assertions stay unchanged. The statement case keeps its exact text.

## Commit checkpoints

1. [x] `plan:` this file.
2. [x] `test:` shared ordered `domain_rows`, including `Result` (T1, T3). Paths: `rounds/tests/conftest.py` (`domain_rows`, `ROUND_RECORDS`, `DOMAIN_MODELS`) and 19 snapshot users in `rounds/tests/` and `ai/tests/`. Result: the 19 modules gave 858 passed; ruff clean. Mutation (a tester detail GET of an Open round creates a `Result`): `test_tester.py` gave 4 failed, including `test_detail_shows_ordered_cases_links_and_latest_covering_build[False]` at its `domain_rows()` no-write check; the base `ebd890c` copy of that test passed both cases under the same mutation. Reverted.
3. [x] `test:` share the other duplicated helpers (T4). `locked`, `no_store`, `title_tag` and `assert_no_raw_markup` moved to `rounds/tests/conftest.py` (`open_with_case` and `stored_retest` now use `locked`); `probe`, `SRC` and `PROBE` moved to new `relay/tests/conftest.py`; the `workspace` overrides (4) and `test_services.py`'s `other_workspace` were removed. No module imports helpers from another test module any more, except `src/e2e/` (other builder's scope). Result: the 18 changed modules gave 712 passed; ruff clean. Mutation (`rounds/views.py` decorator sends `cache_control(no_store=True)`, dropping `private`): `test_close.py` failed `test_closing_a_closed_round_gets_409_and_changes_nothing` and `test_get_head_and_put_get_405_uncached[True]` at the shared `no_store`. Reverted.
4. [x] `test:` deterministic race harness (T2). `race()` pauses the first request inside `slow` until the shared `wait_for_lock(pid)` sees the second request's backend waiting on a lock (fails after 5 s otherwise); `test_result_services.race` uses the same helper. No caller needed `wait=False`: every second request waits. Result: the four race modules gave 174 passed. Mutation (`own_round` without `select_for_update`): the new harness failed 12 race tests; the old harness under the same mutation failed 11, passing `test_a_retest_that_locks_first_completes_before_the_close`. `test_a_retitle_racing_a_publish_is_saved_first_or_refused[True]` passes under both, because the second request still waits on the first's row update. Reverted.
5. [x] `test:` driver-independent ACC-3.7 idle assertion (A13). Path: `accounts/tests/test_limit_views.py`. Orchestrator conditions: the idle case still rejects the statement-timeout text, and its alternative is psycopg's exact connection-loss text, with the source cited. The idle case accepts PostgreSQL's `idle-in-transaction timeout` or libpq's `server closed the connection unexpectedly` (`pqReadData`, `fe-misc.c`; present in the bundled `psycopg_binary/.dylibs/libpq.5.dylib`, libpq 18.0.6). Each case rejects the other case's texts. Result: 6 passed. Mutations: without the injected pause, the 3 idle cases failed (`assert 200/302 == 503`); with the statement fault in the idle case, they failed at the reason check; with the statement fault and the idle reasons widened to the statement text, they failed at the rejection check. Reverted.
6. [x] Full verification: `ruff check . && ruff format --check . && pytest` through the DB lock wrapper, with Codex CLI on `PATH`: ruff clean, 139 files formatted, 2857 passed, 254 subtests passed in 209.30s (same as the base). After the 2026-11-05 reboot, the unit checks, their mutations and full verification were rerun through `/Users/zheng/Desktop/mp4/.r67/dblock.py` with the same results (full: 2857 passed, 254 subtests passed in 213.24s); the T4 mutation then failed 5 `test_close.py` tests at the shared `no_store`.

## Review

Repair round 1 (verifier, candidate `d97e71e`: no High or Medium; three Low findings, all fixed test-only):

1. `race()` lost its unused `wait=False` parameter and docstring sentence, which checked nothing.
2. `race()`, `wait_for_lock` and its failure message now say the second operation waits for "a lock held by the first request", not the round lock: `wait_for_lock` accepts any lock, and `test_a_retitle_racing_a_publish_is_saved_first_or_refused[True]` waits on a row update.
3. Model lists that omitted models the action must not change: `test_records.py` (RND-2.8 locked re-check, which changes only the round row) now compares `domain_rows(*ROUND_RECORDS)`; `test_publish_services.py` (RND-3.4), `test_publish.py` (RND-3.4), `test_retest_services.py` (RND-5.5) and `test_retest.py` (RND-5.5) now include `Result`.

Checks: the 7 affected modules (`test_publish`, `test_publish_services`, `test_retest`, `test_retest_services`, `test_records`, `test_close`, `test_result_services`) gave 356 passed. Mutation (`own_round` without `select_for_update`): 12 race tests failed, with "Second operation did not wait for a lock held by the first request". Reverted. Full verification with the brief's `PATH`: ruff clean, 139 files formatted, 2857 passed, 254 subtests passed in 209.37s.

Out of scope (equivalent inline copies left as they are; no confirmed item covers them):

- Title splitting `split("<title>"` inline in `rounds/tests/test_publish.py`, `test_retest.py`, `test_close.py`, `test_record_rendering.py`.
- Raw-tag checks `SCRIPT_TAG not in` inline in `rounds/tests/test_results.py`, `test_direction_controls.py`, `test_publish.py`, `test_messages.py`, `test_tester.py`, `test_history.py`, `test_retest.py`, `test_close.py`, `test_review.py`.
- Inline `select_for_update().get` in `ai/tests/test_feedback_views.py`, `relay/tests/test_access_matrix.py` and `rounds/tests/test_retest.py`, `test_records.py`, `test_close.py`, `test_publish.py`, `test_review.py`, `test_result_services.py`, `test_results.py`, `test_direction_controls.py`.
- Inline cache-control checks `"no-store" in` in `accounts/tests/test_sign_in.py` and `rounds/tests/test_routes.py`, `test_views.py`, `test_tester.py`.
- Verifier recheck of `d97e71e..fa4a548`: all three Lows resolved, no new findings. CI on `fa4a548` failed once in `src/e2e/test_rounds.py::test_coordinator_manages_later_collapsed_case[1440]` (Playwright "Page.reload: Not attached to an active page", then its teardown row check); this slice changes no browser test or app code, and the test passed three times locally on `fa4a548`. CI on `cc5b034` failed the same test again (`[320]`), at the final `page.reload()` straight after a **Delete criterion** click: the reload races the form's POST and redirect. The race is in `main`'s browser test, which this slice does not touch; the browser-test slice (#126) fixes it by waiting for each submit navigation before reloading. Merge #126 before this PR, or rerun its CI after.

## Open items

- None. Other builders refactor `src/rounds`, `src/ai` and `src/accounts` in parallel; this slice edits only helper definitions, their call sites and the items above.
