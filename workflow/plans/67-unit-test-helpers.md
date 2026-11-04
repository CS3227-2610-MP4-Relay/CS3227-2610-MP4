# #67 cleanup: unit test helpers

Goal: share duplicated test helpers, make no-write snapshots order-independent and complete, and make the round race harness prove the second request waited for the round lock.

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
- `race()` pauses the first request inside `slow` until PostgreSQL reports the second request's backend waiting on a lock, then releases it. It fails if the second never waits. A caller whose second request is refused before locking passes `wait=False`; any such caller is listed in the T2 checkpoint result.
- A13: ACC-3.7 requires the 503 page, no sign-in and nothing created; it does not require any log text. The idle case will accept the server's reason or the client's connection-loss text, because the only injected fault is a 0.5 s pause under a 100 ms idle timeout. All behaviour assertions stay unchanged. The statement case keeps its exact text.

## Commit checkpoints

1. [x] `plan:` this file.
2. [x] `test:` shared ordered `domain_rows`, including `Result` (T1, T3). Paths: `rounds/tests/conftest.py` (`domain_rows`, `ROUND_RECORDS`, `DOMAIN_MODELS`) and 19 snapshot users in `rounds/tests/` and `ai/tests/`. Result: the 19 modules gave 858 passed; ruff clean. Mutation (a tester detail GET of an Open round creates a `Result`): `test_tester.py` gave 4 failed, including `test_detail_shows_ordered_cases_links_and_latest_covering_build[False]` at its `domain_rows()` no-write check; the base `ebd890c` copy of that test passed both cases under the same mutation. Reverted.
3. [ ] `test:` share the other duplicated helpers (T4). Paths: `rounds/tests/conftest.py`, new `relay/tests/conftest.py`, and their call sites. Checks: the affected modules; a mutation of the shared `no_store` fails a named test.
4. [ ] `test:` deterministic race harness (T2). Path: `rounds/tests/conftest.py` (and any `wait=False` callers). Checks: the 11 race callers; with the round lock removed from `rounds/views.py` in a scratch mutation, at least one race test fails (then reverted).
5. [ ] `test:` driver-independent ACC-3.7 idle assertion (A13). Path: `accounts/tests/test_limit_views.py`. Orchestrator conditions: the idle case still rejects the statement-timeout text, and its alternative is psycopg's exact connection-loss text, with the source cited. Checks: the timeout test; the idle case still fails if the injected pause is removed.
6. [ ] Full verification: `ruff check . && ruff format --check . && pytest` through the DB lock wrapper (base: 2857 passed, 254 subtests). The test count must not drop.

## Open items

- None yet. Other builders refactor `src/rounds`, `src/ai` and `src/accounts` in parallel; this slice edits only helper definitions, their call sites and the items above.
