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
- Plan and relocation checkpoints are committed; independent review is complete. The coordinator completes the summary checkpoint and verifies its final hosted CI result before handoff.
- Open issue: local database verification is unavailable in the observed environment. No product decision or scope expansion is required for the relocation.

## Checkpoint 2 evidence

- All nine files relocated; only path/depth adjustments, two shared imports and the framing test-directory exclusion changed. Assertions and markers are preserved. No active guide instruction needs updating.
- Collection comparison: 918 before and after, with no node-ID differences after replacing only `src/relay_tests/` with `src/relay/tests/`.
- Focused configuration, CI, site, page and accounts-model checks: 51 passed before and after; 14 deselected using `-m 'not django_db' -k 'not driver_ignores_inherited_hostaddr'`. The three driver-destination cases, database roundtrip, database-marked accounts tests and entire framing module still need PostgreSQL execution. Existing framing markers were retained.
- `ruff check .`, `ruff format --check .` (73 files), diff whitespace check and builder snapshot scope check passed. Coordinator owns the final full-suite attempt and hosted CI evidence.
- One mechanical edit error caused two collection errors; repaired before the successful comparison and checks. No test expectations were changed.

## Reviewed candidate and delivery

- The verifier found no defects in `1ed0b8546fad32549396f88a16cb550ea89c5b23..b771e19a1506feac49467f4f53cca80ee686ff01`; scope and unchanged-candidate checks passed. No security-review trigger arose.
- [Draft PR #75](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/pull/75) targets `main`, which already includes #72. [Implementation-head CI](https://github.com/CS3227-2610-MP4-Relay/CS3227-2610-MP4/actions/runs/40466397305) passed. The [session log](../../logs/Whimsyturtle/010-relocate-project-tests-beside-relay-code.md) records exact checks, review limits and resources; final summary-head CI belongs in the PR body.
- Human log/manual review and merge remain pending. Local PostgreSQL is unavailable; full hosted verification covers the database-dependent tests.
