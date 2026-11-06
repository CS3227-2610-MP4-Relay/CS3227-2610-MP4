# 158: Reject superseded production runs

Goal: prevent an older validated workflow from migrating or deploying after a newer main commit has superseded its tested SHA.

Why: production concurrency serializes jobs but does not order workflows by commit; delayed validation can admit an older run after a newer delivery.

## Scope and decisions

- High tier; one affected requirement, [PLT-1](../specs/product/platform.md#plt-1-django-foundation-and-continuous-verification), adding PLT-1.15 without renumbering existing criteria. Maximum 400 changed source lines excluding tests/migrations; target a small guard and regressions.
- Keep exact tested-SHA checkout/archive, existing production prerequisites, opt-in and non-cancelling concurrency. Use the existing bounded HTTP helper and public GitHub ref API without credentials or new dependencies/services.
- The [release verification contract](../specs/TECHNICAL-SPEC.md#release-verification) owns lookup limits, stage placement and race boundaries. PLT-1.15 owns observable refusal outcomes; [CI controls](../specs/SECURITY-SPEC.md#ci-and-dependencies) link that policy.
- Check again just before CLI creation: a merge while migration/preparation runs must prevent the subsequent deployment. This cannot atomically lock main against a merge after the final check; serialization still makes any newer delivery wait. No rollback or migration cancellation.
- Pages ordering and hosted settings are outside this slice. No production execution is authorized by this implementation task.

## Intended commit checkpoints

1. `spec: Define production freshness rejection (#158)` — this plan and the three linked specs. Read back changed sections; scope/diff checks. Yield before implementation for coordinator review/commit and a fresh scope snapshot.
2. `fix: Reject superseded production runs (#158)` — `src/release.py`, `src/relay/tests/test_release.py`, `src/relay/tests/test_ci.py`, `.github/workflows/ci.yml`. First run focused new regression cases against unchanged implementation and record actual missing-behaviour failures. Implement the guard and wire validated repository identity into the production operations. Focused checks: release and CI tests, Ruff lint/format for affected Python; then full `ruff check . && ruff format --check . && pytest` with coordinator-allocated PostgreSQL/browser resources. Keep behaviour and regressions together; record any justified pre-implementation test exception.
3. `docs: Explain superseded production run failures (#158)` — `docs/DeveloperGuide.md` only if its current setup/design explanation needs updating; link the canonical release contract. Read back changed section and run relevant doc/CI checks. No Runbook edit within builder scope.

## Verification partitions

- Matching tested SHA permits checks/migrations and exact-SHA CLI creation; old SHA refuses before any migration/Vercel side effect, including the delayed-old-run-after-newer-delivery regression.
- Main advances between migration and deployment: first check succeeds, second refuses, completed migrations remain, CLI is never invoked.
- Independently reject malformed/missing repository or tested SHA, wrong/missing ref or object type, malformed/missing SHA, invalid JSON, failed HTTP status, timeout/transport error, redirect and oversized response. Assert bounded anonymous fixed-host requests and redacted output; use synthetic mocked responses only.
- Workflow checks retain exact-SHA checkout, prerequisites, main-only opt-in, environment, secret isolation and `cancel-in-progress: false`, and supply the repository identity to both guarded operations. Existing prepare/bootstrap behaviour remains covered.
- Mark new acceptance cases PLT-1.15; retain PLT-1.9–1.14 regression evidence. Backend/CI only, no browser journey change; full suite still required for High tier.

## State and next step

- Trigger/context: coordinator assignment for human `/slice 158 on a separate worktree`; base `f8adaad43506733793df05371dce01ecdb7c55f3`, branch `fix/158-production-release-order`. Builder receives the relevant paths, scope/budget and collaborator issue summary as data; no delegation or Git-state changes.
- Model and request effort/settings: not exposed to this role. Coordinator captured the usage baseline outside the repository; final selected-source accounting belongs in the session log/handoff, not this plan.
- First checkpoint: specs/plan only; no implementation or tests run. Harmless `check_scope.py --hook` probe with builder/`AGENTS.md` returned the fixed out-of-scope rejection (exit 2); no edit was attempted. Native client hook dispatch is unverified; effective approval reviewer is `auto_review`.
- Next: coordinator reviews and commits this checkpoint, supplies fresh snapshot, then assigns checkpoint 2. Independent verifier/security review and delivery remain coordinator work. No open scope decision.
