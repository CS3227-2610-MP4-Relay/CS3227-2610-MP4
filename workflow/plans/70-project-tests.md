# Project test relocation (#70)

Move project tests and probe helpers from `src/relay_tests/` to `src/relay/tests/`, preserving test behaviour, coverage and collection.

## Scope and decisions

- Standard tier; pure refactor under [PLT-1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification). Existing criteria and architecture already cover this layout; no requirement or technical-spec change is needed.
- Move all nine tracked files, retaining probe helpers as separate executable Python files. Update shared imports in accounts and rounds tests, subprocess probe paths, repository/source depth calculations and framing scanner test-directory exclusions.
- Preserve assertions and acceptance markers, including existing PLT-2 site checks. No production code, CI, security-control semantics, dependencies or services change.
- Budget: at most one changed requirement and 400 non-test source lines; expected implementation is renames and small test-only path/import edits.
- The requested PR stack now starts at merged PR #72 (`1ed0b8546fad32549396f88a16cb550ea89c5b23`); branch `refactor/70-project-tests` targets `main`.

## Commit checkpoints

1. **Plan:** add this plan only; inspect collection and path dependencies. Check plan readback, `git diff --check` and builder scope against the supplied snapshot. Yield before implementation.
2. **Relocate tests:** move `src/relay_tests/**` to `src/relay/tests/**`; update `src/accounts/tests/test_models.py` and `src/rounds/tests/test_framing.py`. Adjust depths in relocated configuration, CI and site tests and all probe invocations. Compare collected node IDs after normalizing the old/new directory prefix; run focused configuration, CI, site, shared-import and non-database framing checks, lint and formatting. Existing passing tests serve as regression evidence: this refactor has no missing behaviour to demonstrate with a manufactured red test. Yield for the coherent refactor commit.
3. **Documentation, if needed:** update `docs/DeveloperGuide.md` only if inspection finds a now-stale layout reference; otherwise omit this checkpoint. Coordinator records session evidence in its summary log.

## Verification and next steps

- Collection baseline captured outside the repository as `%TEMP%/relay-70-collection-before.txt`: `pytest --collect-only -q` collected 918 tests successfully before implementation. Compare the complete normalized node-ID set, not only its count.
- Required final integrated command remains `ruff check . && ruff format --check . && pytest` with `.venv` active. No database tests ran in this plan checkpoint.
- Coordinator observed loopback PostgreSQL port 55432 unavailable and no usable existing Docker engine. Do not install/start a service within this refactor. Record the exact local full-verification result and use the existing hosted CI database job for complete database evidence; unavailable local database checks remain explicit.
- After the plan commit and a fresh scope snapshot, resume checkpoint 2 only. Coordinator freezes the integrated candidate for independent verification, then completes authorized draft-PR delivery and latest-head CI checks. Add security review only if implementation changes control semantics or another review trigger arises.
- Open issue: local database verification is unavailable in the observed environment. No product decision or scope expansion is required for the relocation.

## Checkpoint 2 evidence

- All nine files relocated; only path/depth adjustments, two shared imports and the framing test-directory exclusion changed. Assertions and markers are preserved. No active guide instruction needs updating.
- Collection comparison: 918 before and after, with no node-ID differences after replacing only `src/relay_tests/` with `src/relay/tests/`.
- Focused configuration, CI, site, page and accounts-model checks: 51 passed before and after; 14 deselected using `-m 'not django_db' -k 'not driver_ignores_inherited_hostaddr'`. The three driver-destination cases, database roundtrip, database-marked accounts tests and entire framing module still need PostgreSQL execution. Existing framing markers were retained.
- `ruff check .`, `ruff format --check .` (73 files), diff whitespace check and builder snapshot scope check passed. Coordinator owns the final full-suite attempt and hosted CI evidence.
- One mechanical edit error caused two collection errors; repaired before the successful comparison and checks. No test expectations were changed. Await coordinator commit and fixed-candidate verification.
