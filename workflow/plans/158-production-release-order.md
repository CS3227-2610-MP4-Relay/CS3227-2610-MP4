# 158: Reject superseded production runs

Goal: prevent an older validated workflow from migrating or deploying after a newer main commit has superseded its tested SHA.

Why: production concurrency serializes jobs but does not order workflows by commit; delayed validation can admit an older run after a newer delivery.

## Scope and decisions

- High tier; one affected requirement, [PLT-1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification), adding PLT-1.16 without renumbering existing criteria. Maximum 400 changed source lines excluding tests/migrations; target a small guard and regressions.
- Keep exact tested-SHA checkout/archive, existing production prerequisites, opt-in and non-cancelling concurrency. Use the existing bounded HTTP helper and public GitHub ref API without credentials or new dependencies/services.
- The [release verification contract](../specs/TECHNICAL-SPEC.md#release-verification) owns lookup limits, stage placement and race boundaries. PLT-1.16 owns observable refusal outcomes; [CI controls](../specs/SECURITY-SPEC.md#ci-and-dependencies) link that policy.
- Check again just before CLI creation: a merge while migration/preparation runs must prevent the subsequent deployment. This cannot atomically lock main against a merge after the final check; serialization still makes any newer delivery wait. No rollback or migration cancellation.
- Pages ordering and hosted settings are outside this slice. No production execution is authorized by this implementation task.

## Intended commit checkpoints

1. `spec: Define production freshness rejection (#158)` — this plan and the three linked specs. Read back changed sections; scope/diff checks. Yield before implementation for coordinator review/commit and a fresh scope snapshot.
2. `fix: Reject superseded production runs (#158)` — `src/release.py`, `src/relay/tests/test_release.py`, `src/relay/tests/test_ci.py`. First run focused new regression cases against unchanged implementation and record actual missing-behaviour failures. Implement the guard using the default Actions repository identity; no workflow override is needed. Focused checks: release and CI tests, Ruff lint/format for affected Python; then full `ruff check . && ruff format --check . && pytest` with coordinator-allocated PostgreSQL/browser resources. Keep behaviour and regressions together; record any justified pre-implementation test exception.
3. `docs: Explain superseded production run failures (#158)` — `docs/DeveloperGuide.md` only if its current setup/design explanation needs updating; link the canonical release contract. Read back changed section and run relevant doc/CI checks. No Runbook edit within builder scope.

## Verification partitions

- Matching tested SHA permits checks/migrations and exact-SHA CLI creation; old SHA refuses before any migration/Vercel side effect, including the delayed-old-run-after-newer-delivery regression.
- Main advances between migration and deployment: first check succeeds, second refuses, completed migrations remain, CLI is never invoked.
- Independently reject malformed/missing repository or tested SHA, wrong/missing ref or object type, malformed/missing SHA, invalid JSON, failed HTTP status, timeout/transport error, redirect and oversized response. Assert bounded anonymous fixed-host requests and redacted output; use synthetic mocked responses only.
- Workflow checks retain exact-SHA checkout, prerequisites, main-only opt-in, environment, secret isolation and `cancel-in-progress: false`, and supply the repository identity to both guarded operations. Existing prepare/bootstrap behaviour remains covered.
- Mark new acceptance cases PLT-1.16; retain PLT-1.9–1.14 regression evidence. Backend/CI only, no browser journey change; full suite still required for High tier.

## State and next step

- Trigger/context: coordinator assignment for human `/slice 158 on a separate worktree`; base `f8adaad43506733793df05371dce01ecdb7c55f3`, branch `fix/158-production-release-order`. Builder receives the relevant paths, scope/budget and collaborator issue summary as data; no delegation or Git-state changes.
- Model/request settings: coordinator reports observed `gpt-6.1-sol`, medium effort. Coordinator captured the usage baseline outside the repository; final selected-source accounting belongs in the session log/handoff, not this plan.
- First checkpoint: specs/plan only; no implementation or tests run. Harmless `check_scope.py --hook` probe with builder/`AGENTS.md` returned the fixed out-of-scope rejection (exit 2); no edit was attempted. Native client hook dispatch is unverified; effective approval reviewer is `auto_review`.
- Specs committed at `7e2aabd1964ad9af61738221fbbfba8ba0876619`; checkpoint 2 uses `%TEMP%/relay-158-builder-2.json`. Pre-implementation regressions reproduced stale migration/deployment success. Broader red run: 62 failed, 70 deselected after shortening oversized-response test IDs to fix Windows fixture paths. Additional status/SHA/preparation partitions were added after implementation; they extend the same guard regression rather than supply pre-implementation evidence.
- Human explicitly assigned this slice PLT-1.16 after discovering another unmerged worktree allocated PLT-1.15. This supersedes the new criterion ID in the first spec checkpoint, without changing any baseline criterion or retiring the other slice's ID; all local specs and test markers now use PLT-1.16.
- Focused implementation checks initially passed 151 tests after correcting a missing parent directory in the local basetemp argument. Full lint/format passed; the first full pytest run was intentionally interrupted before completion to remove redundant Actions identity overrides and rerun the integrated final candidate. No production or provider calls are made by the tests.
- The next full attempt encountered database setup errors and was stopped. A one-test diagnostic established that `test_relay_test` could not be recreated because another session was using it; no assertion failure was established. Interrupting the Git Bash wait left Windows pytest child processes alive. Coordinator stopped only the matching slice processes, cleared the dedicated test database and allocated separate pytest/cache paths before the final run.
- Final verification: full `ruff check .` passed; `ruff format --check .` reported 147 files already formatted; `python -m pytest --ds=relay_slice158_settings --basetemp=<isolated harness>/pytest-complete -o cache_dir=<isolated harness>/cache-complete .` passed with **3078 passed, 5 skipped in 1269.27s**. The coordinator's ignored fixed-settings harness changes only PostgreSQL PORT to 55438; Windows `PYTHONPATH` points to that harness. Full output is outside the tracked tree in the coordinator's `slice158-harness/complete-verification.log`. Focused release/CI verification after the authorized ID change passed 151 tests.
- A targeted `pytest -rs` rerun of the five skipped workflow checks confirmed their existing platform reasons: POSIX hook command, unavailable `pwsh`, two Windows symlink-rights exclusions, and directory symlink creation denied with WinError 1314. Result: 5 skipped, 45 deselected; no skip or test expectation was changed.
- Rollout limitation: only workflows containing the updated helper enforce freshness; rerunning pre-change commits still uses unguarded code. Operators must inspect and wait for any prior production runs before relying on the guard. No production jobs were inspected, cancelled or changed by the builder.
- The Developer Guide already links the authoritative release contract; no separate documentation checkpoint is needed. No open scope decision.

## Review and delivery

- The coordinator committed the human-authorized ID correction as `9bf122b`, then the implementation/tests/plan as `1b87a81f3a641a7c61a2aaa2d85021237b169853`. Implementation and final checks preceded this separation; it is not additional incremental-build evidence.
- Verifier and security-reviewer independently inspected the fixed range `f8adaad43506733793df05371dce01ecdb7c55f3..1b87a81f3a641a7c61a2aaa2d85021237b169853` against `%TEMP%/relay-158-review.json`. Both independently ran the 151 release/CI checks and found no correctness/scope or blocking security findings. The security reviewer additionally passed six development-control tests and 23 subtests. Both role scope checks and the final unchanged-candidate comparison passed; no review repair was needed.
- Review limits: full-suite results were independently read from the saved log, while red-run and Ruff results were supplied console evidence. Production operation, hosted restrictions and native client hook dispatch were not exercised. ASCII allowlists reject Unicode, but the new guard has no separate Unicode regression case.
- [Session evidence and usage](../../logs/Whimsyturtle/042-reject-superseded-production-runs.md) record the review cutoff. Next: push the branch, open its draft PR and wait for `verify` and site validation on the final head. Merge, release and human log/manual review remain pending. The PR body records final hosted outcomes without adding another summary commit.
